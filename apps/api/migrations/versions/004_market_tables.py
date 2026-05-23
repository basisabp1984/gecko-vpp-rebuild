"""004 market schema tables

Revision ID: 004_market
Revises: 003_core
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.3 — rdn_prices, vdr_trades, br_settlements,
dd_contracts (+hourly_volume), bids, ancillary_offers, ancillary_activations.

`interval_start` is GENERATED ALWAYS AS STORED on every table — this is safe
because none of these tables are partitioned (only dispatch.telemetry is).

DEVIATION FROM ARCHITECT'S DDL (logged in difficulties_log.md):
The architect's expression uses `((date + ((hour-1) || ' hour')::INTERVAL)
AT TIME ZONE 'Europe/Kyiv')` which Postgres rejects with "generation
expression is not immutable" (the `||` integer→text cast and `AT TIME ZONE`
both depend on session settings). Replaced with the equivalent immutable
form `(date + make_interval(hours => hour-1))`, which yields a TIMESTAMP
(without tz). Since the 30-day window has no DST transition inside it,
treating this as wall-clock Kyiv local time matches the architect's intent
exactly (see ARCHITECTURE.md §6 — Europe/Kyiv treated as steady +03:00).
"""
from __future__ import annotations

from alembic import op

revision: str = "004_market"
down_revision: str | None = "003_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE market.rdn_prices (
            id                  BIGSERIAL PRIMARY KEY,
            tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            bidding_zone_eic    CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            date                DATE NOT NULL,
            hour                SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start      TIMESTAMP GENERATED ALWAYS AS
                                  (date + make_interval(hours => hour - 1))
                                  STORED,
            price_uah_mwh       NUMERIC(10,2) NOT NULL,
            volume_mwh          NUMERIC(12,3) NOT NULL,
            is_capped           BOOLEAN NOT NULL DEFAULT FALSE,
            cap_uah_mwh         NUMERIC(10,2),
            daily_index_base    NUMERIC(10,2),
            daily_index_peak    NUMERIC(10,2),
            daily_index_offpeak NUMERIC(10,2),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, bidding_zone_eic, date, hour)
        );
        CREATE INDEX ix_rdn_prices_tenant_date ON market.rdn_prices (tenant_id, date);
        CREATE INDEX ix_rdn_prices_interval ON market.rdn_prices (interval_start);
        COMMENT ON TABLE market.rdn_prices IS
          'РДН hourly prices. Cap-pinning modelled per HLA D4. UA convention hour 1..24.';
        """
    )

    op.execute(
        """
        CREATE TABLE market.vdr_trades (
            id               BIGSERIAL PRIMARY KEY,
            tenant_id        UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            trade_id         TEXT NOT NULL,
            executed_at      TIMESTAMPTZ NOT NULL,
            delivery_date    DATE NOT NULL,
            delivery_hour    SMALLINT NOT NULL CHECK (delivery_hour BETWEEN 1 AND 24),
            interval_start   TIMESTAMP GENERATED ALWAYS AS
                               (delivery_date + make_interval(hours => delivery_hour - 1)) STORED,
            volume_mwh       NUMERIC(10,3) NOT NULL,
            price_uah_mwh    NUMERIC(10,2) NOT NULL,
            side             TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
            counterparty_code TEXT NOT NULL,
            resource_eic     CHAR(16),
            bidding_zone_eic CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            UNIQUE (tenant_id, trade_id)
        );
        CREATE INDEX ix_vdr_trades_tenant_del ON market.vdr_trades
            (tenant_id, delivery_date, delivery_hour);
        CREATE INDEX ix_vdr_trades_res_interval ON market.vdr_trades
            (resource_eic, interval_start);
        """
    )

    op.execute(
        """
        CREATE TABLE market.br_settlements (
            id                  BIGSERIAL PRIMARY KEY,
            tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            date                DATE NOT NULL,
            hour                SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start      TIMESTAMP GENERATED ALWAYS AS
                                  (date + make_interval(hours => hour - 1)) STORED,
            price_short_uah_mwh NUMERIC(10,2) NOT NULL,
            price_long_uah_mwh  NUMERIC(10,2) NOT NULL,
            system_direction    TEXT NOT NULL CHECK
                                  (system_direction IN ('SHORT','LONG','BALANCED')),
            our_imbalance_mwh   NUMERIC(10,3) NOT NULL,
            settlement_uah      NUMERIC(14,2) NOT NULL,
            bidding_zone_eic    CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            UNIQUE (tenant_id, date, hour)
        );
        CREATE INDEX ix_br_settlements_tenant_date ON market.br_settlements (tenant_id, date);
        CREATE INDEX ix_br_settlements_interval ON market.br_settlements (interval_start);
        """
    )

    op.execute(
        """
        CREATE TABLE market.dd_contracts (
            id                  BIGSERIAL PRIMARY KEY,
            tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            contract_no         TEXT NOT NULL,
            counterparty_name   TEXT NOT NULL,
            counterparty_edrpou CHAR(8),
            profile_type        TEXT NOT NULL CHECK
                                  (profile_type IN ('BASE','PEAK','OFFPEAK','INDIVIDUAL')),
            start_date          DATE NOT NULL,
            end_date            DATE NOT NULL,
            price_uah_mwh       NUMERIC(10,2),
            price_formula       TEXT,
            total_volume_mwh    NUMERIC(14,3),
            bidding_zone_eic    CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            status              TEXT NOT NULL DEFAULT 'ACTIVE'
                                  CHECK (status IN ('DRAFT','ACTIVE','CLOSED')),
            UNIQUE (tenant_id, contract_no)
        );

        CREATE TABLE market.dd_contract_hourly_volume (
            contract_id    BIGINT NOT NULL REFERENCES market.dd_contracts(id) ON DELETE CASCADE,
            tenant_id      UUID NOT NULL,
            date           DATE NOT NULL,
            hour           SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start TIMESTAMP GENERATED ALWAYS AS
                             (date + make_interval(hours => hour - 1)) STORED,
            volume_mwh     NUMERIC(10,3) NOT NULL,
            PRIMARY KEY (contract_id, date, hour)
        );
        CREATE INDEX ix_dd_hourly_tenant_date ON market.dd_contract_hourly_volume
            (tenant_id, date);
        """
    )

    op.execute(
        """
        CREATE TABLE market.bids (
            id                  BIGSERIAL PRIMARY KEY,
            tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            bid_id              TEXT NOT NULL,
            market              TEXT NOT NULL CHECK (market IN ('RDN','VDR','BR','DD')),
            delivery_date       DATE NOT NULL,
            hour                SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start      TIMESTAMP GENERATED ALWAYS AS
                                  (delivery_date + make_interval(hours => hour - 1)) STORED,
            side                TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
            bid_type            TEXT NOT NULL CHECK
                                  (bid_type IN ('SIMPLE','BLOCK','STEP','LIMIT','IOC','FOK')),
            block_id            UUID,
            volume_mwh          NUMERIC(10,3) NOT NULL,
            price_uah_mwh       NUMERIC(10,2) NOT NULL,
            technology_type     CHAR(3),
            participant_eic     CHAR(16) NOT NULL,
            resource_eic        CHAR(16),
            submitted_at        TIMESTAMPTZ NOT NULL,
            state               TEXT NOT NULL DEFAULT 'ACTIVE'
                                  CHECK (state IN ('ACTIVE','ACCEPTED','PARTIAL','REJECTED','CANCELLED')),
            accepted_volume_mwh NUMERIC(10,3),
            clearing_price      NUMERIC(10,2),
            settlement_amount   NUMERIC(14,2),
            UNIQUE (tenant_id, bid_id)
        );
        CREATE INDEX ix_bids_tenant_market_del ON market.bids
            (tenant_id, market, delivery_date, hour);
        CREATE INDEX ix_bids_res_interval ON market.bids
            (resource_eic, interval_start);
        """
    )

    op.execute(
        """
        CREATE TABLE market.ancillary_offers (
            id                     BIGSERIAL PRIMARY KEY,
            tenant_id              UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            asset_id               UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
            date                   DATE NOT NULL,
            hour                   SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
            interval_start         TIMESTAMP GENERATED ALWAYS AS
                                     (date + make_interval(hours => hour - 1)) STORED,
            service                TEXT NOT NULL CHECK
                                     (service IN ('FCR','aFRR_up','aFRR_down','mFRR_up','mFRR_down','RR')),
            offered_capacity_mw    NUMERIC(8,3) NOT NULL,
            cleared_capacity_mw    NUMERIC(8,3) NOT NULL DEFAULT 0,
            capacity_price_eur_mwh NUMERIC(10,4) NOT NULL,
            revenue_capacity_uah   NUMERIC(14,2) NOT NULL DEFAULT 0,
            UNIQUE (tenant_id, asset_id, date, hour, service)
        );

        CREATE TABLE market.ancillary_activations (
            id                   BIGSERIAL PRIMARY KEY,
            tenant_id            UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            asset_id             UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
            service              TEXT NOT NULL CHECK
                                   (service IN ('FCR','aFRR_up','aFRR_down','mFRR_up','mFRR_down','RR')),
            started_at           TIMESTAMPTZ NOT NULL,
            ended_at             TIMESTAMPTZ NOT NULL,
            avg_power_mw         NUMERIC(8,3) NOT NULL,
            energy_mwh           NUMERIC(10,4) NOT NULL,
            energy_price_uah_mwh NUMERIC(10,2) NOT NULL,
            revenue_energy_uah   NUMERIC(14,2) NOT NULL
        );
        CREATE INDEX ix_anc_act_tenant_asset_started
            ON market.ancillary_activations (tenant_id, asset_id, started_at DESC);
        """
    )


def downgrade() -> None:
    for t in [
        "market.ancillary_activations",
        "market.ancillary_offers",
        "market.bids",
        "market.dd_contract_hourly_volume",
        "market.dd_contracts",
        "market.br_settlements",
        "market.vdr_trades",
        "market.rdn_prices",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
