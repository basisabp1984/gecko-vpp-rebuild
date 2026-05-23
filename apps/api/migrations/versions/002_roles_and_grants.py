"""002 roles and schema-level grants

Revision ID: 002_roles
Revises: 001_init_schemas
Create Date: 2026-05-23

Idempotently creates the `gecko_api` (NOBYPASSRLS) role used by the FastAPI
app. Per BACKEND_DB_INSTRUCTIONS: GRANT on tables is in migration 011 (after
tables exist). Migration 002 grants USAGE on schemas only.

Note: this migration runs under the bootstrap superuser (`gecko`); it is the
only place that touches roles. In a hardened deploy a separate `gecko_migrate`
role would do this; for the demo we collapse those.
"""
from __future__ import annotations

from alembic import op

revision: str = "002_roles"
down_revision: str | None = "001_init_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gecko_api') THEN
                CREATE ROLE gecko_api LOGIN PASSWORD 'gecko_api_pwd';
            END IF;
            ALTER ROLE gecko_api NOBYPASSRLS;
        END
        $$;
        """
    )

    # USAGE on every schema; table-level grants come in migration 011.
    op.execute(
        "GRANT USAGE ON SCHEMA core, market, dispatch, ems, regulatory, "
        "agents, audit TO gecko_api"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE USAGE ON SCHEMA core, market, dispatch, ems, regulatory, "
        "agents, audit FROM gecko_api"
    )
    # Don't DROP ROLE — other objects may depend on it. Manual cleanup if needed.
