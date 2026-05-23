"""ORM models for the `market` schema."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gecko_vpp.models.base import Base


# NOTE on interval_start expressions: see migration 004 docstring for why
# we use make_interval() instead of the architect's `||' hour'::INTERVAL`
# form (Postgres rejects the latter as non-immutable for GENERATED columns).
_GEN_HOUR = "(date + make_interval(hours => hour - 1))"
_GEN_DELIVERY_HOUR = "(delivery_date + make_interval(hours => delivery_hour - 1))"
_GEN_DELIVERY_HOUR_BIDS = "(delivery_date + make_interval(hours => hour - 1))"


class RdnPrice(Base):
    __tablename__ = "rdn_prices"
    __table_args__ = (
        CheckConstraint("hour BETWEEN 1 AND 24", name="rdn_prices_hour_range"),
        UniqueConstraint(
            "tenant_id", "bidding_zone_eic", "date", "hour",
            name="uq_rdn_prices_tenant_id_bzn_date_hour",
        ),
        Index("ix_rdn_prices_tenant_id_date", "tenant_id", "date"),
        Index("ix_rdn_prices_interval_start", "interval_start"),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    bidding_zone_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_HOUR, persisted=True),
        nullable=True,
    )
    price_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    volume_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    is_capped: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    cap_uah_mwh: Mapped[Decimal | None] = mapped_column()
    daily_index_base: Mapped[Decimal | None] = mapped_column()
    daily_index_peak: Mapped[Decimal | None] = mapped_column()
    daily_index_offpeak: Mapped[Decimal | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )


class VdrTrade(Base):
    __tablename__ = "vdr_trades"
    __table_args__ = (
        CheckConstraint(
            "delivery_hour BETWEEN 1 AND 24", name="vdr_trades_hour_range"
        ),
        CheckConstraint("side IN ('BUY','SELL')", name="vdr_trades_side_check"),
        UniqueConstraint(
            "tenant_id", "trade_id", name="uq_vdr_trades_tenant_id_trade_id"
        ),
        Index(
            "ix_vdr_trades_tenant_id_delivery_date_delivery_hour",
            "tenant_id", "delivery_date", "delivery_hour",
        ),
        Index(
            "ix_vdr_trades_resource_eic_interval_start",
            "resource_eic", "interval_start",
        ),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    trade_id: Mapped[str] = mapped_column(Text, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_DELIVERY_HOUR, persisted=True),
        nullable=True,
    )
    volume_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    price_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty_code: Mapped[str] = mapped_column(Text, nullable=False)
    resource_eic: Mapped[str | None] = mapped_column(CHAR(16))
    bidding_zone_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )


class BrSettlement(Base):
    __tablename__ = "br_settlements"
    __table_args__ = (
        CheckConstraint("hour BETWEEN 1 AND 24", name="br_settlements_hour_range"),
        CheckConstraint(
            "system_direction IN ('SHORT','LONG','BALANCED')",
            name="br_settlements_direction_check",
        ),
        UniqueConstraint(
            "tenant_id", "date", "hour",
            name="uq_br_settlements_tenant_id_date_hour",
        ),
        Index("ix_br_settlements_tenant_id_date", "tenant_id", "date"),
        Index("ix_br_settlements_interval_start", "interval_start"),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_HOUR, persisted=True),
        nullable=True,
    )
    price_short_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    price_long_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    system_direction: Mapped[str] = mapped_column(Text, nullable=False)
    our_imbalance_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    settlement_uah: Mapped[Decimal] = mapped_column(nullable=False)
    bidding_zone_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )


class DdContract(Base):
    __tablename__ = "dd_contracts"
    __table_args__ = (
        CheckConstraint(
            "profile_type IN ('BASE','PEAK','OFFPEAK','INDIVIDUAL')",
            name="dd_contracts_profile_check",
        ),
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','CLOSED')",
            name="dd_contracts_status_check",
        ),
        UniqueConstraint(
            "tenant_id", "contract_no",
            name="uq_dd_contracts_tenant_id_contract_no",
        ),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    contract_no: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty_name: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty_edrpou: Mapped[str | None] = mapped_column(CHAR(8))
    profile_type: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_uah_mwh: Mapped[Decimal | None] = mapped_column()
    price_formula: Mapped[str | None] = mapped_column(Text)
    total_volume_mwh: Mapped[Decimal | None] = mapped_column()
    bidding_zone_eic: Mapped[str] = mapped_column(
        CHAR(16), nullable=False, server_default=text("'10Y1001C--00003F'")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'ACTIVE'")
    )


class DdContractHourlyVolume(Base):
    __tablename__ = "dd_contract_hourly_volume"
    __table_args__ = (
        CheckConstraint(
            "hour BETWEEN 1 AND 24",
            name="dd_contract_hourly_volume_hour_range",
        ),
        Index(
            "ix_dd_contract_hourly_volume_tenant_id_date",
            "tenant_id", "date",
        ),
        {"schema": "market"},
    )

    contract_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("market.dd_contracts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    hour: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_HOUR, persisted=True),
        nullable=True,
    )
    volume_mwh: Mapped[Decimal] = mapped_column(nullable=False)


class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        CheckConstraint(
            "market IN ('RDN','VDR','BR','DD')", name="bids_market_check"
        ),
        CheckConstraint("hour BETWEEN 1 AND 24", name="bids_hour_range"),
        CheckConstraint("side IN ('BUY','SELL')", name="bids_side_check"),
        CheckConstraint(
            "bid_type IN ('SIMPLE','BLOCK','STEP','LIMIT','IOC','FOK')",
            name="bids_type_check",
        ),
        CheckConstraint(
            "state IN ('ACTIVE','ACCEPTED','PARTIAL','REJECTED','CANCELLED')",
            name="bids_state_check",
        ),
        UniqueConstraint(
            "tenant_id", "bid_id",
            name="uq_bids_tenant_id_bid_id",
        ),
        Index(
            "ix_bids_tenant_id_market_delivery_date_hour",
            "tenant_id", "market", "delivery_date", "hour",
        ),
        Index(
            "ix_bids_resource_eic_interval_start",
            "resource_eic", "interval_start",
        ),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    bid_id: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_DELIVERY_HOUR_BIDS, persisted=True),
        nullable=True,
    )
    side: Mapped[str] = mapped_column(Text, nullable=False)
    bid_type: Mapped[str] = mapped_column(Text, nullable=False)
    block_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    volume_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    price_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    technology_type: Mapped[str | None] = mapped_column(CHAR(3))
    participant_eic: Mapped[str] = mapped_column(CHAR(16), nullable=False)
    resource_eic: Mapped[str | None] = mapped_column(CHAR(16))
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'ACTIVE'")
    )
    accepted_volume_mwh: Mapped[Decimal | None] = mapped_column()
    clearing_price: Mapped[Decimal | None] = mapped_column()
    settlement_amount: Mapped[Decimal | None] = mapped_column()


class AncillaryOffer(Base):
    __tablename__ = "ancillary_offers"
    __table_args__ = (
        CheckConstraint("hour BETWEEN 1 AND 24", name="ancillary_offers_hour_range"),
        CheckConstraint(
            "service IN ('FCR','aFRR_up','aFRR_down','mFRR_up','mFRR_down','RR')",
            name="ancillary_offers_service_check",
        ),
        UniqueConstraint(
            "tenant_id", "asset_id", "date", "hour", "service",
            name="uq_ancillary_offers_tenant_asset_date_hour_svc",
        ),
        {"schema": "market"},
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
    interval_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        Computed(_GEN_HOUR, persisted=True),
        nullable=True,
    )
    service: Mapped[str] = mapped_column(Text, nullable=False)
    offered_capacity_mw: Mapped[Decimal] = mapped_column(nullable=False)
    cleared_capacity_mw: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0")
    )
    capacity_price_eur_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    revenue_capacity_uah: Mapped[Decimal] = mapped_column(
        nullable=False, server_default=text("0")
    )


class AncillaryActivation(Base):
    __tablename__ = "ancillary_activations"
    __table_args__ = (
        CheckConstraint(
            "service IN ('FCR','aFRR_up','aFRR_down','mFRR_up','mFRR_down','RR')",
            name="ancillary_activations_service_check",
        ),
        Index(
            "ix_ancillary_activations_tenant_asset_started",
            "tenant_id", "asset_id", "started_at",
        ),
        {"schema": "market"},
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
    service: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    avg_power_mw: Mapped[Decimal] = mapped_column(nullable=False)
    energy_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    energy_price_uah_mwh: Mapped[Decimal] = mapped_column(nullable=False)
    revenue_energy_uah: Mapped[Decimal] = mapped_column(nullable=False)
