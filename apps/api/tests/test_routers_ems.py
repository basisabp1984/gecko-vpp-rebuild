"""Tests for POST /api/v1/ems/optimise — the deterministic optimiser.

Coverage:
  * Happy path: scenario=day_ahead, date=2026-05-12 → 200 with the
    OptimiseOut envelope (run_id, scenario, recommendations,
    expected_uplift_uah, confidence, risk_flags, duration_ms,
    inputs_hash).
  * Invalid body — missing required fields → 422.
  * Empty body → 422.
  * Wrong field types → 422.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from gecko_vpp.config import get_settings
from gecko_vpp.main import app

pytestmark = pytest.mark.asyncio


settings = get_settings()
TENANT_PRODUCER = settings.tenant_producer_uuid


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_optimise_day_ahead_happy_path() -> None:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/ems/optimise",
            json={"scenario": "day_ahead", "date": "2026-05-12"},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["tenant_id"] == TENANT_PRODUCER

    data = body["data"]
    for k in (
        "run_id",
        "scenario",
        "recommendations",
        "expected_uplift_uah",
        "confidence",
        "risk_flags",
        "duration_ms",
        "inputs_hash",
    ):
        assert k in data, f"missing key {k} in optimise response {data}"
    assert data["scenario"] == "day_ahead"
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["risk_flags"], list)
    assert isinstance(data["inputs_hash"], str) and len(data["inputs_hash"]) == 64


async def test_optimise_empty_body_rejected() -> None:
    """No body at all → FastAPI returns 422 for missing required JSON."""
    async with _client() as client:
        resp = await client.post(
            "/api/v1/ems/optimise",
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 422, resp.text


async def test_optimise_invalid_field_types_rejected() -> None:
    """horizon_hours must be an int — string is rejected."""
    async with _client() as client:
        resp = await client.post(
            "/api/v1/ems/optimise",
            json={
                "scenario": "day_ahead",
                "horizon_hours": "not-an-int",
            },
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 422, resp.text


async def test_optimise_missing_tenant_header() -> None:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/ems/optimise",
            json={"scenario": "day_ahead", "date": "2026-05-12"},
        )
    assert resp.status_code in (400, 422), resp.text
