"""005 dispatch schema tables

Revision ID: 005_dispatch
Revises: 004_market
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.4 — setpoints, telemetry (partitioned by month),
instructions, instruction_acks, operator_adjustments.

CRITICAL (F16): dispatch.telemetry.interval_start is a PLAIN TIMESTAMPTZ —
NOT GENERATED — because Postgres forbids GENERATED columns as partition
keys. Synth must compute interval_start arithmetically.

Two partitions created in this same migration so synth INSERTs work
immediately after upgrade:
  - telemetry_2026_04: 2026-04-01 .. 2026-05-01
  - telemetry_2026_05: 2026-05-01 .. 2026-06-01
"""
from __future__ import annotations

from alembic import op

revision: str = "005_dispatch"
down_revision: str | None = "004_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE dispatch.setpoints (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            asset_id        UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
            issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            effective_from  TIMESTAMPTZ NOT NULL,
            effective_to    TIMESTAMPTZ NOT NULL,
            target_power_mw NUMERIC(8,3) NOT NULL,
            target_soc_pct  NUMERIC(5,2),
            reason          TEXT NOT NULL,
            issued_by       TEXT NOT NULL,
            state           TEXT NOT NULL DEFAULT 'pending'
                              CHECK (state IN ('pending','acknowledged','executing','done','cancelled','failed'))
        );
        CREATE INDEX ix_setpoints_tenant_asset_eff ON dispatch.setpoints
            (tenant_id, asset_id, effective_from DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE dispatch.telemetry (
            tenant_id           UUID NOT NULL,
            asset_id            UUID NOT NULL,
            date                DATE NOT NULL,
            hour                SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start      TIMESTAMPTZ NOT NULL,
            active_power_mw     NUMERIC(8,3) NOT NULL,
            reactive_power_mvar NUMERIC(8,3),
            soc_pct             NUMERIC(5,2),
            availability_pct    NUMERIC(5,2) NOT NULL DEFAULT 100,
            status              TEXT NOT NULL DEFAULT 'online'
                                  CHECK (status IN
                                    ('online','idle','maintenance','starting','stopping',
                                     'tripped','curtailed_by_TSO','unavailable')),
            data_quality        CHAR(1) NOT NULL DEFAULT 'R'
                                  CHECK (data_quality IN ('R','V','E','S')),
            source              TEXT NOT NULL DEFAULT 'synthetic',
            extras              JSONB NOT NULL DEFAULT '{}'::jsonb,
            PRIMARY KEY (tenant_id, asset_id, interval_start)
        ) PARTITION BY RANGE (interval_start);

        CREATE TABLE dispatch.telemetry_2026_04 PARTITION OF dispatch.telemetry
            FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
        CREATE TABLE dispatch.telemetry_2026_05 PARTITION OF dispatch.telemetry
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

        CREATE INDEX ix_telemetry_tenant_date_hour ON dispatch.telemetry
            (tenant_id, date, hour);
        CREATE INDEX ix_telemetry_asset_interval ON dispatch.telemetry
            (asset_id, interval_start DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE dispatch.instructions (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            setpoint_id     BIGINT REFERENCES dispatch.setpoints(id),
            asset_id        UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
            instruction_kind TEXT NOT NULL CHECK
                              (instruction_kind IN ('setpoint','curtail','restore','start','stop','test')),
            payload         JSONB NOT NULL,
            queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            dispatched_at   TIMESTAMPTZ,
            priority        SMALLINT NOT NULL DEFAULT 5
        );
        CREATE INDEX ix_instructions_tenant_queued ON dispatch.instructions
            (tenant_id, queued_at DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE dispatch.instruction_acks (
            instruction_id  BIGINT PRIMARY KEY REFERENCES dispatch.instructions(id) ON DELETE CASCADE,
            tenant_id       UUID NOT NULL,
            acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            ack_status      TEXT NOT NULL CHECK (ack_status IN ('ack','nack','timeout')),
            ack_payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
            notes           TEXT
        );
        """
    )

    op.execute(
        """
        CREATE TABLE dispatch.operator_adjustments (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            asset_id        UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
            date            DATE NOT NULL,
            hour            SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            operator_mw     NUMERIC(8,3) NOT NULL,
            reason          TEXT NOT NULL,
            operator_user_id UUID REFERENCES core.users(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, asset_id, date, hour)
        );
        """
    )


def downgrade() -> None:
    for t in [
        "dispatch.operator_adjustments",
        "dispatch.instruction_acks",
        "dispatch.instructions",
        "dispatch.telemetry_2026_05",
        "dispatch.telemetry_2026_04",
        "dispatch.telemetry",
        "dispatch.setpoints",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
