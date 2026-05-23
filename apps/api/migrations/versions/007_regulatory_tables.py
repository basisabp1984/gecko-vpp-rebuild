"""007 regulatory schema tables

Revision ID: 007_regulatory
Revises: 006_ems
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.6 — forecast_submissions, settlement_statements,
settlement_statement_lines, signed_documents, regulator_events.

Order matters: settlement_statements references signed_documents via
signed_doc_id but signed_documents doesn't exist yet → create
settlement_statements WITHOUT the FK, create signed_documents, then ALTER
to add the FK.
"""
from __future__ import annotations

from alembic import op

revision: str = "007_regulatory"
down_revision: str | None = "006_ems"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE regulatory.forecast_submissions (
            id                 BIGSERIAL PRIMARY KEY,
            tenant_id          UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            submission_id      TEXT NOT NULL,
            submitted_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            submitter_eic      CHAR(16) NOT NULL,
            resource_eic       CHAR(16),
            bzn_eic            CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
            business_type      CHAR(3) NOT NULL,
            document_type      CHAR(3) NOT NULL,
            process_type       CHAR(3) NOT NULL,
            delivery_date      DATE NOT NULL,
            resolution_minutes SMALLINT NOT NULL DEFAULT 60,
            hourly_volumes_mwh NUMERIC(10,4)[] NOT NULL,
            status             TEXT NOT NULL DEFAULT 'DRAFT'
                                 CHECK (status IN ('DRAFT','SUBMITTED','ACK','REJECTED')),
            status_changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_xml            TEXT,
            UNIQUE (tenant_id, submission_id)
        );
        CREATE INDEX ix_forecast_submissions_tenant_delivery
            ON regulatory.forecast_submissions (tenant_id, delivery_date);
        """
    )

    op.execute(
        """
        CREATE TABLE regulatory.settlement_statements (
            id                  BIGSERIAL PRIMARY KEY,
            tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            statement_no        TEXT NOT NULL,
            counterparty        TEXT NOT NULL,
            counterparty_edrpou CHAR(8),
            contract_no         TEXT,
            period_year         SMALLINT NOT NULL,
            period_month        SMALLINT NOT NULL CHECK (period_month BETWEEN 1 AND 12),
            period_start        DATE NOT NULL,
            period_end          DATE NOT NULL,
            volume_total_mwh    NUMERIC(14,4) NOT NULL,
            amount_net_uah      NUMERIC(14,2) NOT NULL,
            vat_rate            NUMERIC(4,2) NOT NULL DEFAULT 0.20,
            amount_vat_uah      NUMERIC(14,2) NOT NULL,
            amount_gross_uah    NUMERIC(14,2) NOT NULL,
            payment_due_date    DATE NOT NULL,
            payment_received_at TIMESTAMPTZ,
            status              TEXT NOT NULL DEFAULT 'DRAFT' CHECK
                                  (status IN ('DRAFT','ISSUED','SIGNED','PAID','DISPUTED')),
            signed_doc_id       BIGINT,
            UNIQUE (tenant_id, statement_no)
        );
        CREATE INDEX ix_settlement_statements_tenant_year_month
            ON regulatory.settlement_statements (tenant_id, period_year, period_month);

        CREATE TABLE regulatory.settlement_statement_lines (
            id              BIGSERIAL PRIMARY KEY,
            statement_id    BIGINT NOT NULL REFERENCES regulatory.settlement_statements(id)
                              ON DELETE CASCADE,
            tenant_id       UUID NOT NULL,
            line_no         SMALLINT NOT NULL,
            asset_eic       CHAR(16) NOT NULL,
            asset_name      TEXT NOT NULL,
            technology_type CHAR(3),
            volume_mwh      NUMERIC(12,4) NOT NULL,
            tariff_uah_mwh  NUMERIC(10,2) NOT NULL,
            amount_uah      NUMERIC(14,2) NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE regulatory.signed_documents (
            id                   BIGSERIAL PRIMARY KEY,
            tenant_id            UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
            document_type        TEXT NOT NULL CHECK
                                   (document_type IN
                                     ('SETTLEMENT_ACT','BID_PACKAGE','FORECAST_PACKAGE','REPORT','CONTRACT')),
            document_ref_table   TEXT NOT NULL,
            document_ref_id      BIGINT NOT NULL,
            signer_name          TEXT NOT NULL,
            signer_position      TEXT,
            signer_edrpou        CHAR(8),
            signer_ipn           CHAR(10),
            acsk_name            TEXT NOT NULL,
            signature_format     TEXT NOT NULL DEFAULT 'CAdES-X-Long',
            document_hash_sha256 CHAR(64) NOT NULL,
            signed_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            tsa_provider         TEXT DEFAULT 'czo.gov.ua',
            cert_serial          TEXT,
            cert_valid_until     DATE,
            p7s_blob             BYTEA NOT NULL,
            is_demo_stub         BOOLEAN NOT NULL DEFAULT TRUE,
            -- kep_badge_short: architect spec'd this as GENERATED ALWAYS AS
            -- (... TO_CHAR(signed_at, ...) ...). Postgres rejects that as
            -- non-immutable (TO_CHAR over TIMESTAMPTZ is timezone-dependent).
            -- We instead populate this from the API/synth layer on INSERT.
            -- See difficulties_log.md for details.
            kep_badge_short      TEXT
        );

        -- Backfill kep_badge_short via trigger so it stays in sync.
        CREATE OR REPLACE FUNCTION regulatory._set_kep_badge_short()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.kep_badge_short :=
                NEW.signer_name
                || ' · ЄДРПОУ ' || COALESCE(NEW.signer_edrpou, NEW.signer_ipn, 'n/a')
                || ' · ' || TO_CHAR(NEW.signed_at AT TIME ZONE 'Europe/Kyiv',
                                    'YYYY-MM-DD HH24:MI');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_signed_documents_set_badge
            BEFORE INSERT OR UPDATE ON regulatory.signed_documents
            FOR EACH ROW EXECUTE FUNCTION regulatory._set_kep_badge_short();
        CREATE INDEX ix_signed_documents_ref
            ON regulatory.signed_documents (document_ref_table, document_ref_id);

        ALTER TABLE regulatory.settlement_statements
            ADD CONSTRAINT fk_settlement_signed_doc
            FOREIGN KEY (signed_doc_id)
            REFERENCES regulatory.signed_documents(id);
        """
    )

    op.execute(
        """
        CREATE TABLE regulatory.regulator_events (
            id                BIGSERIAL PRIMARY KEY,
            issuer            TEXT NOT NULL CHECK
                                (issuer IN ('НКРЕКП','Укренерго','Кабмін','ОРЕЕ','ГП')),
            act_type          TEXT NOT NULL,
            act_number        TEXT,
            issued_at         DATE NOT NULL,
            effective_at      DATE,
            title             TEXT NOT NULL,
            category          TEXT CHECK (category IN
                                ('TARIFF','CODE_AMENDMENT','SANCTION','EMERGENCY','MARKET_FREEZE','INFO')),
            severity          TEXT NOT NULL DEFAULT 'INFO' CHECK
                                (severity IN ('INFO','NOTICE','WARN','CRITICAL')),
            summary           TEXT NOT NULL,
            affected_entities JSONB NOT NULL DEFAULT '[]'::jsonb,
            affected_tenants  UUID[] NOT NULL DEFAULT '{}'::uuid[],
            source_url        TEXT,
            full_text         TEXT
        );
        CREATE INDEX ix_regulator_events_issued
            ON regulatory.regulator_events (issued_at DESC);
        CREATE INDEX ix_regulator_events_affected_entities
            ON regulatory.regulator_events USING GIN (affected_entities);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS regulatory.regulator_events CASCADE")
    op.execute(
        "ALTER TABLE IF EXISTS regulatory.settlement_statements "
        "DROP CONSTRAINT IF EXISTS fk_settlement_signed_doc"
    )
    op.execute("DROP TABLE IF EXISTS regulatory.signed_documents CASCADE")
    op.execute("DROP TABLE IF EXISTS regulatory.settlement_statement_lines CASCADE")
    op.execute("DROP TABLE IF EXISTS regulatory.settlement_statements CASCADE")
    op.execute("DROP TABLE IF EXISTS regulatory.forecast_submissions CASCADE")
