"""Bid history.

Per architect targets ~6,480 rows total. State distribution:
70% ACCEPTED, 15% PARTIAL, 10% ACTIVE, 5% REJECTED.

For each tenant × day, we generate ~24 RDN bids matching the delivery hours.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid5, UUID

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    SYNTH_DATE_END,
    SYNTH_DATE_START,
    TENANTS,
    date_range_inclusive,
)
from data_generator.rng import get_rng
from data_generator.shapes.assets import W_EIC_POOL, assets_for_tenant


KYIV_OFFSET = timezone(timedelta(hours=3))
BID_NS = UUID("b1d00000-0000-0000-0000-000000000000")


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
        INSERT INTO market.bids
            (tenant_id, bid_id, market, delivery_date, hour, side, bid_type,
             volume_mwh, price_uah_mwh, technology_type, participant_eic,
             resource_eic, submitted_at, state, accepted_volume_mwh,
             clearing_price, settlement_amount)
        VALUES
            (CAST(:tenant_id AS uuid), :bid_id, :market, :delivery_date, :hour,
             :side, :bid_type, :volume_mwh, :price_uah_mwh, :tech, :pe_eic,
             :res_eic, :submitted_at, :state, :acc_vol, :clear_p, :sett_amt)
        ON CONFLICT (tenant_id, bid_id) DO NOTHING
        """
    )
    state_choices = ["ACCEPTED"] * 70 + ["PARTIAL"] * 15 + ["ACTIVE"] * 10 + ["REJECTED"] * 5

    for tenant in TENANTS:
        rdn_map = await _fetch_rdn(conn, str(tenant.uuid))
        rng = get_rng(f"bids:{tenant.code}")
        side_bias = {"producer": 0.80, "c-i": 0.20, "storage": 0.55}[tenant.segment]
        tenant_assets = assets_for_tenant(tenant.uuid)
        if not tenant_assets:
            continue
        rows: list[dict[str, Any]] = []
        for d in dates:
            for hour in range(1, 25):
                rdn = rdn_map.get((d, hour), 4000.0)
                # One RDN bid per hour, plus occasional VDR/BR follow-up
                for market in ("RDN", "VDR"):
                    if market == "VDR" and float(rng.random()) > 0.30:
                        continue
                    side = "SELL" if float(rng.random()) < side_bias else "BUY"
                    bid_price = rdn * float(rng.uniform(0.85, 1.15))
                    volume = round(float(rng.uniform(0.5, 6.0)), 3)
                    state = state_choices[int(rng.integers(0, len(state_choices)))]
                    acc_vol = (
                        Decimal(f"{volume:.3f}")
                        if state == "ACCEPTED"
                        else Decimal(f"{volume * float(rng.uniform(0.3, 0.8)):.3f}")
                        if state == "PARTIAL"
                        else None
                    )
                    clear_p = (
                        Decimal(f"{rdn:.2f}")
                        if state in ("ACCEPTED", "PARTIAL")
                        else None
                    )
                    sett_amt = (
                        Decimal(f"{(float(acc_vol) * float(clear_p)):.2f}")
                        if acc_vol is not None and clear_p is not None
                        else None
                    )
                    asset = tenant_assets[int(rng.integers(0, len(tenant_assets)))]
                    bid_id = f"{market}-{tenant.code}-{d.isoformat()}-h{hour:02d}-{side[0]}"
                    submitted_at = datetime.combine(d, time(0, 0), tzinfo=KYIV_OFFSET) - timedelta(
                        hours=int(rng.integers(8, 18))
                    )
                    rows.append(
                        {
                            "tenant_id": str(tenant.uuid),
                            "bid_id": bid_id,
                            "market": market,
                            "delivery_date": d,
                            "hour": hour,
                            "side": side,
                            "bid_type": "SIMPLE",
                            "volume_mwh": Decimal(f"{volume:.3f}"),
                            "price_uah_mwh": Decimal(f"{bid_price:.2f}"),
                            "tech": asset.technology_type,
                            "pe_eic": tenant.participant_eic,
                            "res_eic": W_EIC_POOL[
                                int(rng.integers(0, len(W_EIC_POOL)))
                            ],
                            "submitted_at": submitted_at,
                            "state": state,
                            "acc_vol": acc_vol,
                            "clear_p": clear_p,
                            "sett_amt": sett_amt,
                        }
                    )
        if rows:
            result = await conn.execute(stmt, rows)
            total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total
