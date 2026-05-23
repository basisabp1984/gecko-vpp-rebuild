"""Regulatory router: settlements, signed_documents (КЕП stub), regulator events, submissions."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.envelope import build_success, now_kyiv_iso
from gecko_vpp.common.errors import NotFound
from gecko_vpp.common.pagination import (
    DateRange,
    Pagination,
    date_range_dep,
    pagination_dep,
)
from gecko_vpp.deps import get_session, get_tenant_id
from gecko_vpp.models.core import Tenant
from gecko_vpp.models.regulatory import (
    ForecastSubmission,
    RegulatorEvent,
    SettlementStatement,
    SettlementStatementLine,
    SignedDocument,
)
from gecko_vpp.schemas.ems import ForecastSubmissionOut
from gecko_vpp.schemas.regulatory import (
    RegulatorEventOut,
    SettlementLineOut,
    SettlementOut,
    SignedDocumentBadgeOut,
    SignedDocumentOut,
    SignBadgeFields,
)

router = APIRouter(prefix="/api/v1/regulatory", tags=["regulatory"])


@router.get("/settlements", operation_id="regulatory.settlements.list")
async def list_settlements(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    period: str | None = Query(None, description="YYYY-MM"),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = select(SettlementStatement)
    if period:
        try:
            y, m = period.split("-")
            q = q.where(SettlementStatement.period_year == int(y)).where(
                SettlementStatement.period_month == int(m)
            )
        except (ValueError, AttributeError):
            pass
    q = q.order_by(
        SettlementStatement.period_year.desc(),
        SettlementStatement.period_month.desc(),
    ).offset(pagination.offset).limit(pagination.per_page)
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [SettlementOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get(
    "/settlements/{settlement_id}",
    operation_id="regulatory.settlements.detail",
)
async def get_settlement(
    settlement_id: int,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    res = await session.execute(
        select(SettlementStatement).where(SettlementStatement.id == settlement_id)
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise NotFound("Settlement not found")
    lres = await session.execute(
        select(SettlementStatementLine)
        .where(SettlementStatementLine.statement_id == settlement_id)
        .order_by(SettlementStatementLine.line_no)
    )
    lines = list(lres.scalars().all())
    out = SettlementOut.model_validate(row)
    out_dict = out.model_dump(mode="json")
    out_dict["lines"] = [
        SettlementLineOut.model_validate(line).model_dump(mode="json")
        for line in lines
    ]
    return build_success(out_dict, tenant_id=tenant_id)


@router.post(
    "/documents/{ref_id}/sign",
    operation_id="regulatory.documents.sign",
)
async def sign_document(
    ref_id: int,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """КЕП stub. Marks the doc is_demo_stub=TRUE. ref_table defaults to 'settlement_statements'."""
    # Resolve tenant to pull edrpou
    tres = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant_row = tres.scalar_one()

    # Compute fake sha256
    payload = f"{ref_id}|{tenant_row.edrpou}|{now_kyiv_iso()}"
    fake_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    signed_at = datetime.now(tz=timezone.utc)
    signer_name = "Радковський А.В."
    signer_edrpou = tenant_row.edrpou
    acsk = "Дія"

    doc = SignedDocument(
        tenant_id=tenant_row.id,
        document_type="SETTLEMENT_ACT",
        document_ref_table="settlement_statements",
        document_ref_id=ref_id,
        signer_name=signer_name,
        signer_position="Директор",
        signer_edrpou=signer_edrpou,
        acsk_name=acsk,
        signature_format="CAdES-X-Long",
        document_hash_sha256=fake_hash,
        signed_at=signed_at,
        p7s_blob=b"DEMO_STUB_P7S_BLOB",
        is_demo_stub=True,
    )
    session.add(doc)
    await session.flush()
    await session.refresh(doc)

    badge = SignedDocumentBadgeOut(
        signed_doc_id=doc.id,
        badge_text=(
            f"Підписано КЕП · {signer_name} · ЄДРПОУ {signer_edrpou} · "
            f"{now_kyiv_iso()}"
        ),
        badge_fields=SignBadgeFields(
            signer_name=signer_name,
            signer_edrpou=signer_edrpou,
            acsk_name=acsk,
            signed_at=now_kyiv_iso(),
            hash_short=f"{fake_hash[:8]}…{fake_hash[-8:]}",
        ),
        is_demo_stub=True,
    )
    return build_success(badge.model_dump(mode="json"), tenant_id=tenant_id)


@router.get("/documents", operation_id="regulatory.documents.list")
async def list_documents(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = (
        select(SignedDocument)
        .order_by(SignedDocument.signed_at.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [SignedDocumentOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/events", operation_id="regulatory.events.list")
async def list_events(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    """regulator_events is read-all across tenants per architect §3.10."""
    q = (
        select(RegulatorEvent)
        .where(RegulatorEvent.issued_at >= date_range.date_start)
        .where(RegulatorEvent.issued_at <= date_range.date_end)
        .order_by(RegulatorEvent.issued_at.desc())
        .limit(200)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [RegulatorEventOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/submissions", operation_id="regulatory.submissions.list")
async def list_submissions(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = (
        select(ForecastSubmission)
        .where(ForecastSubmission.delivery_date >= date_range.date_start)
        .where(ForecastSubmission.delivery_date <= date_range.date_end)
        .order_by(ForecastSubmission.delivery_date.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [ForecastSubmissionOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)
