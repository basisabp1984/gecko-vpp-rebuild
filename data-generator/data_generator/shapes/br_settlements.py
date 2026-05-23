"""БР (balancing market) settlements.

Per research_market_data_shape.md §3:
- 1-hour settlement period.
- Asymmetric prices: price_short = РДН × 1.2–2.5, price_long = РДН × 0.4–0.8.
- ``our_imbalance_mwh`` ~ N(0, σ * portfolio_nameplate).
- Signed settlement_uah.
- 2026-05-04 imbalance spike day per ARCHITECTURE.md events.
"""

from __future__ import annotations

from datetime import date as DateT
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
from data_generator.shapes.assets import assets_for_tenant


IMBALANCE_SIGMA_FRAC = 0.05  # 5% of nameplate
SPIKE_DAY = DateT(2026, 5, 4)


def _portfolio_nameplate(tenant_code: str) -> float:
    """Cached portfolio total MW for one tenant."""
    from data_generator.shapes.assets import ALL_ASSETS
    return sum(
        a.capacity_mw
        for a in ALL_ASSETS
        if a.asset_class not in ("Споживач",)
        and any(t.code == tenant_code and t.uuid == a.tenant_id for t in TENANTS)
    ) or 10.0


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
        INSERT INTO market.br_settlements
            (tenant_id, date, hour, price_short_uah_mwh, price_long_uah_mwh,
             system_direction, our_imbalance_mwh, settlement_uah, bidding_zone_eic)
        VALUES
            (CAST(:tenant_id AS uuid), :date, :hour,
             :price_short, :price_long, :direction,
             :imbalance_mwh, :settlement_uah, :bzn_eic)
        ON CONFLICT (tenant_id, date, hour) DO NOTHING
        """
    )

    for tenant in TENANTS:
        nameplate = _portfolio_nameplate(tenant.code)
        rdn_map = await _fetch_rdn(conn, str(tenant.uuid))
        rng = get_rng(f"br_settlements:{tenant.code}")
        rows: list[dict[str, Any]] = []
        for d in dates:
            spike = (d == SPIKE_DAY)
            for hour in range(1, 25):
                rdn = rdn_map.get((d, hour), 4000.0)
                # System direction
                r = float(rng.random())
                if r < 0.45:
                    direction = "SHORT"
                elif r < 0.85:
                    direction = "LONG"
                else:
                    direction = "BALANCED"

                # Asymmetric prices around РДН
                price_short = rdn * float(rng.uniform(1.2, 2.5))
                price_long = rdn * float(rng.uniform(0.4, 0.8))

                sigma_mwh = IMBALANCE_SIGMA_FRAC * nameplate
                if spike:
                    sigma_mwh *= 3.0  # spike day amplification
                imb = float(rng.normal(0.0, sigma_mwh))

                # Settlement: signed, depends on direction × our imbalance side
                # Simplified: if our imbalance helps system → favourable price;
                # otherwise penalised.
                if (direction == "SHORT" and imb > 0) or (direction == "LONG" and imb < 0):
                    settle = imb * price_short * 0.95
                elif (direction == "SHORT" and imb < 0):
                    settle = imb * price_short
                elif (direction == "LONG" and imb > 0):
                    settle = imb * price_long
                else:
                    settle = imb * rdn

                rows.append(
                    {
                        "tenant_id": str(tenant.uuid),
                        "date": d,
                        "hour": hour,
                        "price_short": Decimal(f"{price_short:.2f}"),
                        "price_long": Decimal(f"{price_long:.2f}"),
                        "direction": direction,
                        "imbalance_mwh": Decimal(f"{imb:.4f}"),
                        "settlement_uah": Decimal(f"{settle:.2f}"),
                        "bzn_eic": BZN_EIC_UA_IPS,
                    }
                )
        result = await conn.execute(stmt, rows)
        total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total
