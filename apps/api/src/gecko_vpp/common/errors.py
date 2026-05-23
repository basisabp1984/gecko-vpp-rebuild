"""Canonical GeckoError hierarchy + FastAPI handler.

Error codes per ARCHITECTURE.md §4.1 — the canonical 7.
"""

from __future__ import annotations

from typing import Any


class GeckoError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "Internal error"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}


class InvalidTenant(GeckoError):
    code = "INVALID_TENANT"
    http_status = 400
    message = "Invalid X-Tenant-Id header"


class MissingTenantHeader(GeckoError):
    code = "MISSING_TENANT_HEADER"
    http_status = 400
    message = "X-Tenant-Id header is required"


class NotFound(GeckoError):
    code = "NOT_FOUND"
    http_status = 404
    message = "Resource not found"


class ValidationFailed(GeckoError):
    code = "VALIDATION_FAILED"
    http_status = 422
    message = "Validation failed"


class RateLimited(GeckoError):
    code = "RATE_LIMITED"
    http_status = 429
    message = "Rate limit exceeded"


class InternalError(GeckoError):
    code = "INTERNAL_ERROR"
    http_status = 500
    message = "Internal error"


class StubNotImplemented(GeckoError):
    code = "STUB_NOT_IMPLEMENTED"
    http_status = 501
    message = "Stub not implemented"
