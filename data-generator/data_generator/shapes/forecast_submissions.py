"""regulatory.forecast_submissions — daily prognosis packages per tenant.

Per ARCHITECTURE.md §3.11.3 event #7:
- Daily for producer-1 (A01 business_type — generation)
- Daily for ci-1 (A04 — consumption)
- Monthly for storage-1 — we still write daily but mark a few as REJECTED.

Status: 90% ACK, 10% SUBMITTED.

§11.19 requires ≥1 ACK per tenant per day where applicable.
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
from data_generator.shapes.assets import W_EIC_POOL


KYIV_OFFSET = timezone(timedelta(hours=3))


def _business_type(segment: str) -> str:
    return {
        "producer": "A01",
        "c-i": "A04",
        "storage": "A60",  # nearest match for storage in ENTSO-E business types
    }[segment]


async def generate(conn: AsyncConnection) -> int:
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    stmt = text(
        """
        INSERT INTO regulatory.forecast_submissions
            (tenant_id, submission_id, submitted_at, submitter_eic, resource_eic,
             bzn_eic, business_type, document_type, process_type, delivery_date,
             resolution_minutes, hourly_volumes_mwh, status, status_changed_at, raw_xml)
        VALUES
            (CAST(:tenant_id AS uuid), :submission_id, :submitted_at,
             :submitter_eic, :resource_eic, :bzn_eic, :biz, :doc, :proc,
             :delivery_date, 60, CAST(:volumes AS NUMERIC(10,4)[]), :status,
             :status_changed_at, :raw_xml)
        ON CONFLICT (tenant_id, submission_id) DO NOTHING
        """
    )
    for tenant in TENANTS:
        rng = get_rng(f"forecast_submissions:{tenant.code}")
        rows: list[dict[str, Any]] = []
        biz = _business_type(tenant.segment)
        for d in dates:
            submitted_at = datetime.combine(
                d - timedelta(days=1), time(9, 30), tzinfo=KYIV_OFFSET
            )
            # 24-hour profile — fake but plausible
            volumes = []
            for h in range(1, 25):
                base = 3.0 if tenant.segment == "storage" else 5.0
                noise = float(rng.uniform(-1.0, 1.0))
                if 8 <= h <= 22:
                    base *= 1.3
                volumes.append(round(max(0.0, base + noise), 4))

            status = "ACK" if float(rng.random()) < 0.92 else "SUBMITTED"
            submission_id = f"FS-{tenant.code}-{d.isoformat()}"
            raw_xml = (
                f"<TimeSeries><mRID>{submission_id}</mRID>"
                f"<businessType>{biz}</businessType></TimeSeries>"
            )
            rows.append(
                {
                    "tenant_id": str(tenant.uuid),
                    "submission_id": submission_id,
                    "submitted_at": submitted_at,
                    "submitter_eic": tenant.participant_eic,
                    "resource_eic": W_EIC_POOL[0],
                    "bzn_eic": BZN_EIC_UA_IPS,
                    "biz": biz,
                    "doc": "A65",
                    "proc": "A01",
                    "delivery_date": d,
                    "volumes": volumes,
                    "status": status,
                    "status_changed_at": submitted_at + timedelta(minutes=15),
                    "raw_xml": raw_xml,
                }
            )
        result = await conn.execute(stmt, rows)
        total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total
