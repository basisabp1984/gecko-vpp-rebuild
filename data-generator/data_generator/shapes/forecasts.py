"""ems.forecasts + ems.forecast_actuals.

Derive forecasts from telemetry by adding MAPE-shaped error.
- primary forecast: σ 10–15% (issued D-1 morning)
- refined forecast: σ 5–8% (issued D-1 evening)
- forecast_actuals: copy of telemetry's energy per (asset, hour)

forecast_kind chosen by asset class:
  СЕС → solar
  ВЕС → wind
  Споживач/АктСпож → load
  УЗЕ/ГПУ → price (we still create a row for each so KPI/coverage works)
"""

from __future__ import annotations

from datetime import date as DateT, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.rng import get_rng
from data_generator.shapes.assets import ALL_ASSETS, AssetSpec


KYIV_OFFSET = timezone(timedelta(hours=3))


def _kind_for_asset(asset: AssetSpec) -> str:
    if asset.asset_class == "СЕС":
        return "solar"
    if asset.asset_class == "ВЕС":
        return "wind"
    if asset.asset_class in ("Споживач", "АктСпож"):
        return "load"
    if asset.asset_class == "УЗЕ":
        return "price"  # batteries forecast price arbitrage signals
    return "price"  # ГПУ


async def generate(conn: AsyncConnection) -> int:
    # Fetch telemetry per asset
    fc_stmt = text(
        """
        INSERT INTO ems.forecasts
            (tenant_id, asset_id, forecast_kind, forecast_type, issued_at,
             date, hour, value_mwh, model_id, confidence_lo, confidence_hi)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid),
             :kind, :ftype, :issued_at, :date, :hour, :value, :model_id,
             :conf_lo, :conf_hi)
        ON CONFLICT (tenant_id, asset_id, forecast_kind, forecast_type,
                     date, hour) DO NOTHING
        """
    )
    act_stmt = text(
        """
        INSERT INTO ems.forecast_actuals
            (tenant_id, asset_id, forecast_kind, date, hour, actual_mwh)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid),
             :kind, :date, :hour, :actual)
        ON CONFLICT DO NOTHING
        """
    )
    total = 0

    for asset in ALL_ASSETS:
        kind = _kind_for_asset(asset)
        rng = get_rng(f"forecasts:{asset.code}")
        # Pull all telemetry for this asset
        res = await conn.execute(
            text(
                """
                SELECT date, hour, active_power_mw
                FROM dispatch.telemetry
                WHERE tenant_id = CAST(:tid AS uuid)
                  AND asset_id = CAST(:aid AS uuid)
                """
            ),
            {"tid": str(asset.tenant_id), "aid": str(asset.asset_id)},
        )
        telemetry_rows = res.fetchall()
        if not telemetry_rows:
            continue

        fc_rows: list[dict[str, Any]] = []
        act_rows: list[dict[str, Any]] = []
        for t in telemetry_rows:
            actual_mwh = abs(float(t.active_power_mw))  # MWh per hour
            # Primary forecast — issued D-1 09:00
            d_prev = t.date - timedelta(days=1)
            issued_primary = datetime.combine(d_prev, time(9, 0), tzinfo=KYIV_OFFSET)
            sigma_p = 0.13 if kind in ("solar", "wind") else 0.08
            err_p = float(rng.normal(0.0, sigma_p))
            primary_val = max(0.0, actual_mwh * (1.0 + err_p))

            # Refined forecast — issued D-1 18:00
            issued_refined = datetime.combine(d_prev, time(18, 0), tzinfo=KYIV_OFFSET)
            sigma_r = 0.06 if kind in ("solar", "wind") else 0.04
            err_r = float(rng.normal(0.0, sigma_r))
            refined_val = max(0.0, actual_mwh * (1.0 + err_r))

            fc_rows.append(
                {
                    "tenant_id": str(asset.tenant_id),
                    "asset_id": str(asset.asset_id),
                    "kind": kind,
                    "ftype": "primary",
                    "issued_at": issued_primary,
                    "date": t.date,
                    "hour": t.hour,
                    "value": Decimal(f"{primary_val:.4f}"),
                    "model_id": "synth-v1-primary",
                    "conf_lo": Decimal(f"{primary_val * 0.85:.4f}"),
                    "conf_hi": Decimal(f"{primary_val * 1.15:.4f}"),
                }
            )
            fc_rows.append(
                {
                    "tenant_id": str(asset.tenant_id),
                    "asset_id": str(asset.asset_id),
                    "kind": kind,
                    "ftype": "refined",
                    "issued_at": issued_refined,
                    "date": t.date,
                    "hour": t.hour,
                    "value": Decimal(f"{refined_val:.4f}"),
                    "model_id": "synth-v1-refined",
                    "conf_lo": Decimal(f"{refined_val * 0.92:.4f}"),
                    "conf_hi": Decimal(f"{refined_val * 1.08:.4f}"),
                }
            )
            act_rows.append(
                {
                    "tenant_id": str(asset.tenant_id),
                    "asset_id": str(asset.asset_id),
                    "kind": kind,
                    "date": t.date,
                    "hour": t.hour,
                    "actual": Decimal(f"{actual_mwh:.4f}"),
                }
            )
        if fc_rows:
            res2 = await conn.execute(fc_stmt, fc_rows)
            total += (res2.rowcount if res2.rowcount and res2.rowcount > 0 else len(fc_rows))
        if act_rows:
            res3 = await conn.execute(act_stmt, act_rows)
            total += (res3.rowcount if res3.rowcount and res3.rowcount > 0 else len(act_rows))
    return total
