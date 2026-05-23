# BACKEND_DB_INSTRUCTIONS — GECKO VPP v2

**Owner:** DB sub-lead (Stage-3 specialist; executes Phase 4.1 + 4.2 of `ARCHITECTURE.md §12`).
**Parent contracts:** `ARCHITECTURE.md` §3 (data model — full DDL, verbatim), §3.11 (synth generator), §10.5 (data coverage tests), §11 FMEA rows F06/F07/F15/F16, §14.1 (this lead's checklist).
**Audience:** the implementing coding agent. Read this file end-to-end before touching code; once read, all SQL, migration order, RLS shape, and synth-coverage tactics live here without needing to re-open `ARCHITECTURE.md`.
**Length:** ~6 pages.

---

## 1. Goal

Stand up the entire Postgres 16 layer of GECKO VPP v2: **7 schemas, 27 tables, BRIN/btree indexes, monthly RANGE partition on `dispatch.telemetry`, RLS policies on every domain table, 2 roles (`gecko_api` `NOBYPASSRLS` + `gecko_migrate` `BYPASSRLS`), one materialised view (`ems.kpi_portfolio_30d`)**, and a one-shot `apps/synth/` Python container that populates the DB with exactly **30 days (2026-04-23 … 2026-05-23 inclusive)** of synthetic Ukrainian-energy data that passes every coverage assertion in §3.11.5. Re-running `docker compose run --rm synth` must produce byte-identical data (RNG seed = `20260523`).

This DB is the substrate for everything else; until it is green, Backend API (Phase 4.3+) and Frontend (4.4+) cannot make progress.

---

## 2. Success criteria (binary checklist — every line green before declaring done)

- [ ] `alembic upgrade head` against a fresh `gecko` database succeeds without manual intervention.
- [ ] All **7 schemas exist:** `core`, `market`, `dispatch`, `ems`, `regulatory`, `agents`, `audit`.
- [ ] All **27 tables exist**, columns and types verbatim per `ARCHITECTURE.md §3` (no edits — the architect locked them).
- [ ] `dispatch.telemetry` is partitioned by `RANGE (interval_start)` with **two partitions live**: `telemetry_2026_04` and `telemetry_2026_05`.
- [ ] `ems.kpi_portfolio_30d` materialised view exists; refreshed once by synth at seed time.
- [ ] RLS is **ENABLE**d on every table listed in `ARCHITECTURE.md §3.9`; standard policy `tenant_isolation_select` + `tenant_isolation_modify` attached to each (except `regulatory.regulator_events` which uses `regevent_read_all` + `regevent_write_admin`).
- [ ] `gecko_api` role has `NOBYPASSRLS`; integration test proves connection A with `app.tenant_id=<X>` cannot see connection B's rows where `tenant_id=<Y>`.
- [ ] `core.tenants` contains **exactly 3 rows** with fixed UUIDs from `synth.yaml` (one per segment: `producer-1`, `ci-1`, `storage-1`).
- [ ] `core.eic_codes` lookup seeded with ≥25 rows (Y/X/W/V types per §3.2.3).
- [ ] `docker compose run --rm synth` populates DB and writes `phase-3-architecture/synth_coverage.md` with **`✅` on every acceptance criterion** listed in §3.11.2.
- [ ] `apps/synth/synth/sniff_test.py` passes every invariant in §3.11.5 (cap-pinning consistency, SoC bounds, EIC regex, VAT arithmetic, etc.).
- [ ] Re-running synth produces **byte-identical row counts and primary-key sets** (determinism contract §3.11.4).
- [ ] CI gate `synth sniff_test` (`ARCHITECTURE.md §10.7`) wired into `.github/workflows/ci.yml` and blocks merge on failure.
- [ ] Pre-flight check (§9 below) answers YES on all 4 questions before code starts.

---

## 3. Tools (verify available before starting)

| Tool | Purpose | Pin / version | Verify |
|---|---|---|---|
| Postgres 16 | DB engine | image `postgres:16-alpine` in `infra/docker/docker-compose.yml` | `docker run --rm postgres:16-alpine psql --version` |
| Python | runtime | **3.12** (matches `.python-version` in repo root per `ARCHITECTURE.md §2`) | `python --version` |
| `uv` | Python package + workspace manager | latest stable | `uv --version` |
| SQLAlchemy 2.0 (async) | declarative_base + naming convention + metadata | `>=2.0,<2.1` | declared in `apps/api/pyproject.toml` |
| `asyncpg` | async driver used by FastAPI; `gecko_migrate` connection uses sync driver for alembic | `>=0.29` | same |
| `alembic` | migrations | `>=1.13` | `uv run alembic --version` |
| `psycopg[binary]` | sync driver for alembic env (asyncpg has no sync mode) | `>=3.1` | same |
| `pytest` + `pytest-asyncio` + `testcontainers[postgres]` | integration tests for RLS isolation | latest stable | `uv run pytest --version` |
| Docker + Docker Compose v2 | local Postgres for dev; one-shot synth container | host install | `docker compose version` |
| `ruff` + `mypy` | lint/type (CI gates per §10.7) | latest | `uv run ruff --version` |

**Package manager pick:** `uv` over `poetry`. Justification: ARCHITECTURE.md §2 declares uv at workspace root (`pyproject.toml`); Zhytomyr's reference project also moved off poetry; uv resolves ~10× faster, fewer foot-guns with lockfile drift across `apps/api/` + `apps/synth/` workspaces. If `uv` is somehow not available on the implementer's machine, see Branching protocol (§10).

---

## 4. Step-by-step plan (execute in order — each step blocks the next)

### Phase A — Project skeleton (DB layer scope of `apps/api/` + `apps/synth/`)

**Step 1. Bootstrap `apps/api/` Python project.**
- Create `apps/api/pyproject.toml` declaring `[project]` name `gecko-api`, Python `>=3.12`, dependencies `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `psycopg[binary]`, `alembic`, `pydantic-settings`, `pydantic>=2.7`.
- Add `apps/api/app/__init__.py` (empty), `apps/api/app/settings.py` (Pydantic Settings reading `DATABASE_URL`, `DATABASE_URL_SYNC`, etc.).
- Add `apps/api/app/db.py` containing the async engine factory + `get_db_conn` dependency stub (Backend API lead fills it later; for DB phase the file just needs `Base = declarative_base(metadata=metadata)` with naming convention — see Step 2).
- Verify: `cd apps/api && uv sync && uv run python -c "import app"` succeeds.

**Step 2. SQLAlchemy 2.0 declarative_base + naming convention.**
- In `apps/api/app/db.py` declare:
  ```python
  NAMING_CONVENTION = {
      "ix": "ix_%(column_0_label)s",
      "uq": "uq_%(table_name)s_%(column_0_name)s",
      "ck": "ck_%(table_name)s_%(constraint_name)s",
      "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
      "pk": "pk_%(table_name)s",
  }
  metadata = MetaData(naming_convention=NAMING_CONVENTION)
  class Base(DeclarativeBase):
      metadata = metadata
  ```
- This guarantees deterministic constraint names → reproducible migrations.

**Step 3. Alembic init wired to read `DATABASE_URL` from env.**
- `cd apps/api && uv run alembic init -t async alembic` (creates `apps/api/alembic/` with async template).
- Edit `apps/api/alembic/env.py`:
  - Read `DATABASE_URL_SYNC` (sync driver — `postgresql+psycopg://gecko_migrate:...`) via `os.environ` rather than `alembic.ini`.
  - `target_metadata = app.db.metadata`.
  - Use the **sync engine** for migrations (alembic + async is more trouble than worth here; Zhytomyr precedent confirms sync alembic works fine even when app is async).
- Set `version_locations` and `script_location` per default; commit the `versions/` folder empty.
- Verify: `uv run alembic current` returns nothing (empty DB) without error.

### Phase B — Migrations (one file per logical unit; numbered to match `ARCHITECTURE.md §2` repo layout)

Each migration is **idempotent on `op.execute("CREATE ... IF NOT EXISTS")` only where safe**; otherwise use plain `op.create_table`. Use `op.execute(sa.text("..."))` to insert verbatim DDL from `ARCHITECTURE.md §3` (the architect locked the SQL; do NOT translate it into SQLAlchemy column constructors — drift risk).

**Migration 001 — `001_init_schemas.py`.** Create the 7 schemas:
```sql
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS dispatch;
CREATE SCHEMA IF NOT EXISTS ems;
CREATE SCHEMA IF NOT EXISTS regulatory;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS audit;
```
Downgrade: `DROP SCHEMA ... CASCADE` in reverse order.

**Migration 002 — `002_roles_and_grants.py`.** Create the 3 roles (`gecko_api LOGIN NOBYPASSRLS`, `gecko_migrate LOGIN BYPASSRLS`, `gecko_readonly LOGIN`). GRANT USAGE on schemas to `gecko_api`. Grants on tables are issued in migration 011 after all tables exist (otherwise `GRANT ALL TABLES IN SCHEMA` runs against an empty schema and grants nothing). Source passwords from env (`POSTGRES_GECKO_API_PASSWORD`, etc.); never inline.

**Migration 003 — `003_core_tables.py`.** Tables from `ARCHITECTURE.md §3.2`: `core.tenants`, `core.users`, `core.eic_codes`, `core.assets`. Verbatim DDL (the comment-placeholder line in `core.tenants` — strip the placeholder, keep all other columns). Include all indexes shown in §3.2.

**Migration 004 — `004_market_tables.py`.** Tables from §3.3: `market.rdn_prices`, `market.vdr_trades`, `market.br_settlements`, `market.dd_contracts`, `market.dd_contract_hourly_volume`, `market.bids`, `market.ancillary_offers`, `market.ancillary_activations`. Each `interval_start` column is `GENERATED ALWAYS AS (...) STORED` — DO NOT manually compute; the architect spec demands DB-generated.

**Migration 005 — `005_dispatch_tables.py`.** Tables from §3.4: `dispatch.setpoints`, `dispatch.telemetry` (PARTITION BY RANGE — see special note below), `dispatch.instructions`, `dispatch.instruction_acks`, `dispatch.operator_adjustments`.

**Telemetry partitioning — critical detail (F16 in FMEA).** Architect's DDL: `dispatch.telemetry` is the parent partitioned table. Migration must create:
1. The parent table with `PARTITION BY RANGE (interval_start)` and `PRIMARY KEY (tenant_id, asset_id, interval_start)`.
2. Two child partitions in the **same migration** (do NOT defer to a separate migration — if synth runs before partitions exist, INSERTs fail per F16):
   - `telemetry_2026_04` FOR VALUES FROM `('2026-04-01')` TO `('2026-05-01')`
   - `telemetry_2026_05` FOR VALUES FROM `('2026-05-01')` TO `('2026-06-01')`
3. **`interval_start` is a regular `TIMESTAMPTZ NOT NULL`**, NOT a GENERATED column on the telemetry table — Postgres does not allow GENERATED on partition keys. Synth must compute it explicitly.

**Migration 006 — `006_ems_tables.py`.** Tables from §3.5: `ems.forecasts`, `ems.forecast_actuals`, `ems.kpi_daily`, `ems.optimisation_runs`. The materialised view `ems.kpi_portfolio_30d` is created here as well (it depends only on `ems.kpi_daily`).

**Migration 007 — `007_regulatory_tables.py`.** Tables from §3.6: `regulatory.forecast_submissions`, `regulatory.settlement_statements`, `regulatory.settlement_statement_lines`, `regulatory.signed_documents`, `regulatory.regulator_events`. **Order matters:** create `settlement_statements` with `signed_doc_id BIGINT` (no FK yet) → create `signed_documents` → `ALTER TABLE settlement_statements ADD CONSTRAINT fk_signed_doc FOREIGN KEY ...` (architect's spec at §3.6.3).

**Migration 008 — `008_agents_tables.py`.** Tables from §3.7: `agents.query_log`, `agents.response_cache`.

**Migration 009 — `009_audit_tables.py`.** Tables from §3.8: `audit.events`.

**Migration 010 — `010_rls_policies.py`.** Per §3.9. For each table that has `tenant_id`:
```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_select ON <t> FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_modify ON <t> FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_admin_bypass ON <t> FOR SELECT
    USING (current_setting('app.is_admin', true) = 'true');
```
For `regulatory.regulator_events` use the **read-all / admin-write** variant in §3.9. `audit.events` allows nullable `tenant_id` (system events); policy must `USING (tenant_id IS NULL OR tenant_id = current_setting('app.tenant_id', true)::uuid)` for SELECT — clarification not explicit in §3.9, lock here.

**Migration 011 — `011_indexes_and_grants.py`.**
- BRIN index on `dispatch.telemetry (interval_start)` (huge partitioned table → BRIN beats btree on this column when seq-scan friendly): `CREATE INDEX ON dispatch.telemetry USING BRIN (interval_start);` — **see Branching protocol** if BRIN fails on a generated column (it should not, since telemetry's `interval_start` is not generated here).
- btree composite indexes per §3 (every table's `CREATE INDEX ...` clauses).
- GIN on `regulatory.regulator_events (affected_entities)` (§3.6.4) and `agents.query_log` if needed (architect didn't specify, leave off unless query plan demands).
- Now `GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA core,market,dispatch,ems,regulatory,agents,audit TO gecko_api;` plus sequences (§3.10).

**Migration 012 — `012_seed_core_lookups.py`.** Seed fixed-UUID rows:
- `core.tenants` — exactly 3 rows, UUIDs hard-coded so synth can reference them. Suggested UUIDs (write to `synth.yaml`):
  - `producer-1` → `11111111-1111-4111-8111-111111111111`
  - `ci-1`       → `22222222-2222-4222-8222-222222222222`
  - `storage-1`  → `33333333-3333-4333-8333-333333333333`
- `core.eic_codes` — ~25 rows: 2 BZN (Y), 3 participants (X), 10–12 W-prefix resources (one per planned asset), 8–10 V-prefix metering points. EIC strings must match the regex `^10[YXWVTZ][A-Z0-9-]{12}[A-Z0-9]$` (sniff-test enforces).

**Migration order is total.** Do NOT reorder; F16 depends on telemetry parent-then-partitions before any synth INSERT.

### Phase C — Synthetic data generator (`apps/synth/`)

**Step 4. Skeleton.** Layout (per `ARCHITECTURE.md §2`):
```
apps/synth/
├── synth/
│   ├── __main__.py        # entrypoint: python -m synth
│   ├── config.py          # loads synth.yaml via pydantic-settings + yaml
│   ├── rng.py             # seeded Random() factory; one instance per generator
│   ├── tenants.py         # writes core.tenants (idempotent UPSERT on fixed UUIDs)
│   ├── assets.py          # writes core.assets + assigns EIC codes
│   ├── market.py          # rdn_prices, vdr_trades, br_settlements, dd_contracts, bids, ancillary
│   ├── telemetry.py       # dispatch.telemetry + setpoints + instructions + acks
│   ├── forecasts.py       # ems.forecasts (primary + refined) + forecast_actuals + kpi_daily
│   ├── regulatory.py      # forecast_submissions, settlement_statements + lines, signed_documents, regulator_events
│   ├── agents_warmup.py   # agents.query_log seed (~30 sample queries for visual richness)
│   ├── coverage.py        # writes synth_coverage.md
│   └── sniff_test.py      # CI-blocking invariant assertions
├── synth.yaml             # config; committed
├── pyproject.toml
└── Dockerfile
```

**Step 5. `synth.yaml` contract.** Architect locked the keys in §3.11.1. Implementer fills exact values:
```yaml
rng_seed: 20260523
window_start: 2026-04-23
window_end:   2026-05-23
tenants:
  - { code: producer-1, segment: producer, uuid: '11111111-1111-4111-8111-111111111111',
      display_name: 'ТОВ "Поляна Енерджі"', region: 'Закарпатська', edrpou: '12345601',
      participant_eic: '10X-UA-PROD-001', asset_mix: { СЕС: 3, ВЕС: 1, УЗЕ: 1, ГПУ: 1 } }
  - { code: ci-1, segment: c-i, uuid: '22222222-2222-4222-8222-222222222222',
      display_name: 'ПАТ "Дніпровий Завод"', region: 'Дніпропетровська', edrpou: '12345602',
      participant_eic: '10X-UA-C-I-001', asset_mix: { СЕС: 1, АктСпож: 1, УЗЕ: 1, Споживач: 1 } }
  - { code: storage-1, segment: storage, uuid: '33333333-3333-4333-8333-333333333333',
      display_name: 'ТОВ "Запоріжжя Сторідж"', region: 'Запорізька', edrpou: '12345603',
      participant_eic: '10X-UA-STOR-001', asset_mix: { УЗЕ: 2, СЕС: 1 } }
market:
  rdn_cap_uah_mwh: { default: 6300, peak: 6900, off_peak: 5600 }
  cap_pinning_probability: 0.40
  cap_pinning_hours: [17, 18, 19, 20, 21]
  vdr_trades_per_day: 30
  br_imbalance_sigma: 0.05
events:
  res_curtailments: 6
  planned_maintenance: 2
  regulator_notices: 10
  forecast_submissions_per_day: 1
```
EIC suffixes are stub strings (NOT real ENTSO-E issued codes); they must satisfy the 16-char regex. Trailing dashes are fine; the sniff regex `^10[YXWVTZ][A-Z0-9-]{12}[A-Z0-9]$` permits them.

**Step 6. Generator semantics per table.** All distributions seeded; cite shape from research files:

| Table | Target row count | Shape rules |
|---|---|---|
| `core.tenants` | 3 | Fixed-UUID UPSERT from `synth.yaml`. |
| `core.eic_codes` | ~25 | 2 BZN (Y), 3 participants (X), one W per planned asset, one V per metering point. |
| `core.assets` | 24–36 (per-tenant asset_mix) | Ukrainian display names from a fixture list (`Поляна СЕС`, `Кагарлицька ВЕС`, `Запорізька ГПУ-1`, `Дніпровська УЗЕ`); capacities 1–20 МВт per `BRIEF §4`; СЕС/ВЕС CFs from `research_asset_data_shape.md §1–2`. |
| `core.users` | 6 | 2 per tenant (one `operator`, one `manager`). |
| `market.rdn_prices` | **2,160** (= 3 tenants × 30 days × 24 hours) | Double-peak curve (`research_market_data_shape.md §1`): trough 03:00–05:00 ~1,500–2,500 UAH/MWh; morning peak 08:00–10:00; deep evening peak 17:00–21:00; daily index base 3,500–6,500. **Cap-pinning:** on `cap_pinning_probability` (40%) of days, evening-peak hours (`cap_pinning_hours`) clamp to `cap_uah_mwh` and set `is_capped=TRUE`. Negative-price day: one day around 2026-05-04 midday hits ≤ 0 UAH/MWh for 2–3 hours (HLA D10 §3.11.3 event 8). |
| `market.vdr_trades` | ~2,700 | 30 trades/day × 30 days × 3 tenants; price ±10–20% of РДН clearing per `§2`; sides BUY/SELL roughly balanced; counterparty codes `CP-001…CP-040`. |
| `market.br_settlements` | **2,160** | Asymmetric prices (`§3`): system-short = РДН × 1.2–2.5; system-long = РДН × 0.4–0.8. `our_imbalance_mwh` ~ N(0, σ=`br_imbalance_sigma` × portfolio_nameplate). Signed `settlement_uah`. |
| `market.dd_contracts` | ~15 (3–6 per tenant) | Profile mix: BASE 8, PEAK 4, OFFPEAK 2, INDIVIDUAL 1. Start/end dates span the window. Some indexed (`price_formula='РДН base + 5%'`). |
| `market.dd_contract_hourly_volume` | ~10,800 | For each contract × 30 days × 24 hours. BASE = constant; PEAK = hours 08–22 only on weekdays; OFFPEAK = hours 23–07; INDIVIDUAL = 24-element array drawn from a flexible-customer profile. |
| `market.bids` | ~6,480 | 3 tenants × 3 markets (RDN/VDR/BR) × 24 hours × 30 days. State distribution: 70% ACCEPTED, 15% PARTIAL, 10% ACTIVE, 5% REJECTED. SELL bids dominate for producer-1, BUY for ci-1, mixed for storage-1. |
| `market.ancillary_offers` | ~2,880 | 2 storage assets × 24 h × 30 days × 2 services (`FCR`, `aFRR_up`). Capacity prices in EUR/MW·h indexed (`§6`, 1 МВт BESS ≈ €100k/yr → roughly 0.4–1.5 €/MW·h). |
| `market.ancillary_activations` | a few hundred | Event-level: `aFRR` activations 5–20/day per BESS, 30 sec – 5 min duration each. |
| `dispatch.setpoints` | ~7,000 | ~8 setpoints/day × 30 assets × 30 days. Reasons: `arbitrage`, `aFRR-up`, `curtailment`, `manual`. UZE setpoints carry `target_soc_pct`. |
| `dispatch.telemetry` | ~21,600 | Hourly across all assets × 30 days × 24 h. SoC curves for УЗЕ follow `research_asset_data_shape.md §4`: 02:00–05:00 charge 15→90%, 17:00–21:00 discharge 90→15%. `availability_pct=100` except planned-maintenance windows. `status='curtailed_by_TSO'` during injected curtailment events. |
| `dispatch.instructions` | ~5,000 | 1 per setpoint typically; payload `JSONB` carries `{target_mw, ramp_seconds}`. |
| `dispatch.instruction_acks` | ~4,800 | Most `ack`, ~4% `timeout` to simulate realism. |
| `dispatch.operator_adjustments` | ~50 | One per asset on ~2 days; `reason` includes `planned_maintenance`, `derate`. |
| `ems.forecasts` | ~86,000 | Per architect estimate. For each (asset, day, hour): 2 types (`primary`, `refined`) × ~2 kinds (`solar`/`wind`/`load` depending on asset class + `price` for everyone). Primary error σ ~10–15%; refined ~5–8% (`research_asset_data_shape.md §6`). |
| `ems.forecast_actuals` | ~43,000 | One per (asset, day, hour) for the kind that asset actually produces; derived from telemetry. |
| `ems.kpi_daily` | ~900 | One per asset per day. `co2_avoided_tn` computed as `RES_energy_mwh × 0.45 tn/MWh` (UA grid factor). |
| `ems.kpi_portfolio_30d` | 3 (one per tenant) | Materialised view; refreshed once at end of synth. |
| `ems.optimisation_runs` | ~30 | Pre-seed ~30 sample runs across the 30-day window; later FastAPI optimiser endpoint writes additional rows live. |
| `regulatory.forecast_submissions` | ~60–90 | 1/day for producer-1 (A01), 1/day for ci-1 (A04), monthly for storage-1. Status distribution: 90% `ACK`, 10% `SUBMITTED` (auto-flips). |
| `regulatory.settlement_statements` | ~12 | Apr 2026 + May 2026 statements per tenant × counterparty (ГП for producer, electricity supplier for c-i). |
| `regulatory.settlement_statement_lines` | ~60 | 5 lines per statement avg. |
| `regulatory.signed_documents` | ~30 | One per `SETTLEMENT_ACT` statement, plus one per signed `FORECAST_PACKAGE`, plus 5 `REPORT` signatures. `is_demo_stub=TRUE` always. `document_hash_sha256` = REAL `hashlib.sha256(canonical_json)`. `p7s_blob` = 64 RNG bytes. ACSK pool: `Дія`, `ПриватБанк`, `ІДД ДПС`, `Ключові системи`. Signer name pool: 8 Ukrainian-fixture names. |
| `regulatory.regulator_events` | 8–12 | 2 TARIFF, 3 INFO, 2 NOTICE, 2 WARN, 1 CRITICAL spread across window. `affected_tenants` array empty (= all) for system-wide; specific UUIDs for targeted notices. |
| `agents.query_log` | ~30 | Pre-seed sample queries (one per intent × persona combination from `ARCHITECTURE.md §7.2`) for visual demo on `/admin/analyze`. |
| `audit.events` | ~50 | `system` events at seed time (`event_type='synth.seed_complete'`, etc.). |

**Determinism contract (§3.11.4).** Every random call routes through a single `rng.RNG` factory seeded from `synth.yaml rng_seed`. NO calls to `random.random()` or `numpy.random.rand()` without going through the factory. Sniff-test verifies determinism by hashing a canonical row export and asserting it stable across runs.

**Step 7. Coverage report (`coverage.py`).** Walks the §11 acceptance criteria; for each, executes a count SQL and writes:
```
§11.4   surfaces (producer)            ✅ assets=8, telemetry=21,600
§11.11  ENTSO-E EIC codes              ✅ eic_codes=25 (Y/X/W/V types covered)
...
```
If ANY line is `❌`, exit non-zero → CI deploy gate fails.

**Step 8. Sniff-test (`sniff_test.py`).** Asserts (per §3.11.5):
1. Every РДН row with `hour BETWEEN 17 AND 21` AND `is_capped=TRUE` → `price_uah_mwh = cap_uah_mwh`.
2. Every `dispatch.telemetry` row with non-null `soc_pct` → `soc_pct BETWEEN 10 AND 90`.
3. Every EIC in `core.eic_codes.eic` matches regex `^10[YXWVTZ][A-Z0-9-]{12}[A-Z0-9]$`.
4. For every `regulatory.settlement_statements`: `ABS(amount_gross_uah - amount_net_uah * (1 + vat_rate)) < 0.01`.
5. Coverage report has no `❌`.
6. `gecko_api` connection cannot see another tenant's `core.assets` (mini-RLS smoke).
7. **Determinism:** SHA-256 of `(SELECT * FROM market.rdn_prices ORDER BY id)` after seed-1 == after seed-2 on a fresh DB.

Fail any assert → exit 1 → CI blocks.

**Step 9. Dockerfile + compose.** `apps/synth/Dockerfile` is a thin Python 3.12 image copying source + `uv sync --no-dev`. `infra/docker/docker-compose.yml` has `synth` service with `restart: no` and `depends_on: postgres` (healthy). Seed command: `docker compose run --rm synth python -m synth`.

### Phase D — Verification

**Step 10. Local end-to-end test.**
1. `docker compose up -d postgres` (wait healthy).
2. `docker compose run --rm api alembic upgrade head` (or `uv run alembic upgrade head` with `DATABASE_URL_SYNC` set).
3. `docker compose run --rm synth python -m synth`.
4. `cat phase-3-architecture/synth_coverage.md` — all `✅`.
5. `docker compose run --rm synth python -m synth.sniff_test` exit 0.
6. RLS integration test (`apps/api/tests/integration/test_rls_isolation.py`): two asyncpg connections with different `app.tenant_id` see disjoint row sets on `core.assets`, `market.rdn_prices`, `dispatch.telemetry`.
7. Re-run step 3; sniff-test step 7 (determinism hash) passes.

---

## 5. Reusable patterns from Zhytomyr (peek, don't copy blindly)

Path: `D:\ВС коде вайбкодинг\Житомир погодинка\`. Useful references:
- `db/schema.sql` — proves the `(date DATE, hour SMALLINT 1..24)` convention works in production; column types and CHECK constraints follow the same shape we use here.
- `db/migrations/v05..v17.sql` — migration cadence example (one logical change per file).
- `db/migrations/v11_snapshot_rls_policies.sql` — example RLS policy syntax in a UA-deployed project.
- `db/migrations/v17_operator_adjustment_reason.sql` — the `operator_adjustments` table pattern we mirror in `dispatch.operator_adjustments`.

**DO NOT copy:** Zhytomyr uses **raw `psycopg3`** with no ORM. GECKO uses **SQLAlchemy 2.0 async + asyncpg** per `ARCHITECTURE.md §6.2` lock. Don't drift.

---

## 6. Conventions (non-negotiable; cite ARCHITECTURE.md)

- Time keying: every domain row carries `(date DATE, hour SMALLINT 1..24)` + GENERATED `interval_start TIMESTAMPTZ` (except `dispatch.telemetry` where `interval_start` is plain `NOT NULL` because partition keys can't be GENERATED). Cite `ARCHITECTURE.md §3` + HLA D1.
- All EIC fields are `CHAR(16)` matching the §3.11.5 regex.
- Monetary fields are `NUMERIC(_, 2)` for whole UAH amounts, `NUMERIC(_, 4)` for prices that need higher precision (EUR ancillary). NEVER `FLOAT` / `DOUBLE`.
- Every domain table carries `tenant_id UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE`, EXCEPT `regulatory.regulator_events` (cross-tenant by design).
- Schema namespacing: tables ALWAYS qualified (`market.rdn_prices`, not `rdn_prices`). HLA D12.
- DST: 2026-03-29 (spring forward) is **before** our window; 2026-10-25 (fall back) is **after**. No DST hours inside the 30-day window — generator can treat `Europe/Kyiv` as a steady +03:00 offset throughout. Document this assumption in `apps/synth/README.md`.

---

## 7. §11 acceptance criteria this file's domain services (BRIEF)

Cross-check each before declaring done; cite `PRODUCT_BRIEF.md §11.x`:

- **§11.2** — 3 demo tenants seeded (Migration 012).
- **§11.4** — telemetry + KPI + assets + market data exist for all 9 producer surfaces.
- **§11.10** — Postgres persists data across `docker compose restart`; synth is one-shot (Migration 012 idempotent UPSERT; later synth runs TRUNCATE+reseed).
- **§11.11** — ENTSO-E EIC codes embedded everywhere; `core.eic_codes` lookup populated.
- **§11.12** — Ukrainian asset names, грн prices, EET timestamps, 1–20 МВт capacities, ~50 МВт total.
- **§11.13** — Sub-1-hour data swap: documented SQL INSERT path via `core.assets` + RLS (HLA §11.13 path).
- **§11.19** — `regulatory.forecast_submissions` populated with at least one ACK per tenant per day where applicable.
- **§11.20** — `regulatory.signed_documents` ≥12 rows with `is_demo_stub=TRUE`.
- **§11.21** — `rdn_prices` + `vdr_trades` + `br_settlements` + `dd_contracts` all present (single-pane data source).
- **§11.22** — `ems.kpi_daily.co2_avoided_tn` > 0 for every RES asset.
- **§11.27** (POLISH) — at least one curtailment day (May 12) and one imbalance spike day (May 4) seeded.

---

## 8. FMEA rows this file mitigates (cite `ARCHITECTURE.md §11`)

- **F06 (RLS missing on a new table).** Mitigation: integration test `test_rls_isolation` runs against every domain table dynamically (introspect `pg_tables WHERE schemaname IN (...) AND rowsecurity = false` → expect empty set EXCEPT `regulator_events` which has its own policy).
- **F07 (Synth non-determinism).** Mitigation: single RNG factory + sniff-test determinism hash.
- **F15 (Coverage `❌`).** Mitigation: `coverage.py` + CI gate.
- **F16 (Telemetry partition missing on seed).** Mitigation: Migration 005 creates partitions in the same transaction as the parent table.

---

## 9. Pre-flight check (NON-NEGOTIABLE — answer YES before starting)

Before writing any migration, the implementer must explicitly answer:

- [ ] **(a) Goal clear?** "Build 7 schemas + 27 tables + RLS + synth that satisfies the coverage report — yes/no."
- [ ] **(b) Success criteria measurable?** "Every line in §2 of this file is binary checkable — yes/no."
- [ ] **(c) Tools available?** "Postgres 16 image pulls; `uv` installed; alembic + asyncpg + sqlalchemy 2.0 resolve in `apps/api/pyproject.toml`; docker compose runs — yes/no."
- [ ] **(d) Plan complete?** "I can produce the entire DB layer by following Phase A → D mechanically with no architectural decisions left to make — yes/no."

If any answer is NO → STOP. Write a `phase-3-architecture/BACKEND_DB_CHECKLIST.md` addendum listing the gap and what unblocks it; ping the orchestrator. Do not paper over a NO.

---

## 10. Branching protocol (when the main path breaks)

Per the user's emphasis on autonomous flow: if a step fails, do NOT halt the project. Instead:

1. **Log to `difficulties_log.md`** using the template (path: `gecko-vpp-rebuild/difficulties_log.md`).
2. **Switch to the documented fallback** (see table below).
3. **Return to the main path** as soon as feasible; document `Returned to main path: yes/no, when`.

| Branch point | Fallback |
|---|---|
| `uv` not available | Use `pip install -e .` + `pip-tools` for lockfile. Document mismatch in the log. |
| Async alembic env errors | Switch to **sync alembic** with `psycopg` driver (Zhytomyr precedent). The app stays async; only migrations are sync. This is already the recommended path in Step 3. |
| BRIN index on a generated column fails | `interval_start` on telemetry is NOT generated (partition-key constraint). If BRIN fails for any other reason → drop to **btree on `(interval_start)`**. Document and continue. |
| `CREATE POLICY ... USING (current_setting('app.tenant_id', true)::uuid)` errors on Postgres 16 quirk | Replace `current_setting(_, true)` (missing_ok=true) with `NULLIF(current_setting('app.tenant_id'), '')::uuid` plus a default-empty session var. |
| `core.tenants` row UUID conflicts with an existing row | Use UPSERT (`ON CONFLICT (code) DO UPDATE`) in Migration 012 instead of plain INSERT. |
| Synth runs out of memory on full seed | Stream INSERTs via `executemany()` in batches of 1,000 rather than building a 100k-row Python list. |
| Coverage `❌` on a specific §11.x criterion | Tune `synth.yaml` event-injection counts, re-seed, re-verify. Document the tuning. |
| Materialised view refresh fails (locks) | Use `REFRESH MATERIALIZED VIEW CONCURRENTLY` if a unique index exists on the MV; otherwise plain refresh inside synth's final commit. |

---

## 11. Done definition

The DB phase is DONE iff:

1. All boxes in §2 (Success criteria) are checked.
2. CI gates `synth sniff_test`, `pytest integration` (specifically `test_rls_isolation`), `alembic upgrade head` all green on PR.
3. `synth_coverage.md` committed and shows `✅` on every line.
4. PR opened against `main` titled `feat(db): full schema + RLS + synth seed (Phase 4.1+4.2)`.
5. Append a one-line report to `PROGRESS.md` "Stage transitions log":
   ```
   - YYYY-MM-DD — Phase 4.1+4.2 (DB lead) DONE. 27 tables; RLS green; synth produces 30-day coverage ✅; sniff-test green. [one-line note about any gotcha hit]
   ```
6. Any branch taken during execution is logged to `difficulties_log.md`.

When done, hand off to Backend API lead (`BACKEND_API_INSTRUCTIONS.md`) — they unblock on a green DB phase.

---

*End of BACKEND_DB_INSTRUCTIONS v0.1.*
