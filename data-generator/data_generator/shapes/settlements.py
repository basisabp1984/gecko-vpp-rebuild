"""regulatory.settlement_statements + lines.

Per ARCHITECTURE.md §3.11.3 #5: Apr 2026 + May 2026 statements per tenant
× counterparty. ~12 total (3 tenants × 2 months × 2 counterparties).
"""

from __future__ import annotations

from datetime import date as DateT, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import TENANTS
from data_generator.rng import get_rng
from data_generator.shapes.assets import W_EIC_POOL, assets_for_tenant


COUNTERPARTIES_BY_SEGMENT = {
    "producer": [
        ("ГП — Гарантований Покупець", "33555000"),
        ("ДТЕК Енерго (контракт)", "23360726"),
    ],
    "c-i": [
        ("ДТЕК Київські Електромережі", "32979649"),
        ("ВЕС Інвест Україна", "12345681"),
    ],
    "storage": [
        ("Укренерго (БР послуги)", "00100227"),
        ("УЕБ — арбітражні розрахунки", "12345699"),
    ],
}


async def generate(conn: AsyncConnection) -> int:
    stmt_st = text(
        """
        INSERT INTO regulatory.settlement_statements
            (tenant_id, statement_no, counterparty, counterparty_edrpou,
             contract_no, period_year, period_month, period_start, period_end,
             volume_total_mwh, amount_net_uah, vat_rate, amount_vat_uah,
             amount_gross_uah, payment_due_date, status)
        VALUES
            (CAST(:tenant_id AS uuid), :statement_no, :counterparty,
             :counterparty_edrpou, :contract_no, :year, :month, :p_start,
             :p_end, :volume, :net, :vat_rate, :vat, :gross, :due, :status)
        ON CONFLICT (tenant_id, statement_no) DO NOTHING
        RETURNING id
        """
    )
    stmt_ln = text(
        """
        INSERT INTO regulatory.settlement_statement_lines
            (statement_id, tenant_id, line_no, asset_eic, asset_name,
             technology_type, volume_mwh, tariff_uah_mwh, amount_uah)
        VALUES
            (:statement_id, CAST(:tenant_id AS uuid), :line_no, :asset_eic,
             :asset_name, :tech, :volume, :tariff, :amount)
        """
    )

    total_st = 0
    total_ln = 0
    for tenant in TENANTS:
        rng = get_rng(f"settlements:{tenant.code}")
        tenant_assets = list(assets_for_tenant(tenant.uuid))
        counterparties = COUNTERPARTIES_BY_SEGMENT[tenant.segment]
        for (year, month) in [(2026, 4), (2026, 5)]:
            p_start = DateT(year, month, 1)
            if month == 12:
                p_end = DateT(year + 1, 1, 1) - timedelta(days=1)
            else:
                p_end = DateT(year, month + 1, 1) - timedelta(days=1)
            for cp_idx, (cp_name, cp_edr) in enumerate(counterparties):
                statement_no = f"AKT-{tenant.code}-{year:04d}-{month:02d}-{cp_idx+1:02d}"
                volume = float(rng.uniform(800, 3500))
                tariff = float(rng.uniform(3500, 5500))
                net = volume * tariff
                vat_rate = 0.20
                vat = round(net * vat_rate, 2)
                gross = round(net + vat, 2)
                due = p_end + timedelta(days=14)
                res = await conn.execute(
                    stmt_st,
                    [
                        {
                            "tenant_id": str(tenant.uuid),
                            "statement_no": statement_no,
                            "counterparty": cp_name,
                            "counterparty_edrpou": cp_edr,
                            "contract_no": f"DD-{tenant.code}-2026-{cp_idx+1:03d}",
                            "year": year,
                            "month": month,
                            "p_start": p_start,
                            "p_end": p_end,
                            "volume": Decimal(f"{volume:.4f}"),
                            "net": Decimal(f"{net:.2f}"),
                            "vat_rate": Decimal(f"{vat_rate:.2f}"),
                            "vat": Decimal(f"{vat:.2f}"),
                            "gross": Decimal(f"{gross:.2f}"),
                            "due": due,
                            "status": "SIGNED",
                        }
                    ],
                )
                inserted = res.fetchone()
                if inserted is None:
                    existing = await conn.execute(
                        text(
                            "SELECT id FROM regulatory.settlement_statements "
                            "WHERE tenant_id=CAST(:tid AS uuid) AND statement_no=:sn"
                        ),
                        {"tid": str(tenant.uuid), "sn": statement_no},
                    )
                    inserted = existing.fetchone()
                    if inserted is None:
                        continue
                else:
                    total_st += 1
                statement_id = inserted.id

                # Lines: 1 per active asset (cap to 5)
                line_rows: list[dict[str, Any]] = []
                remaining_vol = volume
                eligible = [a for a in tenant_assets if a.asset_class != "Споживач"][:5]
                if not eligible:
                    eligible = tenant_assets[:5]
                for li, asset in enumerate(eligible):
                    if li == len(eligible) - 1:
                        line_vol = remaining_vol
                    else:
                        line_vol = volume * float(rng.uniform(0.10, 0.30))
                        remaining_vol -= line_vol
                    line_rows.append(
                        {
                            "statement_id": statement_id,
                            "tenant_id": str(tenant.uuid),
                            "line_no": li + 1,
                            "asset_eic": W_EIC_POOL[li % len(W_EIC_POOL)],
                            "asset_name": asset.display_name,
                            "tech": asset.technology_type,
                            "volume": Decimal(f"{max(0.001, line_vol):.4f}"),
                            "tariff": Decimal(f"{tariff:.2f}"),
                            "amount": Decimal(f"{max(0.0, line_vol) * tariff:.2f}"),
                        }
                    )
                if line_rows:
                    res2 = await conn.execute(stmt_ln, line_rows)
                    total_ln += (
                        (res2.rowcount if res2.rowcount and res2.rowcount > 0 else len(line_rows))
                    )
    return total_st + total_ln
