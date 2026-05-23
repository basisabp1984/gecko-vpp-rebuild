"""Pytest fixtures: async engine, isolated test data hygiene."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import gecko_vpp.db as _db
from gecko_vpp.config import get_settings


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine_at_session_end() -> AsyncIterator[None]:
    """Dispose the module-level async engine when the test session ends.

    With ``asyncio_default_fixture_loop_scope = "session"`` all tests share
    one event loop, so the singleton ``_db._engine`` stays valid across
    tests. We just need a single teardown after the whole session so the
    asyncpg connection pool is closed cleanly.
    """
    yield
    await _db.dispose_engine()


@pytest_asyncio.fixture
async def gecko_api_engine() -> AsyncIterator[AsyncEngine]:
    """Async engine connecting AS the `gecko_api` role (NOBYPASSRLS).

    The base DATABASE_URL connects as superuser `gecko`; here we swap to
    `gecko_api` so RLS actually applies (FORCE RLS would catch the
    superuser too, but using gecko_api mirrors production exactly).
    """
    settings = get_settings()
    url = settings.database_url
    prefix, rest = url.split("://", 1)
    _userinfo, host_part = rest.split("@", 1)
    api_url = f"{prefix}://gecko_api:gecko_api_pwd@{host_part}"
    engine = create_async_engine(api_url, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()
