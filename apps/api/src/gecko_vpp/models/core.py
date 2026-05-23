"""ORM models for the `core` schema (tenants, users, eic_codes, assets).

DDL truth lives in `migrations/versions/003_core_tables.py`. These ORM
classes are SQLAlchemy 2.0 typed declarations matching ARCHITECTURE.md §3.2.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "segment IN ('producer','c-i','storage')",
            name="tenants_segment_check",
        ),
        UniqueConstraint("participant_eic", name="uq_tenants_participant_eic"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    segment: Mapped[str] = mapped_column(Text, nullable=False)
    edrpou: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    participant_eic: Mapped[str] = mapped_column(CHAR(16), nullable=False)
    bzn_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )
    region: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(server_default=text("TRUE"), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('operator','manager','admin','viewer')",
            name="users_role_check",
        ),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    invited_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column()


class EicCode(Base):
    __tablename__ = "eic_codes"
    __table_args__ = (
        CheckConstraint(
            "code_type IN ('Y','X','W','V','T','Z')",
            name="eic_codes_code_type_check",
        ),
        {"schema": "core"},
    )

    eic: Mapped[str] = mapped_column(CHAR(16), primary_key=True)
    code_type: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    issuer: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "asset_class IN ('СЕС','ВЕС','ГПУ','УЗЕ','АктСпож','Споживач')",
            name="assets_asset_class_check",
        ),
        CheckConstraint("capacity_mw > 0", name="assets_capacity_mw_positive"),
        CheckConstraint(
            "status IN ('active','maintenance','decommissioned')",
            name="assets_status_check",
        ),
        UniqueConstraint("tenant_id", "code", name="uq_assets_tenant_id_code"),
        Index("ix_assets_tenant_id_asset_class", "tenant_id", "asset_class"),
        Index("ix_assets_resource_eic", "resource_eic"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    technology_type: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    resource_eic: Mapped[str] = mapped_column(
        CHAR(16),
        ForeignKey("core.eic_codes.eic"),
        nullable=False,
    )
    metering_eic: Mapped[str | None] = mapped_column(
        CHAR(16), ForeignKey("core.eic_codes.eic")
    )
    capacity_mw: Mapped[Decimal] = mapped_column(nullable=False)
    storage_capacity_mwh: Mapped[Decimal | None] = mapped_column()
    region: Mapped[str] = mapped_column(Text, nullable=False)
    commissioned_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'active'")
    )
    bzn_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
