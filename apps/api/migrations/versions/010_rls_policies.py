"""010 RLS policies

Revision ID: 010_rls
Revises: 009_audit
Create Date: 2026-05-23

Per ARCHITECTURE.md §3.9. Every tenant-scoped table gets:
  - ENABLE ROW LEVEL SECURITY
  - tenant_isolation_select policy: USING (tenant_id = app.tenant_id)
  - tenant_isolation_modify policy: ALL with same predicate + WITH CHECK
  - tenant_isolation_admin_bypass policy: SELECT when app.is_admin = 'true'

Special cases:
  - regulatory.regulator_events — read-all / write-admin (cross-tenant)
  - audit.events — tenant_id is nullable; system events visible to all

NOTE on owner bypass: by default the table owner bypasses RLS. Because we
run migrations as the bootstrap `gecko` superuser (which also owns these
tables), `gecko` will bypass RLS. The `gecko_api` role (`NOBYPASSRLS`,
created in 002) is what the app uses, and RLS will apply to it. Tests use
either `gecko_api` or set `ROW LEVEL SECURITY FORCE`.

To make RLS apply EVEN to table owners (so the smoke test from a superuser
session works), we use `ALTER TABLE ... FORCE ROW LEVEL SECURITY`.
"""
from __future__ import annotations

from alembic import op

revision: str = "010_rls"
down_revision: str | None = "009_audit"
branch_labels = None
depends_on = None


# Tables with a `tenant_id` column → standard isolation policy.
TENANT_TABLES = [
    "core.tenants",  # tenant_id is `id` here; we treat id as tenant_id below
    "core.users",
    "core.assets",
    "market.rdn_prices",
    "market.vdr_trades",
    "market.br_settlements",
    "market.dd_contracts",
    "market.dd_contract_hourly_volume",
    "market.bids",
    "market.ancillary_offers",
    "market.ancillary_activations",
    "dispatch.setpoints",
    "dispatch.telemetry",
    "dispatch.instructions",
    "dispatch.instruction_acks",
    "dispatch.operator_adjustments",
    "ems.forecasts",
    "ems.forecast_actuals",
    "ems.kpi_daily",
    "ems.optimisation_runs",
    "regulatory.forecast_submissions",
    "regulatory.settlement_statements",
    "regulatory.settlement_statement_lines",
    "regulatory.signed_documents",
    "agents.query_log",
]


def upgrade() -> None:
    # core.tenants uses `id` as the tenant key; handle separately.
    op.execute("ALTER TABLE core.tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE core.tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_select ON core.tenants FOR SELECT
            USING (id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
                   OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation_modify ON core.tenants FOR ALL
            USING (id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )

    # Standard tenant_id-based policies for the rest.
    for t in TENANT_TABLES[1:]:  # skip core.tenants — handled above
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_select ON {t} FOR SELECT
                USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_modify ON {t} FOR ALL
                USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
                WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_admin_bypass ON {t} FOR SELECT
                USING (current_setting('app.is_admin', true) = 'true')
            """
        )

    # regulatory.regulator_events — cross-tenant readable, admin-only writes.
    op.execute("ALTER TABLE regulatory.regulator_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE regulatory.regulator_events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY regevent_read_all ON regulatory.regulator_events
            FOR SELECT USING (TRUE)
        """
    )
    op.execute(
        """
        CREATE POLICY regevent_write_admin ON regulatory.regulator_events FOR ALL
            USING (current_setting('app.is_admin', true) = 'true')
            WITH CHECK (current_setting('app.is_admin', true) = 'true')
        """
    )

    # audit.events — tenant_id is nullable (system events); allow read of
    # NULL tenant rows from every session.
    op.execute("ALTER TABLE audit.events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit.events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_select ON audit.events FOR SELECT
            USING (tenant_id IS NULL
                   OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
                   OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation_modify ON audit.events FOR ALL
            USING (tenant_id IS NULL
                   OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id IS NULL
                        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    for t in TENANT_TABLES + ["regulatory.regulator_events", "audit.events"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_select ON {t}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_modify ON {t}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_admin_bypass ON {t}")
        op.execute(f"DROP POLICY IF EXISTS regevent_read_all ON {t}")
        op.execute(f"DROP POLICY IF EXISTS regevent_write_admin ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY")
