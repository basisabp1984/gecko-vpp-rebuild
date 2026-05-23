"""011 BRIN indexes + table grants

Revision ID: 011_idx_grants
Revises: 010_rls
Create Date: 2026-05-23

- BRIN index on dispatch.telemetry (interval_start) — partition-friendly,
  beats btree for append-only time-series.
- GRANT SELECT/INSERT/UPDATE/DELETE on every table and USAGE on sequences
  to the gecko_api role created in migration 002.
"""
from __future__ import annotations

from alembic import op

revision: str = "011_idx_grants"
down_revision: str | None = "010_rls"
branch_labels = None
depends_on = None


SCHEMAS = ["core", "market", "dispatch", "ems", "regulatory", "agents", "audit"]


def upgrade() -> None:
    # BRIN index on telemetry partition key — cheap range scans.
    op.execute(
        "CREATE INDEX ix_telemetry_brin_interval "
        "ON dispatch.telemetry USING BRIN (interval_start)"
    )

    # Grant CRUD on every table in every schema.
    for s in SCHEMAS:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {s} "
            f"TO gecko_api"
        )
        op.execute(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {s} TO gecko_api"
        )
        # And for future tables created in this schema:
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {s} "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gecko_api"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {s} "
            f"GRANT USAGE, SELECT ON SEQUENCES TO gecko_api"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS dispatch.ix_telemetry_brin_interval")
    for s in SCHEMAS:
        op.execute(
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {s} "
            f"FROM gecko_api"
        )
        op.execute(
            f"REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {s} FROM gecko_api"
        )
