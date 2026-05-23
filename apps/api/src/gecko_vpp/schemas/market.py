"""Schemas for market: rdn, vdr, br, dd, bids, ancillary, revenue."""

from __future__ import annotations

import datetime as _dt
Date = _dt.date  # alias to avoid name collision with field named `date`

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_serializer

from gecko_vpp.schemas.common import GeckoModel, dec_to_str, to_kyiv_iso, to_date_iso


class RdnPriceOut(GeckoModel):
    date: Date
    hour: int
    interval_start: datetime | None = None
    price_uah_mwh: Decimal
    volume_mwh: Decimal
    is_capped: bool
    cap_uah_mwh: Decimal | None = None
    daily_index_base: Decimal | None = None
    daily_index_peak: Decimal | None = None
    daily_index_offpeak: Decimal | None = None
    bidding_zone_eic: str

    @field_serializer("price_uah_mwh", "volume_mwh", "cap_uah_mwh",
                       "daily_index_base", "daily_index_peak", "daily_index_offpeak",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class VdrTradeOut(GeckoModel):
    trade_id: str
    executed_at: datetime
    delivery_date: Date
    delivery_hour: int
    interval_start: datetime | None = None
    volume_mwh: Decimal
    price_uah_mwh: Decimal
    side: str
    counterparty_code: str
    resource_eic: str | None = None
    bidding_zone_eic: str

    @field_serializer("volume_mwh", "price_uah_mwh", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("delivery_date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("executed_at", "interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class BrSettlementOut(GeckoModel):
    date: Date
    hour: int
    interval_start: datetime | None = None
    price_short_uah_mwh: Decimal
    price_long_uah_mwh: Decimal
    system_direction: str
    our_imbalance_mwh: Decimal
    settlement_uah: Decimal
    bidding_zone_eic: str

    @field_serializer("price_short_uah_mwh", "price_long_uah_mwh",
                       "our_imbalance_mwh", "settlement_uah", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class DdContractOut(GeckoModel):
    id: int
    contract_no: str
    counterparty_name: str
    counterparty_edrpou: str | None = None
    profile_type: str
    start_date: Date
    end_date: Date
    price_uah_mwh: Decimal | None = None
    price_formula: str | None = None
    total_volume_mwh: Decimal | None = None
    status: str

    @field_serializer("price_uah_mwh", "total_volume_mwh", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("start_date", "end_date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)


class BidOut(GeckoModel):
    id: int
    bid_id: str
    market: str
    delivery_date: Date
    hour: int
    interval_start: datetime | None = None
    side: str
    bid_type: str
    volume_mwh: Decimal
    price_uah_mwh: Decimal
    resource_eic: str | None = None
    participant_eic: str
    submitted_at: datetime
    state: str
    accepted_volume_mwh: Decimal | None = None
    clearing_price: Decimal | None = None
    settlement_amount: Decimal | None = None

    @field_serializer("volume_mwh", "price_uah_mwh", "accepted_volume_mwh",
                       "clearing_price", "settlement_amount", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("delivery_date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("submitted_at", "interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class BidSubmitIn(GeckoModel):
    market: str  # RDN|VDR|BR|DD
    delivery_date: Date
    hour: int
    side: str  # BUY|SELL
    bid_type: str = "SIMPLE"
    volume_mwh: Decimal
    price_uah_mwh: Decimal
    resource_eic: str | None = None
    participant_eic: str | None = None


class RevenueChannelOut(GeckoModel):
    channel: str
    revenue_uah: Decimal
    share_pct: float

    @field_serializer("revenue_uah", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class RevenueSummaryOut(GeckoModel):
    rdn_uah: Decimal
    vdr_uah: Decimal
    br_uah: Decimal
    dd_uah: Decimal
    ancillary_uah: Decimal
    green_tariff_uah: Decimal
    total_uah: Decimal
    by_channel: list[RevenueChannelOut] = []

    @field_serializer("rdn_uah", "vdr_uah", "br_uah", "dd_uah",
                       "ancillary_uah", "green_tariff_uah", "total_uah",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class AncillaryActivationOut(GeckoModel):
    id: int
    asset_id: UUID
    service: str
    started_at: datetime
    ended_at: datetime
    avg_power_mw: Decimal
    energy_mwh: Decimal
    energy_price_uah_mwh: Decimal
    revenue_energy_uah: Decimal

    @field_serializer("avg_power_mw", "energy_mwh", "energy_price_uah_mwh",
                       "revenue_energy_uah", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("started_at", "ended_at", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)
