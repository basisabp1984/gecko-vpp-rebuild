"""ems.kpi_daily — one row per (tenant, asset, day).

Derived from telemetry × РДН prices. Includes CO₂ avoided (§11.22), revenue,
imbalance, availability. Plus availability dip on curtailment days
(satisfies §11.27 / coverage curtailment criterion).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    SYNTH_DATE_END,
    SYNTH_DATE_START,
    date_range_inclusive,
)
from data_generator.rng import get_rng
from data_generator.shapes.assets import ALL_ASSETS


CO2_GRID_FACTOR_TN_PER_MWH = 0.45  # UA grid emissions factor


async def generate(conn: AsyncConnection) -> int:
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    stmt = text(
        """
        INSERT INTO ems.kpi_daily
            (tenant_id, asset_id, date, grn_saved_uah, grn_earned_uah,
             imbalance_mwh, co2_avoided_tn, availability_pct, opportunity_score, notes)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid), :date,
             :grn_saved, :grn_earned, :imbalance, :co2, :avail, :opp, :notes)
        ON CONFLICT (tenant_id, asset_id, date) DO UPDATE SET
            grn_saved_uah = EXCLUDED.grn_saved_uah,
            grn_earned_uah = EXCLUDED.grn_earned_uah,
            imbalance_mwh = EXCLUDED.imbalance_mwh,
            co2_avoided_tn = EXCLUDED.co2_avoided_tn,
            availability_pct = EXCLUDED.availability_pct,
            opportunity_score = EXCLUDED.opportunity_score,
            notes = EXCLUDED.notes
        """
    )

    for asset in ALL_ASSETS:
        rng = get_rng(f"kpi_daily:{asset.code}")
        # Pull telemetry aggregated by day + rdn for revenue
        res = await conn.execute(
            text(
                """
                SELECT t.date,
                       SUM(t.active_power_mw)               AS energy_mwh,
                       SUM(t.active_power_mw * COALESCE(r.price_uah_mwh, 4000)) AS revenue_uah,
                       AVG(t.availability_pct)             AS avg_avail,
                       BOOL_OR(t.status='curtailed_by_TSO') AS had_curtailment
                FROM dispatch.telemetry t
                LEFT JOIN market.rdn_prices r
                  ON r.tenant_id = t.tenant_id
                 AND r.date = t.date
                 AND r.hour = t.hour
                WHERE t.tenant_id = CAST(:tid AS uuid)
                  AND t.asset_id = CAST(:aid AS uuid)
                GROUP BY t.date
                """
            ),
            {"tid": str(asset.tenant_id), "aid": str(asset.asset_id)},
        )
        daily = {row.date: row for row in res.fetchall()}

        rows: list[dict[str, Any]] = []
        for d in dates:
            r = daily.get(d)
            if r is None:
                continue
            energy_mwh = float(r.energy_mwh or 0)
            revenue = float(r.revenue_uah or 0)

            # RES classes earn revenue; consumers "save" by not buying at peak.
            if asset.asset_class in ("СЕС", "ВЕС", "ГПУ", "УЗЕ"):
                # For batteries the energy_mwh nets to ~0; use absolute swing.
                grn_earned = abs(revenue)
                grn_saved = 0.0
                # CO₂ only counted for RES (СЕС, ВЕС). ГПУ produces, doesn't avoid.
                if asset.asset_class in ("СЕС", "ВЕС"):
                    co2 = max(0.0, energy_mwh) * CO2_GRID_FACTOR_TN_PER_MWH
                elif asset.asset_class == "УЗЕ":
                    co2 = abs(energy_mwh) * 0.10  # storage shifts to lower-carbon hours
                else:
                    co2 = 0.0
            else:
                # Consumer — energy is negative; "saved" = avoided peak cost
                grn_earned = 0.0
                grn_saved = abs(revenue) * 0.04  # ~4% of bill saved via flex
                co2 = abs(energy_mwh) * 0.02

            imbalance = float(rng.normal(0.0, asset.capacity_mw * 0.5))
            avail = float(r.avg_avail or 100.0)
            opp = int(np.clip(60 + rng.integers(-20, 30), 0, 100))
            notes = (
                "Подія: обмеження ТСО зафіксовано"
                if r.had_curtailment
                else None
            )

            rows.append(
                {
                    "tenant_id": str(asset.tenant_id),
                    "asset_id": str(asset.asset_id),
                    "date": d,
                    "grn_saved": Decimal(f"{grn_saved:.2f}"),
                    "grn_earned": Decimal(f"{grn_earned:.2f}"),
                    "imbalance": Decimal(f"{imbalance:.4f}"),
                    "co2": Decimal(f"{co2:.3f}"),
                    "avail": Decimal(f"{avail:.2f}"),
                    "opp": opp,
                    "notes": notes,
                }
            )
        if rows:
            result = await conn.execute(stmt, rows)
            total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total
