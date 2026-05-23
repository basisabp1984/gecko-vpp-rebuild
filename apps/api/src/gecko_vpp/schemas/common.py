"""Shared base model + serializers.

- Decimal → str (avoid JS float loss)
- datetime → ISO 8601 with Europe/Kyiv offset
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_serializer

KYIV_TZ = timezone(timedelta(hours=3))


T = TypeVar("T")


class GeckoModel(BaseModel):
    """Base for all response/request models. Decimal → str on dump."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        ser_json_timedelta="iso8601",
    )


def to_kyiv_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # Assume UTC if naive (Postgres TIMESTAMP without TZ — treat as Kyiv-local)
        value = value.replace(tzinfo=KYIV_TZ)
    return value.astimezone(KYIV_TZ).replace(microsecond=0).isoformat()


def to_date_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def dec_to_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


# ---- envelope shapes (for OpenAPI docs) ----


class Meta(GeckoModel):
    request_id: str
    tenant_id: str | None = None
    generated_at: str
    pagination: dict[str, Any] | None = None


class Success(GeckoModel, Generic[T]):
    data: T
    meta: Meta


class ErrorBody(GeckoModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(GeckoModel):
    error: ErrorBody
