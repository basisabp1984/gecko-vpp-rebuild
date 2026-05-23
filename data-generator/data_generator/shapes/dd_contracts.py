"""ДД — bilateral contracts (long-term OTC).

Per research §4 + ARCHITECTURE.md table targets:
- ~3–6 contracts per tenant. Mix BASE / PEAK / OFFPEAK / INDIVIDUAL.
- Hourly volumes follow the profile.
- Start/end span the window.
"""

from __future__ import annotations

from datetime import date as DateT, timedelta
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


# Mix per tenant: 5 contracts each
PROFILE_MIX = ["BASE", "BASE", "PEAK", "OFFPEAK", "INDIVIDUAL"]

COUNTERPARTIES = [
    ("ДТЕК Енерго", "12345678"),
    ("Укренерго", "12345679"),
    ("Гарантований Покупець", "12345680"),
    ("ВЕС Інвест Україна", "12345681"),
    ("Метінвест Енергоменеджмент", "12345682"),
    ("Епіцентр Енерго", "12345683"),
]


async def generate(conn: AsyncConnection) -> int:
    stmt_contract = text(
        """
        INSERT INTO market.dd_contracts
            (tenant_id, contract_no, counterparty_name, counterparty_edrpou,
             profile_type, start_date, end_date, price_uah_mwh, price_formula,
             total_volume_mwh, bidding_zone_eic, status)
        VALUES
            (CAST(:tenant_id AS uuid), :contract_no, :counterparty_name,
             :counterparty_edrpou, :profile_type, :start_date, :end_date,
             :price_uah_mwh, :price_formula, :total_volume_mwh, :bzn_eic, 'ACTIVE')
        ON CONFLICT (tenant_id, contract_no) DO NOTHING
        RETURNING id, profile_type, total_volume_mwh, start_date, end_date
        """
    )
    stmt_hourly = text(
        """
        INSERT INTO market.dd_contract_hourly_volume
            (contract_id, tenant_id, date, hour, volume_mwh)
        VALUES
            (:contract_id, CAST(:tenant_id AS uuid), :date, :hour, :volume_mwh)
        ON CONFLICT DO NOTHING
        """
    )

    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total_contracts = 0
    total_hourly = 0

    for tenant in TENANTS:
        rng = get_rng(f"dd_contracts:{tenant.code}")
        for idx, profile in enumerate(PROFILE_MIX):
            cp_name, cp_edr = COUNTERPARTIES[idx % len(COUNTERPARTIES)]
            base_price = 4200 + 200 * idx
            indexed = (idx == 1)  # one indexed contract per tenant
            contract_no = f"DD-{tenant.code}-2026-{idx+1:03d}"
            base_vol_per_hour = {
                "BASE": 5.0,
                "PEAK": 8.0,
                "OFFPEAK": 3.0,
                "INDIVIDUAL": 4.0,
            }[profile]
            total_vol = base_vol_per_hour * 24 * len(dates) * 0.6
            params = {
                "tenant_id": str(tenant.uuid),
                "contract_no": contract_no,
                "counterparty_name": cp_name,
                "counterparty_edrpou": cp_edr,
                "profile_type": profile,
                "start_date": SYNTH_DATE_START - timedelta(days=10),
                "end_date": SYNTH_DATE_END + timedelta(days=20),
                "price_uah_mwh": (
                    None if indexed else Decimal(f"{base_price:.2f}")
                ),
                "price_formula": "РДН base + 5%" if indexed else None,
                "total_volume_mwh": Decimal(f"{total_vol:.2f}"),
                "bzn_eic": BZN_EIC_UA_IPS,
            }
            res = await conn.execute(stmt_contract, [params])
            row = res.fetchone() if res.returns_rows else None
            if row is None:
                # Re-fetch existing
                existing = await conn.execute(
                    text(
                        "SELECT id, profile_type FROM market.dd_contracts "
                        "WHERE tenant_id=CAST(:tid AS uuid) AND contract_no=:cn"
                    ),
                    {"tid": str(tenant.uuid), "cn": contract_no},
                )
                row = existing.fetchone()
                if row is None:
                    continue
            else:
                total_contracts += 1

            # Hourly volumes
            hourly_rows: list[dict[str, Any]] = []
            for d in dates:
                weekday = d.weekday() < 5
                for hour in range(1, 25):
                    if profile == "BASE":
                        v = base_vol_per_hour
                    elif profile == "PEAK":
                        v = base_vol_per_hour if (weekday and 8 <= hour <= 22) else 0.0
                    elif profile == "OFFPEAK":
                        v = base_vol_per_hour if (hour <= 7 or hour >= 23) else 0.0
                    else:  # INDIVIDUAL — flexible customer curve
                        # Shape mimics a process load — peak around 10-15h
                        cf = 0.4 + 0.6 * np.sin(max(0.0, (hour - 6) / 12 * np.pi)) ** 2
                        v = base_vol_per_hour * float(cf)
                        v *= float(1.0 + rng.normal(0.0, 0.08))
                    if v > 0:
                        hourly_rows.append(
                            {
                                "contract_id": row.id,
                                "tenant_id": str(tenant.uuid),
                                "date": d,
                                "hour": hour,
                                "volume_mwh": Decimal(f"{max(0.0, v):.3f}"),
                            }
                        )
            if hourly_rows:
                res2 = await conn.execute(stmt_hourly, hourly_rows)
                total_hourly += (
                    (res2.rowcount if res2.rowcount and res2.rowcount > 0 else len(hourly_rows))
                )

    return total_contracts + total_hourly
