"""Envelope builders.

ARCHITECTURE.md §4.1:
  Success: {"data": ..., "meta": {"request_id", "tenant_id", "generated_at"}}
  Error:   {"error": {"code": ..., "message": ..., "details": ...}}

Timestamps: ISO 8601 with Europe/Kyiv offset (+03:00 in our post-DST window).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

KYIV_TZ = timezone(timedelta(hours=3))  # post-DST window, fixed at +03:00


def now_kyiv_iso() -> str:
    """Return ISO 8601 timestamp with Europe/Kyiv offset, no microseconds."""
    return datetime.now(tz=KYIV_TZ).replace(microsecond=0).isoformat()


def make_meta(
    tenant_id: str | None = None,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "request_id": request_id or str(uuid4()),
        "tenant_id": tenant_id,
        "generated_at": now_kyiv_iso(),
    }
    if extra:
        meta.update(extra)
    return meta


def build_success(
    data: Any,
    tenant_id: str | None = None,
    request_id: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"data": data, "meta": make_meta(tenant_id, request_id, extra_meta)}


def build_error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }
