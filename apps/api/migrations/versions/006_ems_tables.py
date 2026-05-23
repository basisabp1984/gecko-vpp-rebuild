"""006 ems schema tables

Revision ID: 006_ems
Revises: 005_dispatch
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.5 — forecasts, forecast_actuals, kpi_daily,
kpi_portfolio_30d materialised view, optimisation_runs.
"""
from __future__ import annotations

from alembic import op

revision: str = "006_ems"
down_revision: str | None = "005_dispatch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ems.forecasts (
            id             BIGSERIAL PRIMARY KEY,
            tenant_id      UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            asset_id       UUID REFERENCES core.assets(id) ON DELETE CASCADE,
            forecast_kind  TEXT NOT NULL CHECK
                             (forecast_kind IN ('solar','wind','load','price','consumption')),
            forecast_type  TEXT NOT NULL CHECK (forecast_type IN ('primary','refined')),
            issued_at      TIMESTAMPTZ NOT NULL,
            date           DATE NOT NULL,
            hour           SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start TIMESTAMP GENERATED ALWAYS AS
                             (date + make_interval(hours => hour - 1)) STORED,
            value_mwh      NUMERIC(10,4) NOT NULL,
            model_id       TEXT NOT NULL DEFAULT 'synth-v1',
            confidence_lo  NUMERIC(10,4),
            confidence_hi  NUMERIC(10,4),
            UNIQUE (tenant_id, asset_id, forecast_kind, forecast_type, date, hour)
        );
        CREATE INDEX ix_forecasts_tenant_kind_date ON ems.forecasts
            (tenant_id, forecast_kind, date);
        """
    )

    op.execute(
        """
        CREATE TABLE ems.forecast_actuals (
            tenant_id      UUID NOT NULL,
            asset_id       UUID NOT NULL,
            forecast_kind  TEXT NOT NULL,
            date           DATE NOT NULL,
            hour           SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start TIMESTAMP GENERATED ALWAYS AS
                             (date + make_interval(hours => hour - 1)) STORED,
            actual_mwh     NUMERIC(10,4) NOT NULL,
            PRIMARY KEY (tenant_id, asset_id, forecast_kind, date, hour)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE ems.kpi_daily (
            tenant_id         UUID NOT NULL,
            asset_id          UUID NOT NULL,
            date              DATE NOT NULL,
            grn_saved_uah     NUMERIC(14,2) NOT NULL DEFAULT 0,
            grn_earned_uah    NUMERIC(14,2) NOT NULL DEFAULT 0,
            imbalance_mwh     NUMERIC(10,4) NOT NULL DEFAULT 0,
            co2_avoided_tn    NUMERIC(10,3) NOT NULL DEFAULT 0,
            availability_pct  NUMERIC(5,2) NOT NULL DEFAULT 100,
            opportunity_score SMALLINT NOT NULL DEFAULT 0
                                CHECK (opportunity_score BETWEEN 0 AND 100),
            notes             TEXT,
            PRIMARY KEY (tenant_id, asset_id, date)
        );

        CREATE MATERIALIZED VIEW ems.kpi_portfolio_30d AS
        SELECT
            tenant_id,
            SUM(grn_saved_uah)::NUMERIC(14,2)  AS grn_saved_uah,
            SUM(grn_earned_uah)::NUMERIC(14,2) AS grn_earned_uah,
            SUM(imbalance_mwh)::NUMERIC(12,4)  AS imbalance_mwh,
            SUM(co2_avoided_tn)::NUMERIC(12,3) AS co2_avoided_tn,
            AVG(availability_pct)::NUMERIC(5,2) AS availability_pct,
            AVG(opportunity_score)::SMALLINT   AS opportunity_score
        FROM ems.kpi_daily
        WHERE date BETWEEN '2026-04-23' AND '2026-05-23'
        GROUP BY tenant_id;
        """
    )

    op.execute(
        """
        CREATE TABLE ems.optimisation_runs (
            id                  BIGSERIAL PRIMARY KEY,
            tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            requested_by        UUID REFERENCES core.users(id),
            requested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at        TIMESTAMPTZ,
            scenario            TEXT NOT NULL,
            inputs_hash         CHAR(64) NOT NULL,
            inputs              JSONB NOT NULL,
            recommendations     JSONB NOT NULL,
            expected_uplift_uah NUMERIC(14,2) NOT NULL,
            risk_flags          JSONB NOT NULL DEFAULT '[]'::jsonb,
            confidence_pct      NUMERIC(5,2) NOT NULL,
            duration_ms         INTEGER NOT NULL
        );
        CREATE INDEX ix_optimisation_runs_tenant_requested
            ON ems.optimisation_runs (tenant_id, requested_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ems.optimisation_runs CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS ems.kpi_portfolio_30d")
    op.execute("DROP TABLE IF EXISTS ems.kpi_daily CASCADE")
    op.execute("DROP TABLE IF EXISTS ems.forecast_actuals CASCADE")
    op.execute("DROP TABLE IF EXISTS ems.forecasts CASCADE")
