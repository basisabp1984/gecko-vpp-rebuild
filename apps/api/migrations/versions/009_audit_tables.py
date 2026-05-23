"""009 audit schema tables

Revision ID: 009_audit
Revises: 008_agents
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.8 — audit.events.
"""
from __future__ import annotations

from alembic import op

revision: str = "009_audit"
down_revision: str | None = "008_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit.events (
            id          BIGSERIAL PRIMARY KEY,
            tenant_id   UUID,
            user_id     UUID REFERENCES core.users(id),
            actor       TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            ref_table   TEXT,
            ref_id      TEXT,
            payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            request_id  UUID
        );
        CREATE INDEX ix_audit_events_tenant_occurred
            ON audit.events (tenant_id, occurred_at DESC);
        CREATE INDEX ix_audit_events_type_occurred
            ON audit.events (event_type, occurred_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit.events CASCADE")
