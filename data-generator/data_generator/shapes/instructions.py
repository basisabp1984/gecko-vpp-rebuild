"""Dispatch instructions + acks.

For each setpoint we generated, write an instruction + ack (96% ack, 4% timeout).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.rng import get_rng


async def generate(conn: AsyncConnection) -> int:
    rng = get_rng("instructions")
    # Fetch setpoints
    res = await conn.execute(
        text(
            """
            SELECT id, tenant_id, asset_id, effective_from, target_power_mw, reason
            FROM dispatch.setpoints
            ORDER BY id
            """
        )
    )
    setpoints = res.fetchall()
    if not setpoints:
        return 0

    inst_stmt = text(
        """
        INSERT INTO dispatch.instructions
            (tenant_id, setpoint_id, asset_id, instruction_kind, payload,
             queued_at, dispatched_at, priority)
        VALUES
            (CAST(:tenant_id AS uuid), :setpoint_id, CAST(:asset_id AS uuid),
             :kind, CAST(:payload AS jsonb), :queued, :dispatched, :priority)
        RETURNING id
        """
    )
    ack_stmt = text(
        """
        INSERT INTO dispatch.instruction_acks
            (instruction_id, tenant_id, acknowledged_at, ack_status, ack_payload, notes)
        VALUES
            (:instruction_id, CAST(:tenant_id AS uuid), :ack_at, :status,
             CAST(:ack_payload AS jsonb), :notes)
        ON CONFLICT (instruction_id) DO NOTHING
        """
    )

    import json

    inst_count = 0
    ack_count = 0
    for sp in setpoints:
        kind = (
            "curtail"
            if sp.reason == "curtailment"
            else "setpoint"
        )
        payload = {
            "target_mw": float(sp.target_power_mw),
            "ramp_seconds": 60,
        }
        queued = sp.effective_from - timedelta(minutes=5)
        dispatched = sp.effective_from - timedelta(seconds=10)
        priority = 3 if kind == "curtail" else 5

        res = await conn.execute(
            inst_stmt,
            [
                {
                    "tenant_id": str(sp.tenant_id),
                    "setpoint_id": sp.id,
                    "asset_id": str(sp.asset_id),
                    "kind": kind,
                    "payload": json.dumps(payload),
                    "queued": queued,
                    "dispatched": dispatched,
                    "priority": priority,
                }
            ],
        )
        inserted = res.fetchone()
        if inserted is None:
            continue
        inst_id = inserted.id
        inst_count += 1

        ack_status = "timeout" if float(rng.random()) < 0.04 else "ack"
        ack_at = dispatched + timedelta(seconds=int(rng.integers(2, 30)))
        ack_payload = {"latency_ms": int(rng.integers(150, 4000))}
        notes = None if ack_status == "ack" else "controller heartbeat lost"
        res2 = await conn.execute(
            ack_stmt,
            [
                {
                    "instruction_id": inst_id,
                    "tenant_id": str(sp.tenant_id),
                    "ack_at": ack_at,
                    "status": ack_status,
                    "ack_payload": json.dumps(ack_payload),
                    "notes": notes,
                }
            ],
        )
        ack_count += res2.rowcount if res2.rowcount is not None else 1
    return inst_count + ack_count
