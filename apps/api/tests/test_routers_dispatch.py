"""Tests for /api/v1/dispatch/setpoints and /api/v1/dispatch/telemetry.

Coverage:
  * GET /dispatch/setpoints — list response with expected schema
    (asset_id, effective_from, target_power_mw, state).
  * GET /dispatch/telemetry — list response with expected schema
    (asset_id, date, hour, active_power_mw, status, source).
  * Multi-tenant isolation — different tenants see distinct rowsets
    (different asset_ids when both non-empty).
  * Missing tenant header rejected.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from gecko_vpp.config import get_settings
from gecko_vpp.main import app

pytestmark = pytest.mark.asyncio


settings = get_settings()
TENANT_PRODUCER = settings.tenant_producer_uuid
TENANT_CI = settings.tenant_ci_uuid

SYNTH_DATE = "2026-05-12"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_setpoints_basic_shape() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/dispatch/setpoints",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["data"], list)
    assert body["meta"]["tenant_id"] == TENANT_PRODUCER
    if body["data"]:
        row = body["data"][0]
        for k in (
            "id",
            "asset_id",
            "effective_from",
            "effective_to",
            "target_power_mw",
            "state",
        ):
            assert k in row, f"missing key {k} in setpoint row {row}"


async def test_telemetry_basic_shape() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/dispatch/telemetry",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["data"], list)
    if body["data"]:
        row = body["data"][0]
        for k in (
            "asset_id",
            "date",
            "hour",
            "active_power_mw",
            "status",
            "source",
        ):
            assert k in row, f"missing key {k} in telemetry row {row}"


async def test_setpoints_missing_tenant_header() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/dispatch/setpoints",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
        )
    assert resp.status_code in (400, 422), resp.text


async def test_dispatch_multi_tenant_isolation() -> None:
    """Setpoints + telemetry must be tenant-scoped.

    Asset ID sets between TENANT_PRODUCER and TENANT_CI should differ
    when both have any data — assets do not span tenants.
    """
    async with _client() as client:
        r_prod = await client.get(
            "/api/v1/dispatch/telemetry",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
        r_ci = await client.get(
            "/api/v1/dispatch/telemetry",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_CI},
        )

    assert r_prod.status_code == 200, r_prod.text
    assert r_ci.status_code == 200, r_ci.text
    aprod = {row["asset_id"] for row in r_prod.json()["data"]}
    aci = {row["asset_id"] for row in r_ci.json()["data"]}

    if aprod and aci:
        assert aprod.isdisjoint(aci), (
            "RLS leak: telemetry asset_ids overlap between TENANT_PRODUCER "
            f"and TENANT_CI: overlap={aprod & aci}"
        )
