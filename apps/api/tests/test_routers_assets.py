"""Tests for GET /api/v1/assets.

Coverage:
  * Envelope + per-row schema (id, code, display_name, asset_class,
    capacity_mw, region).
  * asset_class belongs to the Ukrainian VPP taxonomy
    (СЕС / ВЕС / ГПУ / УЗЕ).
  * capacity_mw is serialised as a string (Decimal → str) and parses as a
    positive number.
  * Multi-tenant isolation — TENANT_PRODUCER and TENANT_CI must return
    distinct asset sets (different code/id signature when both non-empty).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from gecko_vpp.config import get_settings
from gecko_vpp.main import app

pytestmark = pytest.mark.asyncio


settings = get_settings()
TENANT_PRODUCER = settings.tenant_producer_uuid
TENANT_CI = settings.tenant_ci_uuid

ALLOWED_ASSET_CLASSES = {"СЕС", "ВЕС", "ГПУ", "УЗЕ"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_assets_shape_for_producer() -> None:
    async with _client() as client:
        resp = await client.get(
            "/api/v1/assets",
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["tenant_id"] == TENANT_PRODUCER
    assert isinstance(body["data"], list)

    for asset in body["data"]:
        for key in (
            "id",
            "code",
            "display_name",
            "asset_class",
            "capacity_mw",
            "region",
        ):
            assert key in asset, f"missing key {key} in {asset}"
        assert asset["asset_class"] in ALLOWED_ASSET_CLASSES, (
            f"unexpected asset_class={asset['asset_class']!r} "
            f"(allowed: {ALLOWED_ASSET_CLASSES})"
        )
        # capacity_mw is Decimal serialised as string per dec_to_str.
        cap = Decimal(str(asset["capacity_mw"]))
        assert cap > 0, f"capacity_mw must be positive, got {cap}"


async def test_assets_missing_tenant_header_rejected() -> None:
    async with _client() as client:
        resp = await client.get("/api/v1/assets")
    assert resp.status_code in (400, 422), resp.text


async def test_assets_multi_tenant_isolation() -> None:
    """Producer and CI tenants should see different asset rosters."""
    async with _client() as client:
        r_prod = await client.get(
            "/api/v1/assets",
            headers={"X-Tenant-Id": TENANT_PRODUCER},
        )
        r_ci = await client.get(
            "/api/v1/assets",
            headers={"X-Tenant-Id": TENANT_CI},
        )

    assert r_prod.status_code == 200, r_prod.text
    assert r_ci.status_code == 200, r_ci.text
    prod_codes = {a["code"] for a in r_prod.json()["data"]}
    ci_codes = {a["code"] for a in r_ci.json()["data"]}

    # Empty DB (e.g. fresh CI before seed): isolation is untestable.
    # The schema-correctness check is already covered by the previous test;
    # without rows to compare, we can't prove or disprove isolation here.
    if not prod_codes and not ci_codes:
        pytest.skip(
            "no seeded assets — isolation untestable on an empty DB "
            "(this is expected in fresh CI; run data-generator to enable)",
        )

    # If both non-empty, code-sets must differ.
    if prod_codes and ci_codes:
        assert prod_codes != ci_codes, (
            "RLS leak: producer and CI tenants returned identical "
            "asset code sets — assets must be tenant-scoped."
        )
