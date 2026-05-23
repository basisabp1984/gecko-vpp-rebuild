"""Async DB engine + session helpers.

We connect as the ``gecko`` superuser (BYPASSRLS) so the generator can
freely INSERT across all tenants without setting ``app.tenant_id``. RLS is
enforced for the runtime ``gecko_api`` role, not for the seeder.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)

from data_generator.config import DATABASE_URL


_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Lazily build the async engine. One per process."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=4,
            max_overflow=4,
            future=True,
        )
    return _engine


@asynccontextmanager
async def connect() -> AsyncIterator[AsyncConnection]:
    """Yield a transactional async connection. Commits on success."""
    engine = get_engine()
    async with engine.begin() as conn:
        yield conn


async def dispose() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
