"""ВДР (intraday market) trades.

Continuous-trade fact rows. Per research_market_data_shape.md §2:
- ~30 trades/day per tenant.
- Prices track РДН ±10–20% (occasional ±30% outliers near gate).
- Counterparty codes: CP-001 .. CP-040.
- Sides BUY/SELL roughly balanced (per-tenant slight bias by segment).
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    BZN_EIC_UA_IPS,
    SYNTH_DATE_END,
    SYNTH_DATE_START,
    TENANTS,
    date_range_inclusive,
)
from data_generator.rng import get_rng
from data_generator.shapes.assets import W_EIC_POOL, assets_for_tenant


KYIV_OFFSET = timezone(timedelta(hours=3))

TRADES_PER_DAY = 30


async def _fetch_rdn(conn: AsyncConnection, tenant_id: str) -> dict[tuple, float]:
    res = await conn.execute(
        text(
            """
            SELECT date, hour, price_uah_mwh
            FROM market.rdn_prices
            WHERE tenant_id = CAST(:tid AS uuid)
            """
        ),
        {"tid": tenant_id},
    )
    return {(r.date, r.hour): float(r.price_uah_mwh) for r in res}


async def generate(conn: AsyncConnection) -> int:
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    stmt = text(
        """
        INSERT INTO market.vdr_trades
            (tenant_id, trade_id, executed_at, delivery_date, delivery_hour,
             volume_mwh, price_uah_mwh, side, counterparty_code,
             resource_eic, bidding_zone_eic)
        VALUES
            (CAST(:tenant_id AS uuid), :trade_id, :executed_at,
             :delivery_date, :delivery_hour,
             :volume_mwh, :price_uah_mwh, :side, :counterparty_code,
             :resource_eic, :bzn_eic)
        ON CONFLICT (tenant_id, trade_id) DO NOTHING
        """
    )
    counterparties = [f"CP-{i:03d}" for i in range(1, 41)]

    for tenant in TENANTS:
        rdn_map = await _fetch_rdn(conn, str(tenant.uuid))
        rng = get_rng(f"vdr_trades:{tenant.code}")
        # Side bias by segment
        sell_bias = {"producer": 0.70, "c-i": 0.30, "storage": 0.55}[tenant.segment]
        tenant_assets = assets_for_tenant(tenant.uuid)
        rows: list[dict[str, Any]] = []
        for d in dates:
            for tn in range(TRADES_PER_DAY):
                # Random delivery hour 1..24 with afternoon/evening peak bias
                delivery_hour = int(rng.choice(
                    np.arange(1, 25),
                    p=_hour_weight_dist(),
                ))
                rdn_price = rdn_map.get((d, delivery_hour), 4000.0)
                # ±10–20% with occasional ±30% outliers
                if float(rng.random()) < 0.08:
                    spread = float(rng.uniform(-0.30, 0.30))
                else:
                    spread = float(rng.uniform(-0.18, 0.18))
                price = max(50.0, rdn_price * (1.0 + spread))

                side = "SELL" if float(rng.random()) < sell_bias else "BUY"
                volume_mwh = round(float(rng.uniform(0.5, 8.0)), 3)
                # Execute the trade some time on D-1 evening → D-1 minutes before delivery
                exec_dt = datetime.combine(d, time(0, 0), tzinfo=KYIV_OFFSET) - timedelta(
                    hours=int(rng.integers(0, 18)),
                    minutes=int(rng.integers(0, 60)),
                )
                cp = counterparties[int(rng.integers(0, len(counterparties)))]
                # Resource EIC: pick from tenant's assets (or first W if no asset)
                if tenant_assets:
                    res_eic = W_EIC_POOL[int(rng.integers(0, len(W_EIC_POOL)))]
                else:
                    res_eic = W_EIC_POOL[0]
                trade_id = (
                    f"VDR-{tenant.code}-{d.isoformat()}-{tn:03d}"
                )
                rows.append(
                    {
                        "tenant_id": str(tenant.uuid),
                        "trade_id": trade_id,
                        "executed_at": exec_dt,
                        "delivery_date": d,
                        "delivery_hour": delivery_hour,
                        "volume_mwh": Decimal(f"{volume_mwh:.3f}"),
                        "price_uah_mwh": Decimal(f"{price:.2f}"),
                        "side": side,
                        "counterparty_code": cp,
                        "resource_eic": res_eic,
                        "bzn_eic": BZN_EIC_UA_IPS,
                    }
                )
        result = await conn.execute(stmt, rows)
        total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total


def _hour_weight_dist() -> np.ndarray:
    """Bias hours toward morning + evening peaks (matches РДН demand shape)."""
    w = np.array(
        [0.5, 0.4, 0.3, 0.3, 0.3, 0.4, 0.6, 1.0,  # 1..8
         1.4, 1.5, 1.3, 1.0, 0.9, 0.9, 1.0, 1.2,  # 9..16
         1.4, 1.7, 2.0, 2.1, 1.8, 1.3, 0.9, 0.7], # 17..24
        dtype=float,
    )
    return w / w.sum()
