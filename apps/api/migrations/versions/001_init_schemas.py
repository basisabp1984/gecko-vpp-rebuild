"""001 init schemas

Revision ID: 001_init_schemas
Revises:
Create Date: 2026-05-23

Creates the 7 top-level Postgres schemas.
"""
from __future__ import annotations

from alembic import op

revision: str = "001_init_schemas"
down_revision: str | None = None
branch_labels = None
depends_on = None

SCHEMAS = ["core", "market", "dispatch", "ems", "regulatory", "agents", "audit"]


def upgrade() -> None:
    for s in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")


def downgrade() -> None:
    for s in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {s} CASCADE")
