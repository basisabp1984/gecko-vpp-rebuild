"""ORM models for the `regulatory` schema."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    CHAR,
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


class ForecastSubmission(Base):
    __tablename__ = "forecast_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','ACK','REJECTED')",
            name="forecast_submissions_status_check",
        ),
        UniqueConstraint(
            "tenant_id", "submission_id",
            name="uq_forecast_submissions_tenant_submission_id",
        ),
        Index(
            "ix_forecast_submissions_tenant_delivery",
            "tenant_id", "delivery_date",
        ),
        {"schema": "regulatory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    submission_id: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    submitter_eic: Mapped[str] = mapped_column(CHAR(16), nullable=False)
    resource_eic: Mapped[str | None] = mapped_column(CHAR(16))
    bzn_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )
    business_type: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    document_type: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    process_type: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("60")
    )
    hourly_volumes_mwh: Mapped[list[Decimal]] = mapped_column(
        ARRAY(Numeric(10, 4)), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'DRAFT'")
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    raw_xml: Mapped[str | None] = mapped_column(Text)


class SettlementStatement(Base):
    __tablename__ = "settlement_statements"
    __table_args__ = (
        CheckConstraint(
            "period_month BETWEEN 1 AND 12",
            name="settlement_statements_month_range",
        ),
        CheckConstraint(
            "status IN ('DRAFT','ISSUED','SIGNED','PAID','DISPUTED')",
            name="settlement_statements_status_check",
        ),
        UniqueConstraint(
            "tenant_id", "statement_no",
            name="uq_settlement_statements_tenant_statement_no",
        ),
        Index(
            "ix_settlement_statements_tenant_year_month",
            "tenant_id", "period_year", "period_month",
        ),
        {"schema": "regulatory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    statement_no: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty_edrpou: Mapped[str | None] = mapped_column(CHAR(8))
    contract_no: Mapped[str | None] = mapped_column(Text)
    period_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    period_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    volume_total_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    amount_net_uah: Mapped[Decimal] = mapped_column(nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0.20")
    )
    amount_vat_uah: Mapped[Decimal] = mapped_column(nullable=False)
    amount_gross_uah: Mapped[Decimal] = mapped_column(nullable=False)
    payment_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_received_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'DRAFT'")
    )
    # FK to signed_documents.id is added by migration 007 (chicken-and-egg).
    signed_doc_id: Mapped[int | None] = mapped_column(BigInteger)


class SettlementStatementLine(Base):
    __tablename__ = "settlement_statement_lines"
    __table_args__ = ({"schema": "regulatory"},)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    statement_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("regulatory.settlement_statements.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    line_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    asset_eic: Mapped[str] = mapped_column(CHAR(16), nullable=False)
    asset_name: Mapped[str] = mapped_column(Text, nullable=False)
    technology_type: Mapped[str | None] = mapped_column(CHAR(3))
    volume_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    tariff_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    amount_uah: Mapped[Decimal] = mapped_column(nullable=False)


class SignedDocument(Base):
    __tablename__ = "signed_documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('SETTLEMENT_ACT','BID_PACKAGE','FORECAST_PACKAGE',"
            "'REPORT','CONTRACT')",
            name="signed_documents_type_check",
        ),
        Index(
            "ix_signed_documents_ref",
            "document_ref_table", "document_ref_id",
        ),
        {"schema": "regulatory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_ref_table: Mapped[str] = mapped_column(Text, nullable=False)
    document_ref_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    signer_name: Mapped[str] = mapped_column(Text, nullable=False)
    signer_position: Mapped[str | None] = mapped_column(Text)
    signer_edrpou: Mapped[str | None] = mapped_column(CHAR(8))
    signer_ipn: Mapped[str | None] = mapped_column(CHAR(10))
    acsk_name: Mapped[str] = mapped_column(Text, nullable=False)
    signature_format: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'CAdES-X-Long'")
    )
    document_hash_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    tsa_provider: Mapped[str | None] = mapped_column(
        Text, server_default=text("'czo.gov.ua'")
    )
    cert_serial: Mapped[str | None] = mapped_column(Text)
    cert_valid_until: Mapped[date | None] = mapped_column(Date)
    p7s_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_demo_stub: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("TRUE")
    )
    # Populated by a BEFORE INSERT/UPDATE trigger (see migration 007) — the
    # architect spec'd this GENERATED but Postgres rejects TO_CHAR over
    # TIMESTAMPTZ as non-immutable. Trigger preserves the badge contract.
    kep_badge_short: Mapped[str | None] = mapped_column(Text)


class RegulatorEvent(Base):
    __tablename__ = "regulator_events"
    __table_args__ = (
        CheckConstraint(
            "issuer IN ('НКРЕКП','Укренерго','Кабмін','ОРЕЕ','ГП')",
            name="regulator_events_issuer_check",
        ),
        CheckConstraint(
            "category IS NULL OR category IN "
            "('TARIFF','CODE_AMENDMENT','SANCTION','EMERGENCY',"
            "'MARKET_FREEZE','INFO')",
            name="regulator_events_category_check",
        ),
        CheckConstraint(
            "severity IN ('INFO','NOTICE','WARN','CRITICAL')",
            name="regulator_events_severity_check",
        ),
        Index("ix_regulator_events_issued_at", "issued_at"),
        Index(
            "ix_regulator_events_affected_entities",
            "affected_entities",
            postgresql_using="gin",
        ),
        {"schema": "regulatory"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    act_type: Mapped[str] = mapped_column(Text, nullable=False)
    act_number: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    effective_at: Mapped[date | None] = mapped_column(Date)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'INFO'")
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_entities: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    affected_tenants: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
