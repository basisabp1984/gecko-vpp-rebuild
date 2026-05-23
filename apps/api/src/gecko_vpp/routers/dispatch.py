"""Dispatch router: setpoints, telemetry, instructions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.envelope import build_success
from gecko_vpp.common.errors import NotFound
from gecko_vpp.common.pagination import (
    DateRange,
    Pagination,
    date_range_dep,
    pagination_dep,
)
from gecko_vpp.deps import get_session, get_tenant_id
from gecko_vpp.models.dispatch import (
    Instruction,
    InstructionAck,
    Setpoint,
    Telemetry,
)
from gecko_vpp.schemas.dispatch import (
    InstructionAckIn,
    InstructionAckOut,
    InstructionOut,
    SetpointIssueIn,
    SetpointOut,
    TelemetryOut,
)

router = APIRouter(prefix="/api/v1/dispatch", tags=["dispatch"])


@router.get("/setpoints", operation_id="dispatch.setpoints.list")
async def list_setpoints(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    asset_id: UUID | None = Query(None),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    start = datetime.combine(date_range.date_start, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(date_range.date_end, datetime.max.time(), tzinfo=timezone.utc)
    q = (
        select(Setpoint)
        .where(Setpoint.effective_from >= start)
        .where(Setpoint.effective_from <= end)
    )
    if asset_id:
        q = q.where(Setpoint.asset_id == asset_id)
    q = q.order_by(Setpoint.effective_from.desc()).offset(pagination.offset).limit(
        pagination.per_page
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [SetpointOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.post("/setpoints", operation_id="dispatch.setpoints.issue", status_code=201)
async def issue_setpoint(
    body: SetpointIssueIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    new_sp = Setpoint(
        tenant_id=UUID(tenant_id),
        asset_id=body.asset_id,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        target_power_mw=body.target_power_mw,
        target_soc_pct=body.target_soc_pct,
        reason=body.reason,
        issued_by=body.issued_by,
        state="pending",
    )
    session.add(new_sp)
    await session.flush()
    await session.refresh(new_sp)
    return build_success(
        SetpointOut.model_validate(new_sp).model_dump(mode="json"),
        tenant_id=tenant_id,
    )


@router.get("/telemetry", operation_id="dispatch.telemetry.list")
async def list_telemetry(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    asset_id: UUID | None = Query(None),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = (
        select(Telemetry)
        .where(Telemetry.date >= date_range.date_start)
        .where(Telemetry.date <= date_range.date_end)
    )
    if asset_id:
        q = q.where(Telemetry.asset_id == asset_id)
    q = q.order_by(Telemetry.interval_start.desc()).offset(pagination.offset).limit(
        min(pagination.per_page, 1000)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [TelemetryOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/instructions", operation_id="dispatch.instructions.list")
async def list_instructions(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    start = datetime.combine(date_range.date_start, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(date_range.date_end, datetime.max.time(), tzinfo=timezone.utc)
    q = (
        select(Instruction)
        .where(Instruction.queued_at >= start)
        .where(Instruction.queued_at <= end)
        .order_by(Instruction.queued_at.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [InstructionOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.post(
    "/instructions/{instruction_id}/ack",
    operation_id="dispatch.instructions.ack",
)
async def ack_instruction(
    instruction_id: int,
    body: InstructionAckIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    # Ensure the instruction exists & is visible (RLS).
    res = await session.execute(
        select(Instruction).where(Instruction.id == instruction_id)
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise NotFound("Instruction not found")

    ack = InstructionAck(
        instruction_id=instruction_id,
        tenant_id=UUID(tenant_id),
        ack_status=body.ack_status,
        ack_payload=body.ack_payload,
        notes=body.notes,
    )
    session.add(ack)
    await session.flush()
    await session.refresh(ack)
    return build_success(
        InstructionAckOut.model_validate(ack).model_dump(mode="json"),
        tenant_id=tenant_id,
    )
