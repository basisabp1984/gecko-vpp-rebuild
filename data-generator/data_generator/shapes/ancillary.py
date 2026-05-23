"""Ancillary services — offers + activations.

Storage assets (УЗЕ) offer FCR + aFRR_up. Activations happen frequently.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
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


KYIV_OFFSET = timezone(timedelta(hours=3))

SERVICES = ("FCR", "aFRR_up")


async def generate(conn: AsyncConnection) -> int:
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    storage_assets = [a for a in ALL_ASSETS if a.asset_class == "УЗЕ"]

    offer_stmt = text(
        """
        INSERT INTO market.ancillary_offers
            (tenant_id, asset_id, date, hour, service, offered_capacity_mw,
             cleared_capacity_mw, capacity_price_eur_mwh, revenue_capacity_uah)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid), :date, :hour,
             :service, :offered, :cleared, :price, :revenue)
        ON CONFLICT (tenant_id, asset_id, date, hour, service) DO NOTHING
        """
    )
    act_stmt = text(
        """
        INSERT INTO market.ancillary_activations
            (tenant_id, asset_id, service, started_at, ended_at,
             avg_power_mw, energy_mwh, energy_price_uah_mwh, revenue_energy_uah)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid),
             :service, :started_at, :ended_at, :avg_mw, :energy_mwh,
             :energy_price, :revenue)
        """
    )

    for asset in storage_assets:
        rng = get_rng(f"ancillary:{asset.code}")
        offer_rows: list[dict[str, Any]] = []
        act_rows: list[dict[str, Any]] = []
        for d in dates:
            for hour in range(1, 25):
                for svc in SERVICES:
                    offered = round(float(rng.uniform(0.2, 0.5)) * asset.capacity_mw, 3)
                    cleared = offered * float(rng.uniform(0.5, 1.0))
                    price_eur = round(float(rng.uniform(0.4, 1.5)), 4)
                    # Revenue: capacity_mw × hours (1) × price × 40 UAH/EUR
                    revenue = cleared * price_eur * 40
                    offer_rows.append(
                        {
                            "tenant_id": str(asset.tenant_id),
                            "asset_id": str(asset.asset_id),
                            "date": d,
                            "hour": hour,
                            "service": svc,
                            "offered": Decimal(f"{offered:.3f}"),
                            "cleared": Decimal(f"{cleared:.3f}"),
                            "price": Decimal(f"{price_eur:.4f}"),
                            "revenue": Decimal(f"{revenue:.2f}"),
                        }
                    )

            # Activations: 3–8 aFRR events per day per battery, 30s-5min
            n_acts = int(rng.integers(3, 9))
            for _ in range(n_acts):
                start_h = int(rng.integers(7, 22))
                start_m = int(rng.integers(0, 60))
                dur_sec = int(rng.integers(30, 300))
                start_dt = datetime.combine(d, time(start_h, start_m), tzinfo=KYIV_OFFSET)
                end_dt = start_dt + timedelta(seconds=dur_sec)
                avg_mw = round(asset.capacity_mw * float(rng.uniform(0.05, 0.20)), 3)
                energy_mwh = round(avg_mw * dur_sec / 3600, 4)
                e_price = round(float(rng.uniform(4500, 7500)), 2)
                act_rows.append(
                    {
                        "tenant_id": str(asset.tenant_id),
                        "asset_id": str(asset.asset_id),
                        "service": "aFRR_up",
                        "started_at": start_dt,
                        "ended_at": end_dt,
                        "avg_mw": Decimal(f"{avg_mw:.3f}"),
                        "energy_mwh": Decimal(f"{energy_mwh:.4f}"),
                        "energy_price": Decimal(f"{e_price:.2f}"),
                        "revenue": Decimal(f"{energy_mwh * e_price:.2f}"),
                    }
                )

        if offer_rows:
            res = await conn.execute(offer_stmt, offer_rows)
            total += (res.rowcount if res.rowcount and res.rowcount > 0 else len(offer_rows))
        if act_rows:
            res = await conn.execute(act_stmt, act_rows)
            total += (res.rowcount if res.rowcount and res.rowcount > 0 else len(act_rows))
    return total
