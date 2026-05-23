"""Schemas for dispatch: setpoints, telemetry, instructions."""

from __future__ import annotations

import datetime as _dt
Date = _dt.date  # alias to avoid name collision with field named `date`

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import field_serializer

from gecko_vpp.schemas.common import GeckoModel, dec_to_str, to_kyiv_iso, to_date_iso


class SetpointOut(GeckoModel):
    id: int
    asset_id: UUID
    issued_at: datetime
    effective_from: datetime
    effective_to: datetime
    target_power_mw: Decimal
    target_soc_pct: Decimal | None = None
    reason: str
    issued_by: str
    state: str

    @field_serializer("target_power_mw", "target_soc_pct", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("issued_at", "effective_from", "effective_to",
                       when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class SetpointIssueIn(GeckoModel):
    asset_id: UUID
    effective_from: datetime
    effective_to: datetime
    target_power_mw: Decimal
    target_soc_pct: Decimal | None = None
    reason: str = "manual"
    issued_by: str = "demo_operator"


class TelemetryOut(GeckoModel):
    asset_id: UUID
    date: Date
    hour: int
    interval_start: datetime
    active_power_mw: Decimal
    reactive_power_mvar: Decimal | None = None
    soc_pct: Decimal | None = None
    availability_pct: Decimal
    status: str
    data_quality: str
    source: str

    @field_serializer("active_power_mw", "reactive_power_mvar", "soc_pct",
                       "availability_pct", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("date", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)

    @field_serializer("interval_start", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class InstructionOut(GeckoModel):
    id: int
    setpoint_id: int | None = None
    asset_id: UUID
    instruction_kind: str
    payload: dict[str, Any]
    queued_at: datetime
    dispatched_at: datetime | None = None
    priority: int

    @field_serializer("queued_at", "dispatched_at", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class InstructionAckOut(GeckoModel):
    instruction_id: int
    acknowledged_at: datetime
    ack_status: str
    ack_payload: dict[str, Any] = {}
    notes: str | None = None

    @field_serializer("acknowledged_at", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class InstructionAckIn(GeckoModel):
    ack_status: str = "ack"
    ack_payload: dict[str, Any] = {}
    notes: str | None = None
