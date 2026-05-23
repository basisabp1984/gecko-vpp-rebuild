"""ORM models for the `agents` schema."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


class QueryLog(Base):
    __tablename__ = "query_log"
    __table_args__ = (
        CheckConstraint(
            "persona IN ('dispatcher_analyst','market_analyst',"
            "'energy_advisor','battery_coach')",
            name="query_log_persona_check",
        ),
        Index("ix_query_log_tenant_created", "tenant_id", "created_at"),
        {"schema": "agents"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona: Mapped[str] = mapped_column(Text, nullable=False)
    user_text: Mapped[str] = mapped_column(Text, nullable=False)
    classified_intent: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class ResponseCache(Base):
    __tablename__ = "response_cache"
    __table_args__ = ({"schema": "agents"},)

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    persona: Mapped[str] = mapped_column(Text, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    ttl_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("300")
    )
