"""Demo users — 2 per tenant (operator + manager). Stable UUIDs."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import TENANTS


USER_NS = UUID("a55e7000-0000-0000-0000-000000000001")


def _uid(tenant_uuid: UUID, role: str) -> UUID:
    return uuid5(USER_NS, f"{tenant_uuid}:{role}")


async def generate(conn: AsyncConnection) -> int:
    rows = []
    for tenant in TENANTS:
        for role, display in [
            ("operator", "Оператор зміни"),
            ("manager", "Енергоменеджер"),
        ]:
            rows.append(
                {
                    "id": str(_uid(tenant.uuid, role)),
                    "tenant_id": str(tenant.uuid),
                    "email": f"{role}@{tenant.code}.gecko.local",
                    "display_name": f"{display} ({tenant.code})",
                    "role": role,
                    "invited_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "accepted_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                }
            )
    stmt = text(
        """
        INSERT INTO core.users
            (id, tenant_id, email, display_name, role, invited_at, accepted_at)
        VALUES
            (CAST(:id AS uuid), CAST(:tenant_id AS uuid),
             :email, :display_name, :role, :invited_at, :accepted_at)
        ON CONFLICT (tenant_id, email) DO NOTHING
        """
    )
    result = await conn.execute(stmt, rows)
    return (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
