"""FastAPI dependencies — tenant injection + DB session with RLS.

Critical security control: every DB session opens a transaction and runs
`SET LOCAL app.tenant_id = <header>` before yielding the connection.

Demo tenants are restricted to the 3 fixed UUIDs from .env.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.errors import InvalidTenant, MissingTenantHeader
from gecko_vpp.config import get_settings
from gecko_vpp.db import get_session_factory


# ---- tenant header ----


def _allowed_tenants() -> set[str]:
    s = get_settings()
    return {
        s.tenant_producer_uuid.lower(),
        s.tenant_ci_uuid.lower(),
        s.tenant_storage_uuid.lower(),
    }


async def get_tenant_id(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
) -> str:
    if not x_tenant_id:
        raise MissingTenantHeader()
    try:
        parsed = UUID(x_tenant_id)
    except (ValueError, TypeError):
        raise InvalidTenant("X-Tenant-Id is not a valid UUID")
    if str(parsed).lower() not in _allowed_tenants():
        raise InvalidTenant(
            "Tenant not in demo allowlist",
            {"allowed": sorted(_allowed_tenants())},
        )
    return str(parsed)


async def get_admin_flag(
    request: Request,
    x_admin: Annotated[str | None, Header(alias="X-Admin")] = None,
) -> bool:
    """True iff X-Admin=true AND path is under /api/v1/admin/."""
    if not x_admin:
        return False
    if x_admin.lower() != "true":
        return False
    return request.url.path.startswith("/api/v1/admin/")


# ---- DB session with RLS GUC ----


async def get_session(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    is_admin: Annotated[bool, Depends(get_admin_flag)] = False,
) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession with SET LOCAL app.tenant_id applied.

    `SET LOCAL` requires being inside a transaction. We open one explicitly,
    commit on success, roll back on exception.
    """
    # tenant_id has been validated as a UUID, safe to interpolate directly.
    # Postgres SET LOCAL does not support bound parameters.
    factory = get_session_factory()
    async with factory() as session:
        try:
            await session.begin()
            await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
            if is_admin:
                await session.execute(text("SET LOCAL app.is_admin = 'true'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_admin_session() -> AsyncIterator[AsyncSession]:
    """Admin session — sets app.is_admin='true', no tenant filter.

    Used by /admin/* endpoints that need cross-tenant visibility. We still
    must run inside a transaction for SET LOCAL semantics.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            await session.begin()
            await session.execute(text("SET LOCAL app.is_admin = 'true'"))
            # Set a sentinel tenant_id so RLS policies that reference it
            # don't crash on NULL — admin policies override via is_admin.
            await session.execute(
                text("SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000'")
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---- mock auth ----


def get_current_user() -> dict[str, str]:
    """Mock: every request maps to a single demo user."""
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "display_name": "Demo User",
        "name": "Demo User",
        "role": "operator",
    }
