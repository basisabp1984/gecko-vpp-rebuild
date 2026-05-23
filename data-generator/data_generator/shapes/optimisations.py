"""ems.optimisation_runs — ~30 pre-seeded runs across the window."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    SYNTH_DATE_END,
    SYNTH_DATE_START,
    TENANTS,
    date_range_inclusive,
)
from data_generator.rng import get_rng


KYIV_OFFSET = timezone(timedelta(hours=3))
SCENARIOS = ("arbitrage_default", "frequency_response", "peak_shaving", "ancillary_max")


async def generate(conn: AsyncConnection) -> int:
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    stmt = text(
        """
        INSERT INTO ems.optimisation_runs
            (tenant_id, requested_by, requested_at, completed_at, scenario,
             inputs_hash, inputs, recommendations, expected_uplift_uah,
             risk_flags, confidence_pct, duration_ms)
        VALUES
            (CAST(:tenant_id AS uuid), NULL, :req_at, :done_at, :scenario,
             :inputs_hash, CAST(:inputs AS jsonb), CAST(:recs AS jsonb),
             :uplift, CAST(:risks AS jsonb), :conf, :dur_ms)
        """
    )
    total = 0
    for tenant in TENANTS:
        rng = get_rng(f"optimisations:{tenant.code}")
        rows: list[dict[str, Any]] = []
        # ~10 per tenant → 30 total
        sample_days = list(dates[::3])[:10]
        for d in sample_days:
            scenario = SCENARIOS[int(rng.integers(0, len(SCENARIOS)))]
            req_at = datetime.combine(d, time(8, 30), tzinfo=KYIV_OFFSET)
            dur_ms = int(rng.integers(800, 4500))
            done_at = req_at + timedelta(milliseconds=dur_ms)
            inputs = {
                "scenario": scenario,
                "window_date": d.isoformat(),
                "horizon_hours": 24,
            }
            inputs_str = json.dumps(inputs, sort_keys=True)
            inputs_hash = hashlib.sha256(inputs_str.encode()).hexdigest()
            recs = {
                "actions": [
                    {"asset": "polyana-ses-1", "action": "shift_to_evening", "delta_mwh": 1.2},
                    {"asset": "dnipro-uze-1", "action": "discharge_at_peak", "delta_mwh": 4.5},
                ],
                "rationale": "Прогнозований вечірній пік сумісно з достатнім SOC батареї.",
            }
            uplift = float(rng.uniform(8000, 65000))
            risks = []
            if float(rng.random()) < 0.3:
                risks.append({"flag": "forecast_uncertainty", "level": "medium"})
            conf = float(rng.uniform(72, 96))
            rows.append(
                {
                    "tenant_id": str(tenant.uuid),
                    "req_at": req_at,
                    "done_at": done_at,
                    "scenario": scenario,
                    "inputs_hash": inputs_hash,
                    "inputs": json.dumps(inputs, ensure_ascii=False),
                    "recs": json.dumps(recs, ensure_ascii=False),
                    "uplift": Decimal(f"{uplift:.2f}"),
                    "risks": json.dumps(risks, ensure_ascii=False),
                    "conf": Decimal(f"{conf:.2f}"),
                    "dur_ms": dur_ms,
                }
            )
        if rows:
            result = await conn.execute(stmt, rows)
            total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total
