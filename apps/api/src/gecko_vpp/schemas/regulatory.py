"""Schemas for regulatory: settlements, signed_documents, regulator_events."""

from __future__ import annotations

import datetime as _dt
Date = _dt.date  # alias to avoid name collision with field named `date`

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import field_serializer

from gecko_vpp.schemas.common import GeckoModel, dec_to_str, to_kyiv_iso, to_date_iso


class SettlementLineOut(GeckoModel):
    id: int
    line_no: int
    asset_eic: str
    asset_name: str
    technology_type: str | None = None
    volume_mwh: Decimal
    tariff_uah_mwh: Decimal
    amount_uah: Decimal

    @field_serializer("volume_mwh", "tariff_uah_mwh", "amount_uah",
                       when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)


class SettlementOut(GeckoModel):
    id: int
    statement_no: str
    counterparty: str
    counterparty_edrpou: str | None = None
    contract_no: str | None = None
    period_year: int
    period_month: int
    period_start: Date
    period_end: Date
    volume_total_mwh: Decimal
    amount_net_uah: Decimal
    vat_rate: Decimal
    amount_vat_uah: Decimal
    amount_gross_uah: Decimal
    payment_due_date: Date
    status: str
    signed_doc_id: int | None = None
    lines: list[SettlementLineOut] = []

    @field_serializer("volume_total_mwh", "amount_net_uah", "vat_rate",
                       "amount_vat_uah", "amount_gross_uah", when_used="json")
    def _ser_dec(self, v: Decimal | None) -> str | None:
        return dec_to_str(v)

    @field_serializer("period_start", "period_end", "payment_due_date",
                       when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)


class SignBadgeFields(GeckoModel):
    signer_name: str
    signer_edrpou: str
    acsk_name: str
    signed_at: str
    hash_short: str


class SignedDocumentBadgeOut(GeckoModel):
    signed_doc_id: int
    badge_text: str
    badge_fields: SignBadgeFields
    is_demo_stub: bool


class SignedDocumentOut(GeckoModel):
    id: int
    document_type: str
    document_ref_table: str
    document_ref_id: int
    signer_name: str
    signer_position: str | None = None
    signer_edrpou: str | None = None
    acsk_name: str
    signature_format: str
    document_hash_sha256: str
    signed_at: datetime
    is_demo_stub: bool
    kep_badge_short: str | None = None

    @field_serializer("signed_at", when_used="json")
    def _ser_dt(self, v: datetime | None) -> str | None:
        return to_kyiv_iso(v)


class RegulatorEventOut(GeckoModel):
    id: int
    issuer: str
    act_type: str
    act_number: str | None = None
    issued_at: Date
    effective_at: Date | None = None
    title: str
    category: str | None = None
    severity: str
    summary: str
    affected_entities: list[Any] = []
    source_url: str | None = None

    @field_serializer("issued_at", "effective_at", when_used="json")
    def _ser_date(self, v: Date | None) -> str | None:
        return to_date_iso(v)
