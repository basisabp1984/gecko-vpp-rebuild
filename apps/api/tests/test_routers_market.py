"""Tests for /api/v1/market/* endpoints (RDN, VDR, BR).

Coverage:
  * Happy path schema validation for each of the three market endpoints
    against the seeded synth window (2026-04-23 .. 2026-05-23).
  * Missing X-Tenant-Id header → 400 (MissingTenantHeader → maps to 400).
  * Malformed X-Tenant-Id UUID → 400 (InvalidTenant).
  * Tenant not in demo allowlist → 400.
  * Multi-tenant isolation at HTTP level — different tenant headers must
    yield distinct datasets (different rows, even if same length).

Uses httpx.AsyncClient with ASGITransport — no real network.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import gecko_vpp.db as _db
from gecko_vpp.config import get_settings
from gecko_vpp.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def _reset_engine_between_tests():
    """Dispose and reset the global async engine after each test.

    pytest-asyncio creates a fresh event loop per test (function scope).
    The cached AsyncEngine + connection pool from the previous test are
    bound to the now-closed loop → asyncpg crashes with
    'NoneType has no attribute send'. We dispose & null the singletons
    so the next test gets a fresh engine on its own loop.
    """
    yield
    if _db._engine is not None:
        try:
            await _db._engine.dispose()
        except Exception:
            pass
    _db._engine = None
    _db._session_factory = None


settings = get_settings()
TENANT_PRODUCER = settings.tenant_producer_uuid
TENANT_CI = settings.tenant_ci_uuid
TENANT_STORAGE = settings.tenant_storage_uuid

# A date inside the seeded synth window.
SYNTH_DATE = "2026-05-12"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---- happy-path shape ----


async def test_rdn_basic_shape() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/market/rdn",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body and "meta" in body
    assert isinstance(body["data"], list)
    assert body["meta"].get("tenant_id") == TENANT_PRODUCER
    if body["data"]:
        row = body["data"][0]
        for k in ("date", "hour", "price_uah_mwh", "volume_mwh", "is_capped"):
            assert k in row, f"missing key {k} in {row}"
        assert isinstance(row["is_capped"], bool)
        assert isinstance(row["hour"], int)


async def test_vdr_basic_shape() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/market/vdr",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["data"], list)
    if body["data"]:
        row = body["data"][0]
        for k in (
            "trade_id",
            "executed_at",
            "delivery_date",
            "delivery_hour",
            "volume_mwh",
            "price_uah_mwh",
            "side",
        ):
            assert k in row, f"missing key {k} in vdr row {row}"


async def test_br_basic_shape() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/market/br",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["data"], list)
    if body["data"]:
        row = body["data"][0]
        for k in (
            "date",
            "hour",
            "price_short_uah_mwh",
            "price_long_uah_mwh",
            "system_direction",
            "settlement_uah",
        ):
            assert k in row, f"missing key {k} in br row {row}"


# ---- auth / validation errors ----


async def test_rdn_missing_tenant_header_rejected() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/market/rdn",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
        )
    # MissingTenantHeader (400) or framework validation (422) are acceptable.
    assert resp.status_code in (400, 422), resp.text
    body = resp.json()
    assert "error" in body or "detail" in body


async def test_rdn_invalid_tenant_uuid_rejected() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/market/rdn",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": "not-a-uuid"},
        )
    assert resp.status_code in (400, 422), resp.text


async def test_rdn_tenant_outside_allowlist_rejected() -> None:
    # Well-formed UUID but not in the demo allowlist of 3 tenants.
    foreign = "44444444-4444-4444-4444-444444444444"
    async with _client() as client:
        resp = await client.get(
            "/api/v1/market/rdn",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": foreign},
        )
    assert resp.status_code in (400, 401, 403), resp.text


# ---- multi-tenant isolation at HTTP layer ----


async def test_rdn_multi_tenant_isolation() -> None:
    """Different tenants must see different RDN rowsets.

    We don't assume specific lengths — only that the SETS differ
    (different bidding_zone_eic / row content) when RLS is active.
    Both could be empty, both could be non-empty — but if both are
    non-empty, the row identities should not be a subset/superset
    where tenant A's rows are exactly tenant B's rows.
    """
    async with _client() as client:
        r_prod = await client.get(
            "/api/v1/market/rdn",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
        r_ci = await client.get(
            "/api/v1/market/rdn",
            params={"date_start": SYNTH_DATE, "date_end": SYNTH_DATE},
            headers={"X-Tenant-Id": TENANT_CI},
        )

    assert r_prod.status_code == 200, r_prod.text
    assert r_ci.status_code == 200, r_ci.text
    data_prod = r_prod.json()["data"]
    data_ci = r_ci.json()["data"]

    # meta.tenant_id must reflect the requested tenant.
    assert r_prod.json()["meta"]["tenant_id"] == TENANT_PRODUCER
    assert r_ci.json()["meta"]["tenant_id"] == TENANT_CI

    # If both have rows, identify by (date, hour, bidding_zone_eic, price)
    # — at least one row should differ to prove RLS isolation took effect.
    if data_prod and data_ci:
        sig_prod = {
            (r["date"], r["hour"], r["bidding_zone_eic"], r["price_uah_mwh"])
            for r in data_prod
        }
        sig_ci = {
            (r["date"], r["hour"], r["bidding_zone_eic"], r["price_uah_mwh"])
            for r in data_ci
        }
        assert sig_prod != sig_ci, (
            "RLS isolation broken: producer and CI tenants returned identical "
            "RDN rowsets — they should be tenant-scoped."
        )
