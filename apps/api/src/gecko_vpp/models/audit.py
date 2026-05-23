"""ORM models for the `audit` schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


class AuditEvent(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_audit_events_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_audit_events_type_occurred", "event_type", "occurred_at"),
        {"schema": "audit"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.users.id")
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    ref_table: Mapped[str | None] = mapped_column(Text)
    ref_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
