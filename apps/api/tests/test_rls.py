"""RLS smoke test — proves tenant A cannot see tenant B's rows.

Strategy:
  1. Connect as `gecko_api` (NOBYPASSRLS, also overridden by FORCE RLS).
  2. Session 1: SET app.tenant_id = TENANT_PRODUCER → INSERT a rdn_prices row.
  3. Session 1: SELECT count → expect 1.
  4. Session 2: SET app.tenant_id = TENANT_CI → SELECT count → expect 0.
  5. Cleanup.

Acceptance per BACKEND_DB_INSTRUCTIONS §2 line 26:
  "connection A with app.tenant_id=<X> cannot see connection B's rows
   where tenant_id=<Y>".
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from gecko_vpp.config import get_settings

pytestmark = pytest.mark.asyncio

settings = get_settings()
TENANT_PRODUCER = settings.tenant_producer_uuid
TENANT_CI = settings.tenant_ci_uuid


async def _set_tenant(conn, tenant_id: str) -> None:
    # SET LOCAL requires being inside a transaction; conn.begin() opens one.
    await conn.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))


async def test_rls_blocks_cross_tenant_select(gecko_api_engine: AsyncEngine) -> None:
    """Inserts a row as TENANT_PRODUCER, fails to see it as TENANT_CI."""

    # --- 1. Setup: ensure no leftover row exists for our marker tenant_id.
    # We use a unique bidding_zone_eic as a marker so cleanup is precise.
    # Admin bypass only covers SELECT (see migration 010), so we delete
    # while tenant=PRODUCER (the only tenant that could have inserted it).
    marker_bzn = "10Y1001C--RLS-T"  # 16 chars, never produced by anything else

    async with gecko_api_engine.begin() as conn:
        await _set_tenant(conn, TENANT_PRODUCER)
        await conn.execute(
            text(
                "DELETE FROM market.rdn_prices WHERE bidding_zone_eic = :bzn"
            ),
            {"bzn": marker_bzn},
        )

    # --- 2. Tenant A (producer) inserts a row
    async with gecko_api_engine.begin() as conn:
        await _set_tenant(conn, TENANT_PRODUCER)
        await conn.execute(
            text(
                """
                INSERT INTO market.rdn_prices
                    (tenant_id, bidding_zone_eic, date, hour, price_uah_mwh, volume_mwh)
                VALUES (:t, :bzn, '2026-05-04', 18, 6300.00, 12.500)
                """
            ),
            {"t": TENANT_PRODUCER, "bzn": marker_bzn},
        )

    # --- 3. Tenant A can see its own row
    async with gecko_api_engine.connect() as conn:
        async with conn.begin():
            await _set_tenant(conn, TENANT_PRODUCER)
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM market.rdn_prices "
                    "WHERE bidding_zone_eic = :bzn"
                ),
                {"bzn": marker_bzn},
            )
            count_a = result.scalar_one()
            assert count_a == 1, (
                f"Tenant A should see its own row, got {count_a}"
            )

    # --- 4. Tenant B cannot see Tenant A's row
    async with gecko_api_engine.connect() as conn:
        async with conn.begin():
            await _set_tenant(conn, TENANT_CI)
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM market.rdn_prices "
                    "WHERE bidding_zone_eic = :bzn"
                ),
                {"bzn": marker_bzn},
            )
            count_b = result.scalar_one()
            assert count_b == 0, (
                "RLS LEAK: Tenant B should NOT see Tenant A's row; "
                f"saw {count_b}"
            )

    # --- 5. Cleanup (delete as the owning tenant)
    async with gecko_api_engine.begin() as conn:
        await _set_tenant(conn, TENANT_PRODUCER)
        await conn.execute(
            text(
                "DELETE FROM market.rdn_prices WHERE bidding_zone_eic = :bzn"
            ),
            {"bzn": marker_bzn},
        )


async def test_rls_blocks_cross_tenant_insert(gecko_api_engine: AsyncEngine) -> None:
    """WITH CHECK clause blocks INSERT with someone else's tenant_id."""
    async with gecko_api_engine.connect() as conn:
        async with conn.begin():
            await _set_tenant(conn, TENANT_PRODUCER)
            # Try to INSERT a row tagged with TENANT_CI — should fail WITH CHECK.
            from sqlalchemy.exc import DBAPIError

            with pytest.raises(DBAPIError):
                await conn.execute(
                    text(
                        """
                        INSERT INTO market.rdn_prices
                            (tenant_id, bidding_zone_eic, date, hour,
                             price_uah_mwh, volume_mwh)
                        VALUES (:t, '10Y1001C--00003F', '2026-05-04', 19,
                                6300.00, 12.500)
                        """
                    ),
                    {"t": TENANT_CI},
                )
