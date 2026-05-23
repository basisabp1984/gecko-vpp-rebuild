"""008 agents schema tables

Revision ID: 008_agents
Revises: 007_regulatory
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.7 — agents.query_log, agents.response_cache.
"""
from __future__ import annotations

from alembic import op

revision: str = "008_agents"
down_revision: str | None = "007_regulatory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE agents.query_log (
            id                BIGSERIAL PRIMARY KEY,
            tenant_id         UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            persona           TEXT NOT NULL CHECK
                                (persona IN ('dispatcher_analyst','market_analyst',
                                             'energy_advisor','battery_coach')),
            user_text         TEXT NOT NULL,
            classified_intent TEXT NOT NULL,
            confidence        NUMERIC(4,3) NOT NULL,
            response_text     TEXT NOT NULL,
            evidence          JSONB NOT NULL DEFAULT '[]'::jsonb,
            duration_ms       INTEGER NOT NULL,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_query_log_tenant_created
            ON agents.query_log (tenant_id, created_at DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE agents.response_cache (
            cache_key     TEXT PRIMARY KEY,
            response_text TEXT NOT NULL,
            evidence      JSONB NOT NULL DEFAULT '[]'::jsonb,
            persona       TEXT NOT NULL,
            cached_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            ttl_seconds   INTEGER NOT NULL DEFAULT 300
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agents.response_cache CASCADE")
    op.execute("DROP TABLE IF EXISTS agents.query_log CASCADE")
