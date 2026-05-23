"""Setpoint history — ~5 per day per asset, matching telemetry behaviour."""

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

REASONS = (
    "arbitrage",
    "aFRR-up",
    "curtailment",
    "manual",
    "schedule-update",
)


async def generate(conn: AsyncConnection) -> int:
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    stmt = text(
        """
        INSERT INTO dispatch.setpoints
            (tenant_id, asset_id, issued_at, effective_from, effective_to,
             target_power_mw, target_soc_pct, reason, issued_by, state)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid),
             :issued_at, :eff_from, :eff_to,
             :target_mw, :target_soc, :reason, :issued_by, :state)
        """
    )
    for asset in ALL_ASSETS:
        rng = get_rng(f"setpoints:{asset.code}")
        rows: list[dict[str, Any]] = []
        for d in dates:
            n = int(rng.integers(3, 8))
            for _ in range(n):
                start_h = int(rng.integers(0, 23))
                dur_h = int(rng.integers(1, 4))
                start_dt = datetime.combine(d, time(start_h, 0), tzinfo=KYIV_OFFSET)
                end_dt = start_dt + timedelta(hours=dur_h)
                issued_dt = start_dt - timedelta(minutes=int(rng.integers(5, 60)))
                target_mw = round(asset.capacity_mw * float(rng.uniform(0.0, 1.0)), 3)
                target_soc = (
                    Decimal(f"{float(rng.uniform(20, 80)):.2f}")
                    if asset.asset_class == "УЗЕ"
                    else None
                )
                reason = REASONS[int(rng.integers(0, len(REASONS)))]
                rows.append(
                    {
                        "tenant_id": str(asset.tenant_id),
                        "asset_id": str(asset.asset_id),
                        "issued_at": issued_dt,
                        "eff_from": start_dt,
                        "eff_to": end_dt,
                        "target_mw": Decimal(f"{target_mw:.3f}"),
                        "target_soc": target_soc,
                        "reason": reason,
                        "issued_by": "synth-bot",
                        "state": "done",
                    }
                )
        if rows:
            result = await conn.execute(stmt, rows)
            total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total
