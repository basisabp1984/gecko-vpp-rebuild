"""regulatory.signed_documents — КЕП-signed stub documents (§11.20).

Per tenant, generate signed documents for:
- Every settlement statement (SETTLEMENT_ACT)
- A few forecast packages (FORECAST_PACKAGE)
- A few reports (REPORT)

All marked is_demo_stub=TRUE. document_hash_sha256 is a real sha256 of
deterministic canonical content. p7s_blob = 64 RNG bytes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import TENANTS
from data_generator.rng import get_rng


KYIV_OFFSET = timezone(timedelta(hours=3))

SIGNER_POOL = (
    ("Радковський А.В.", "директор"),
    ("Петренко О.І.", "комерційний директор"),
    ("Шевченко М.Ю.", "головний бухгалтер"),
    ("Коваленко Л.М.", "фінансовий директор"),
    ("Ткаченко Я.А.", "операційний директор"),
    ("Бойко В.С.", "директор з ринку"),
    ("Гончарук Н.П.", "директор з регулювання"),
    ("Лисенко Д.Г.", "юрист"),
)

ACSK_POOL = ("Дія", "ПриватБанк", "ІДД ДПС", "Ключові системи")


async def generate(conn: AsyncConnection) -> int:
    total = 0
    stmt = text(
        """
        INSERT INTO regulatory.signed_documents
            (tenant_id, document_type, document_ref_table, document_ref_id,
             signer_name, signer_position, signer_edrpou, signer_ipn,
             acsk_name, signature_format, document_hash_sha256, signed_at,
             tsa_provider, cert_serial, cert_valid_until, p7s_blob, is_demo_stub)
        VALUES
            (CAST(:tenant_id AS uuid), :doc_type, :ref_table, :ref_id,
             :signer_name, :signer_position, :signer_edrpou, :signer_ipn,
             :acsk_name, 'CAdES-X-Long', :doc_hash, :signed_at,
             'czo.gov.ua', :cert_serial, :cert_valid, :p7s, TRUE)
        """
    )

    update_st_stmt = text(
        """
        UPDATE regulatory.settlement_statements
        SET signed_doc_id = :doc_id
        WHERE id = :st_id
        """
    )

    # Cache settlement statements per tenant for linking
    res = await conn.execute(
        text(
            """
            SELECT id, tenant_id, statement_no, period_end
            FROM regulatory.settlement_statements
            ORDER BY tenant_id, id
            """
        )
    )
    statements = res.fetchall()

    for tenant in TENANTS:
        rng = get_rng(f"signed_docs:{tenant.code}")
        rows: list[dict[str, Any]] = []
        tenant_stmts = [s for s in statements if str(s.tenant_id) == str(tenant.uuid)]

        # 1. One signed doc per settlement statement
        for st in tenant_stmts:
            signer = SIGNER_POOL[int(rng.integers(0, len(SIGNER_POOL)))]
            canonical = f"SETTLEMENT_ACT|{tenant.code}|{st.statement_no}"
            doc_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            signed_at = datetime.combine(
                st.period_end + timedelta(days=3), time(15, 0), tzinfo=KYIV_OFFSET
            )
            p7s_bytes = bytes(rng.integers(0, 256, size=64).astype(np.uint8))
            cert_serial = f"{int(rng.integers(10**12, 10**13)):x}"
            cert_valid = signed_at.date() + timedelta(days=365)
            rows.append(
                {
                    "tenant_id": str(tenant.uuid),
                    "doc_type": "SETTLEMENT_ACT",
                    "ref_table": "regulatory.settlement_statements",
                    "ref_id": st.id,
                    "signer_name": signer[0],
                    "signer_position": signer[1],
                    "signer_edrpou": tenant.edrpou,
                    "signer_ipn": None,
                    "acsk_name": ACSK_POOL[int(rng.integers(0, len(ACSK_POOL)))],
                    "doc_hash": doc_hash,
                    "signed_at": signed_at,
                    "cert_serial": cert_serial,
                    "cert_valid": cert_valid,
                    "p7s": p7s_bytes,
                    "_link_st_id": st.id,
                }
            )

        # 2. Three FORECAST_PACKAGE per tenant
        for i in range(3):
            signer = SIGNER_POOL[int(rng.integers(0, len(SIGNER_POOL)))]
            canonical = f"FORECAST_PACKAGE|{tenant.code}|{i}"
            doc_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            signed_at = datetime(2026, 5, 10 + i, 11, 0, tzinfo=KYIV_OFFSET)
            p7s_bytes = bytes(rng.integers(0, 256, size=64).astype(np.uint8))
            rows.append(
                {
                    "tenant_id": str(tenant.uuid),
                    "doc_type": "FORECAST_PACKAGE",
                    "ref_table": "regulatory.forecast_submissions",
                    "ref_id": i + 1,
                    "signer_name": signer[0],
                    "signer_position": signer[1],
                    "signer_edrpou": tenant.edrpou,
                    "signer_ipn": None,
                    "acsk_name": ACSK_POOL[int(rng.integers(0, len(ACSK_POOL)))],
                    "doc_hash": doc_hash,
                    "signed_at": signed_at,
                    "cert_serial": f"{int(rng.integers(10**12, 10**13)):x}",
                    "cert_valid": signed_at.date() + timedelta(days=365),
                    "p7s": p7s_bytes,
                    "_link_st_id": None,
                }
            )

        # 3. Two REPORT per tenant
        for i in range(2):
            signer = SIGNER_POOL[int(rng.integers(0, len(SIGNER_POOL)))]
            canonical = f"REPORT|{tenant.code}|{i}"
            doc_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            signed_at = datetime(2026, 5, 20 + i, 17, 30, tzinfo=KYIV_OFFSET)
            p7s_bytes = bytes(rng.integers(0, 256, size=64).astype(np.uint8))
            rows.append(
                {
                    "tenant_id": str(tenant.uuid),
                    "doc_type": "REPORT",
                    "ref_table": "regulatory.signed_documents",
                    "ref_id": i + 1,
                    "signer_name": signer[0],
                    "signer_position": signer[1],
                    "signer_edrpou": tenant.edrpou,
                    "signer_ipn": None,
                    "acsk_name": ACSK_POOL[int(rng.integers(0, len(ACSK_POOL)))],
                    "doc_hash": doc_hash,
                    "signed_at": signed_at,
                    "cert_serial": f"{int(rng.integers(10**12, 10**13)):x}",
                    "cert_valid": signed_at.date() + timedelta(days=365),
                    "p7s": p7s_bytes,
                    "_link_st_id": None,
                }
            )

        # Insert rows one-by-one to capture the RETURNING id for linking
        for row in rows:
            link_st_id = row.pop("_link_st_id")
            res = await conn.execute(
                text(stmt.text + " RETURNING id"),
                [row],
            )
            inserted = res.fetchone()
            if inserted is None:
                continue
            total += 1
            if link_st_id is not None:
                await conn.execute(
                    update_st_stmt,
                    {"doc_id": inserted.id, "st_id": link_st_id},
                )
    return total
