"""Schemas for EMS: forecasts, optimisation, KPI."""

from __future__ import annotations

import datetime as _dt
from datetime import datetime
Date = _dt.date  # alias to avoid name collision with field named `date`
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import field_serializer

from gecko_vpp.schemas.common import GeckoModel, dec_to_str, to_kyiv_iso, to_date_iso


class ForecastOut(GeckoModel):
    id: int
    asset_id: UUID | None = None
    forecast_kind: str
    forecast_type: str
    issued_at: datetime
    date: Date
    hour: int
    interval_start: datetime | None = None
    value_mwh: Decimal
    model_id: str
    confidence_lo: Decimal | None = None
    confidence_hi: Decimal | None = None

    @field_serializer("value_mwh", "confidence_lo", "confidence_hi",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("issued_at", "interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class ForecastActualOut(GeckoModel):
    asset_id: UUID
    forecast_kind: str
    date: Date
    hour: int
    interval_start: datetime | None = None
    actual_mwh: Decimal

    @field_serializer("actual_mwh", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class ForecastSubmitIn(GeckoModel):
    delivery_date: Date
    resource_eic: str
    submitter_eic: str | None = None
    business_type: str = "A01"
    document_type: str = "A14"
    process_type: str = "A01"
    resolution_minutes: int = 60
    hourly_volumes_mwh: list[Decimal]


class ForecastSubmissionOut(GeckoModel):
    id: int
    submission_id: str
    submitted_at: datetime
    submitter_eic: str
    resource_eic: str | None = None
    bzn_eic: str
    business_type: str
    document_type: str
    process_type: str
    delivery_date: Date
    resolution_minutes: int
    hourly_volumes_mwh: list[Decimal]
    status: str
    status_changed_at: datetime

    @field_serializer("delivery_date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("submitted_at", "status_changed_at", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)

    @field_serializer("hourly_volumes_mwh", when_used="json")
    def _ser_vols(self, v: list[Decimal]) -> list[str]:
        return [str(x) for x in v]


class OptimiseIn(GeckoModel):
    scenario: str = "arbitrage"  # arbitrage|capacity|day_ahead
    horizon_hours: int = 24
    asset_ids: list[UUID] = []
    date: Date | None = None


class RecommendationOut(GeckoModel):
    asset_id: UUID
    hour: int
    action: str
    mw: Decimal

    @field_serializer("mw", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class OptimiseOut(GeckoModel):
    run_id: int
    scenario: str
    recommendations: list[RecommendationOut]
    expected_uplift_uah: Decimal
    uplift_uah: Decimal
    confidence_pct: Decimal
    confidence: float
    risk_flags: list[str]
    duration_ms: int
    inputs_hash: str

    @field_serializer("expected_uplift_uah", "uplift_uah", "confidence_pct",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class KpiDailyOut(GeckoModel):
    asset_id: UUID
    date: Date
    grn_saved_uah: Decimal
    grn_earned_uah: Decimal
    imbalance_mwh: Decimal
    co2_avoided_tn: Decimal
    availability_pct: Decimal
    opportunity_score: int
    notes: str | None = None

    @field_serializer("grn_saved_uah", "grn_earned_uah", "imbalance_mwh",
                       "co2_avoided_tn", "availability_pct", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)


class KpiPortfolioOut(GeckoModel):
    range: str
    grn_saved_uah: Decimal
    grn_earned_uah: Decimal
    revenue_uah: Decimal
    imbalance_mwh: Decimal
    co2_avoided_tn: Decimal
    availability_pct: Decimal
    asset_count: int

    @field_serializer("grn_saved_uah", "grn_earned_uah", "revenue_uah",
                       "imbalance_mwh", "co2_avoided_tn", "availability_pct",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)
