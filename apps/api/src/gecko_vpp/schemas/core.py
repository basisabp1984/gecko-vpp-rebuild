"""Schemas for core: tenants, auth, assets."""

from __future__ import annotations

import datetime as _dt
Date = _dt.date  # alias to avoid name collision with field named `date`

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import field_serializer

from gecko_vpp.schemas.common import GeckoModel, dec_to_str, to_kyiv_iso, to_date_iso


class TenantOut(GeckoModel):
    id: UUID
    code: str
    display_name: str
    segment: str
    edrpou: str
    participant_eic: str
    bzn_eic: str
    region: str | None = None


class CurrentUserOut(GeckoModel):
    id: str
    display_name: str
    name: str
    role: str


class AuthMeOut(GeckoModel):
    tenant_id: UUID
    tenant: TenantOut
    current_user: CurrentUserOut


class SwitchTenantIn(GeckoModel):
    tenant_id: UUID | None = None
    tenant_code: str | None = None


class AssetOut(GeckoModel):
    id: UUID
    tenant_id: UUID
    code: str
    display_name: str
    asset_class: str
    technology_type: str
    resource_eic: str
    metering_eic: str | None = None
    capacity_mw: Decimal
    storage_capacity_mwh: Decimal | None = None
    region: str
    commissioned_on: Date
    status: str
    bzn_eic: str

    @field_serializer("capacity_mw", "storage_capacity_mwh", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("commissioned_on", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)
