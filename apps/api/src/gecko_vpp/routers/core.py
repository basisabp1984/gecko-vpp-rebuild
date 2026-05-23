"""Core router: healthz, auth, tenants, assets."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.envelope import build_success
from gecko_vpp.common.errors import InvalidTenant, NotFound
from gecko_vpp.common.pagination import (
    DateRange,
    Pagination,
    date_range_dep,
    pagination_dep,
    pagination_meta,
)
from gecko_vpp.config import get_settings
from gecko_vpp.db import get_session_factory
from gecko_vpp.deps import (
    get_current_user,
    get_session,
    get_tenant_id,
)
from gecko_vpp.models.core import Asset, Tenant
from gecko_vpp.models.dispatch import Telemetry
from gecko_vpp.schemas.core import (
    AssetOut,
    AuthMeOut,
    CurrentUserOut,
    SwitchTenantIn,
    TenantOut,
)
from gecko_vpp.schemas.dispatch import TelemetryOut

router = APIRouter(prefix="/api/v1", tags=["core"])


# ---- health ----


@router.get("/healthz", operation_id="core.health.check")
async def healthz() -> dict[str, Any]:
    """No DB; no tenant header required."""
    return build_success({"status": "ok"})


# ---- tenants & auth ----


def _allowed_tenants_set() -> set[str]:
    s = get_settings()
    return {
        s.tenant_producer_uuid.lower(),
        s.tenant_ci_uuid.lower(),
        s.tenant_storage_uuid.lower(),
    }


async def _fetch_tenant_row(session: AsyncSession, tenant_id: str) -> Tenant:
    res = await session.execute(
        select(Tenant).where(Tenant.id == UUID(tenant_id))
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise NotFound("Tenant not found")
    return row


@router.get("/tenants", operation_id="core.tenants.list")
async def list_tenants() -> dict[str, Any]:
    """Lists the 3 demo tenants. Uses an admin session to bypass RLS."""
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            await session.execute(text("SET LOCAL app.is_admin = 'true'"))
            await session.execute(
                text("SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000'")
            )
            res = await session.execute(
                select(Tenant).where(Tenant.id.in_(
                    [UUID(t) for t in _allowed_tenants_set()]
                ))
            )
            rows = list(res.scalars().all())
    return build_success([TenantOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.get("/auth/me", operation_id="core.auth.me")
async def auth_me(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_row = await _fetch_tenant_row(session, tenant_id)
    payload = AuthMeOut(
        tenant_id=tenant_row.id,
        tenant=TenantOut.model_validate(tenant_row),
        current_user=CurrentUserOut(**user),
    )
    return build_success(payload.model_dump(mode="json"), tenant_id=tenant_id)


@router.post("/auth/switch-tenant", operation_id="core.auth.switch_tenant")
async def switch_tenant(body: SwitchTenantIn) -> dict[str, Any]:
    """Validates the requested tenant is one of the 3 demo tenants."""
    allowed = _allowed_tenants_set()
    target_id: str | None = None
    if body.tenant_id is not None:
        if str(body.tenant_id).lower() not in allowed:
            raise InvalidTenant("Tenant not in demo allowlist")
        target_id = str(body.tenant_id)
    elif body.tenant_code is not None:
        # Lookup by code via admin session
        factory = get_session_factory()
        async with factory() as session:
            async with session.begin():
                await session.execute(text("SET LOCAL app.is_admin = 'true'"))
                await session.execute(
                    text("SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000'")
                )
                res = await session.execute(
                    select(Tenant).where(Tenant.code == body.tenant_code)
                )
                row = res.scalar_one_or_none()
                if row is None or str(row.id).lower() not in allowed:
                    raise InvalidTenant("Tenant code not found in demo allowlist")
                target_id = str(row.id)
    else:
        raise InvalidTenant("Provide tenant_id or tenant_code")

    # Fetch and return the row
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            await session.execute(text("SET LOCAL app.is_admin = 'true'"))
            await session.execute(
                text("SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000'")
            )
            res = await session.execute(
                select(Tenant).where(Tenant.id == UUID(target_id))
            )
            row = res.scalar_one()
    return build_success(
        {"tenant_id": target_id, "tenant": TenantOut.model_validate(row).model_dump(mode="json")},
        tenant_id=target_id,
    )


# ---- assets ----


@router.get("/assets", operation_id="core.assets.list")
async def list_assets(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    asset_class: str | None = Query(None),
    asset_type: str | None = Query(None),
    segment: str | None = Query(None),
    active: bool | None = Query(None),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = select(Asset)
    cls = asset_class or asset_type
    if cls:
        q = q.where(Asset.asset_class == cls)
    if active is True:
        q = q.where(Asset.status == "active")
    elif active is False:
        q = q.where(Asset.status != "active")
    # segment filter requires tenant join; pragmatic: filter via tenant
    if segment:
        q = q.join(Tenant, Asset.tenant_id == Tenant.id).where(
            Tenant.segment == segment
        )
    total_res = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_res.scalar_one()
    q = q.order_by(Asset.code).offset(pagination.offset).limit(pagination.per_page)
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [AssetOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(
        data,
        tenant_id=tenant_id,
        extra_meta=pagination_meta(pagination, total),
    )


@router.get("/assets/{asset_id}", operation_id="core.assets.detail")
async def get_asset(
    asset_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    res = await session.execute(select(Asset).where(Asset.id == asset_id))
    row = res.scalar_one_or_none()
    if row is None:
        raise NotFound("Asset not found")
    return build_success(
        AssetOut.model_validate(row).model_dump(mode="json"),
        tenant_id=tenant_id,
    )


@router.get(
    "/assets/{asset_id}/telemetry",
    operation_id="core.assets.telemetry",
)
async def asset_telemetry(
    asset_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    pagination: Annotated[Pagination, Depends(pagination_dep)],
) -> dict[str, Any]:
    q = (
        select(Telemetry)
        .where(Telemetry.asset_id == asset_id)
        .where(Telemetry.date >= date_range.date_start)
        .where(Telemetry.date <= date_range.date_end)
        .order_by(Telemetry.interval_start)
        .offset(pagination.offset)
        .limit(pagination.per_page)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [TelemetryOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)
