"""Schemas for admin (cross-tenant)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import field_serializer

from gecko_vpp.schemas.common import GeckoModel, dec_to_str


class TenantPortfolioRow(GeckoModel):
    tenant_id: UUID
    code: str
    display_name: str
    segment: str
    asset_count: int
    capacity_mw: Decimal
    revenue_30d_uah: Decimal

    @field_serializer("capacity_mw", "revenue_30d_uah", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class AdminPortfolioOut(GeckoModel):
    tenants: list[TenantPortfolioRow]
    total_capacity_mw: Decimal
    total_revenue_30d_uah: Decimal

    @field_serializer("total_capacity_mw", "total_revenue_30d_uah",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class AdminOperationsRow(GeckoModel):
    tenant_id: UUID
    code: str
    setpoints_24h: int
    telemetry_rows_24h: int
    avg_availability_pct: Decimal

    @field_serializer("avg_availability_pct", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class AdminOperationsOut(GeckoModel):
    rows: list[AdminOperationsRow]


class AdminAnalyticsRow(GeckoModel):
    tenant_id: UUID
    code: str
    co2_avoided_tn_30d: Decimal
    grn_earned_uah_30d: Decimal
    opportunity_score_avg: Decimal

    @field_serializer("co2_avoided_tn_30d", "grn_earned_uah_30d",
                       "opportunity_score_avg", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class AdminAnalyticsOut(GeckoModel):
    rows: list[AdminAnalyticsRow]
