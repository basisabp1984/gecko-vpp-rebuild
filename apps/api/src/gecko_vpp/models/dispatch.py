"""ORM models for the `dispatch` schema.

NOTE: `dispatch.telemetry.interval_start` is a plain TIMESTAMPTZ — NOT a
GENERATED column, because Postgres forbids GENERATED columns as partition
keys. Synth must compute interval_start explicitly in Python.
See difficulties_log.md entry for full reasoning.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


class Setpoint(Base):
    __tablename__ = "setpoints"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending','acknowledged','executing','done','cancelled','failed')",
            name="setpoints_state_check",
        ),
        Index(
            "ix_setpoints_tenant_asset_eff",
            "tenant_id", "asset_id", "effective_from",
        ),
        {"schema": "dispatch"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    effective_from: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    target_power_mw: Mapped[Decimal] = mapped_column(nullable=False)
    target_soc_pct: Mapped[Decimal | None] = mapped_column()
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    issued_by: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pending'")
    )


class Telemetry(Base):
    """Partitioned by RANGE (interval_start). Partitions live in migration 005."""

    __tablename__ = "telemetry"
    __table_args__ = (
        CheckConstraint("hour BETWEEN 1 AND 24", name="telemetry_hour_range"),
        CheckConstraint(
            "status IN ('online','idle','maintenance','starting','stopping',"
            "'tripped','curtailed_by_TSO','unavailable')",
            name="telemetry_status_check",
        ),
        CheckConstraint(
            "data_quality IN ('R','V','E','S')",
            name="telemetry_data_quality_check",
        ),
        Index("ix_telemetry_tenant_date_hour", "tenant_id", "date", "hour"),
        Index("ix_telemetry_asset_interval", "asset_id", "interval_start"),
        {
            "schema": "dispatch",
            "postgresql_partition_by": "RANGE (interval_start)",
        },
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True
    )
    active_power_mw: Mapped[Decimal] = mapped_column(nullable=False)
    reactive_power_mvar: Mapped[Decimal | None] = mapped_column()
    soc_pct: Mapped[Decimal | None] = mapped_column()
    availability_pct: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("100")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'online'")
    )
    data_quality: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, server_default=text("'R'")
    )
    source: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'synthetic'")
    )
    extras: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class Instruction(Base):
    __tablename__ = "instructions"
    __table_args__ = (
        CheckConstraint(
            "instruction_kind IN ('setpoint','curtail','restore','start','stop','test')",
            name="instructions_kind_check",
        ),
        Index("ix_instructions_tenant_queued", "tenant_id", "queued_at"),
        {"schema": "dispatch"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    setpoint_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dispatch.setpoints.id")
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    instruction_kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    queued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    priority: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("5")
    )


class InstructionAck(Base):
    __tablename__ = "instruction_acks"
    __table_args__ = (
        CheckConstraint(
            "ack_status IN ('ack','nack','timeout')",
            name="instruction_acks_status_check",
        ),
        {"schema": "dispatch"},
    )

    instruction_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dispatch.instructions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    ack_status: Mapped[str] = mapped_column(Text, nullable=False)
    ack_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class OperatorAdjustment(Base):
    __tablename__ = "operator_adjustments"
    __table_args__ = (
        CheckConstraint(
            "hour BETWEEN 1 AND 24",
            name="operator_adjustments_hour_range",
        ),
        UniqueConstraint(
            "tenant_id", "asset_id", "date", "hour",
            name="uq_operator_adjustments_tenant_asset_date_hour",
        ),
        {"schema": "dispatch"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    operator_mw: Mapped[Decimal] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    operator_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
