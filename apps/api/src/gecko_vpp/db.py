"""Async SQLAlchemy engine + session factory.

The DB layer (alembic) uses the sync psycopg driver; the app itself uses
async asyncpg per ARCHITECTURE.md §6.2.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from gecko_vpp.config import get_settings
from gecko_vpp.models.base import Base, metadata  # noqa: F401  (re-export)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily-built async engine.

    Uses `api_database_url` (gecko_api role, NOBYPASSRLS) so RLS applies
    at runtime. The superuser `database_url` is reserved for migrations.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.api_database_url,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency / context manager for an async session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
