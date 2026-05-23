"""003 core schema tables

Revision ID: 003_core
Revises: 002_roles
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.2 — tenants, users, eic_codes, assets.
"""
from __future__ import annotations

from alembic import op

revision: str = "003_core"
down_revision: str | None = "002_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgcrypto is needed for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(
        """
        CREATE TABLE core.tenants (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code            TEXT NOT NULL UNIQUE,
            display_name    TEXT NOT NULL,
            segment         TEXT NOT NULL CHECK (segment IN ('producer','c-i','storage')),
            edrpou          CHAR(8) NOT NULL,
            participant_eic CHAR(16) NOT NULL,
            bzn_eic         CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            region          TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            is_demo         BOOLEAN NOT NULL DEFAULT TRUE
        );
        COMMENT ON TABLE core.tenants IS
          'Mock multi-tenancy: 3 demo customers, one per segment A/B/C (BRIEF §3, §11.2)';
        CREATE UNIQUE INDEX uq_tenants_participant_eic ON core.tenants (participant_eic);
        """
    )

    op.execute(
        """
        CREATE TABLE core.users (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            email        TEXT NOT NULL,
            display_name TEXT NOT NULL,
            role         TEXT NOT NULL CHECK (role IN ('operator','manager','admin','viewer')),
            invited_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            accepted_at  TIMESTAMPTZ
        );
        CREATE UNIQUE INDEX uq_users_tenant_email ON core.users (tenant_id, email);
        """
    )

    op.execute(
        """
        CREATE TABLE core.eic_codes (
            eic          CHAR(16) PRIMARY KEY,
            code_type    CHAR(1) NOT NULL CHECK (code_type IN ('Y','X','W','V','T','Z')),
            display_name TEXT NOT NULL,
            issuer       TEXT,
            valid_from   DATE,
            valid_to     DATE,
            metadata     JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        COMMENT ON COLUMN core.eic_codes.code_type IS
          'ENTSO-E EIC position-3 classifier — see research_regulatory_data_shape.md §6';
        """
    )

    op.execute(
        """
        CREATE TABLE core.assets (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            code                 TEXT NOT NULL,
            display_name         TEXT NOT NULL,
            asset_class          TEXT NOT NULL CHECK (asset_class IN
                                   ('СЕС','ВЕС','ГПУ','УЗЕ','АктСпож','Споживач')),
            technology_type      CHAR(3) NOT NULL,
            resource_eic         CHAR(16) NOT NULL REFERENCES core.eic_codes(eic),
            metering_eic         CHAR(16) REFERENCES core.eic_codes(eic),
            capacity_mw          NUMERIC(8,3) NOT NULL CHECK (capacity_mw > 0),
            storage_capacity_mwh NUMERIC(8,3),
            region               TEXT NOT NULL,
            commissioned_on      DATE NOT NULL,
            status               TEXT NOT NULL DEFAULT 'active'
                                  CHECK (status IN ('active','maintenance','decommissioned')),
            bzn_eic              CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, code)
        );
        CREATE INDEX ix_assets_tenant_class ON core.assets (tenant_id, asset_class);
        CREATE INDEX ix_assets_resource_eic ON core.assets (resource_eic);
        COMMENT ON TABLE core.assets IS
          'Asset registry. Total portfolio ≈ 50 МВт across 8–12 assets (BRIEF §4).';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS core.assets CASCADE")
    op.execute("DROP TABLE IF EXISTS core.eic_codes CASCADE")
    op.execute("DROP TABLE IF EXISTS core.users CASCADE")
    op.execute("DROP TABLE IF EXISTS core.tenants CASCADE")
