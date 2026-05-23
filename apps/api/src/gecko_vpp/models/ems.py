"""ORM models for the `ems` schema."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


# See models/market.py note — Postgres GENERATED columns require an
# immutable expression; we use make_interval() instead of '|| INTERVAL'.
_GEN_HOUR = "(date + make_interval(hours => hour - 1))"


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        CheckConstraint("hour BETWEEN 1 AND 24", name="forecasts_hour_range"),
        CheckConstraint(
            "forecast_kind IN ('solar','wind','load','price','consumption')",
            name="forecasts_kind_check",
        ),
        CheckConstraint(
            "forecast_type IN ('primary','refined')",
            name="forecasts_type_check",
        ),
        UniqueConstraint(
            "tenant_id", "asset_id", "forecast_kind", "forecast_type",
            "date", "hour",
            name="uq_forecasts_full",
        ),
        Index(
            "ix_forecasts_tenant_kind_date",
            "tenant_id", "forecast_kind", "date",
        ),
        {"schema": "ems"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.assets.id", ondelete="CASCADE"),
    )
    forecast_kind: Mapped[str] = mapped_column(Text, nullable=False)
    forecast_type: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_HOUR, persisted=True),
        nullable=True,
    )
    value_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    model_id: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'synth-v1'")
    )
    confidence_lo: Mapped[Decimal | None] = mapped_column()
    confidence_hi: Mapped[Decimal | None] = mapped_column()


class ForecastActual(Base):
    __tablename__ = "forecast_actuals"
    __table_args__ = (
        CheckConstraint(
            "hour BETWEEN 1 AND 24", name="forecast_actuals_hour_range"
        ),
        {"schema": "ems"},
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    forecast_kind: Mapped[str] = mapped_column(Text, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    hour: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_HOUR, persisted=True),
        nullable=True,
    )
    actual_mwh: Mapped[Decimal] = mapped_column(nullable=False)


class KpiDaily(Base):
    __tablename__ = "kpi_daily"
    __table_args__ = (
        CheckConstraint(
            "opportunity_score BETWEEN 0 AND 100",
            name="kpi_daily_opp_score_range",
        ),
        {"schema": "ems"},
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    grn_saved_uah: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0")
    )
    grn_earned_uah: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0")
    )
    imbalance_mwh: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0")
    )
    co2_avoided_tn: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0")
    )
    availability_pct: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("100")
    )
    opportunity_score: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class OptimisationRun(Base):
    __tablename__ = "optimisation_runs"
    __table_args__ = (
        Index(
            "ix_optimisation_runs_tenant_requested",
            "tenant_id", "requested_at",
        ),
        {"schema": "ems"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.users.id")
    )
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    inputs_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recommendations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected_uplift_uah: Mapped[Decimal] = mapped_column(nullable=False)
    risk_flags: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    confidence_pct: Mapped[Decimal] = mapped_column(nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
