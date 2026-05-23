"""Pytest fixtures: async engine, isolated test data hygiene."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gecko_vpp.config import get_settings


@pytest_asyncio.fixture
async def gecko_api_engine() -> AsyncIterator[AsyncEngine]:
    """Async engine connecting AS the `gecko_api` role (NOBYPASSRLS).

    The base DATABASE_URL connects as superuser `gecko`; here we swap to
    `gecko_api` so RLS actually applies (FORCE RLS would catch the
    superuser too, but using gecko_api mirrors production exactly).
    """
    settings = get_settings()
    # Swap the userinfo of the URL to gecko_api.
    url = settings.database_url
    # postgresql+asyncpg://gecko:dev_local_pwd_2026@host:port/db
    # → postgresql+asyncpg://gecko_api:gecko_api_pwd@host:port/db
    prefix, rest = url.split("://", 1)
    _userinfo, host_part = rest.split("@", 1)
    api_url = f"{prefix}://gecko_api:gecko_api_pwd@{host_part}"
    engine = create_async_engine(api_url, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()
