# ARCHITECTURE — GECKO VPP v2

**Status:** v0.1 · Stage 2 (Senior Detailed Architect) · 2026-05-23
**Parent:** `PRODUCT_BRIEF.md` v0.4 (frozen 2026-05-23) + `HIGH_LEVEL_ARCHITECTURE.md` v0.1 (Stage 1, locked decisions)
**Audience:** 8 specialist leads (DB, Backend, Frontend, AI agents, Voice agent, SDK, Security, Testing, DevOps) and the implementing agents that follow them.
**Length:** ~38 pages markdown (~3,800 lines)

This is the single document that Phase 4 (Implementation) is written from. It must be precise enough that writing the code is mechanical.

---

## 0. Document conventions

### 0.1 What this document is

- **The detailed technical contract** between Stage 1 (topology) and Stage 3 (specialist instructions).
- **DDL-level** for the data model — copy/pasteable SQL with concrete column types, defaults, indexes, and RLS policies.
- **Path-level** for the API — exact route strings, request/response shapes, status codes, error envelopes.
- **Component-level** for the frontend — concrete React component names, props at the seam, design-token contract.
- **Module-level** for the backend — Python package layout, the import-linter contract, dependency injection seams.

### 0.2 What this document is NOT

- Not implementation code. Each `CREATE TABLE` and each Pydantic schema is a contract; the code goes in Phase 4.
- Not a re-litigation of Stage 1. Where Stage 1 locked a decision (§9.1 of `HIGH_LEVEL_ARCHITECTURE.md`), this doc extends it.
- Not a sales narrative. PRODUCT_BRIEF v0.4 owns the "why".

### 0.3 How to cite

Anywhere in subsequent specialist instructions, cite this doc as `ARCHITECTURE.md §<N>.<sub>` (e.g., `§3.2.4` for the `core.tenants` DDL). Cite the brief as `BRIEF §11.x`. Cite Stage 1 as `HLA §<N>`.

### 0.4 Status of every locked decision from Stage 1

All 15 lock items from `HIGH_LEVEL_ARCHITECTURE.md §9.1` are honoured. The 20 delegated questions from `HLA §9.2` are answered below or explicitly forwarded to a specialist lead in §14.

### 0.5 Vocabulary

| Term | Meaning |
|---|---|
| MTU | Market Time Unit. UA = 60 min. |
| BRP | Сторона, відповідальна за баланс (Balance Responsible Party). |
| BSP | Постачальник послуг балансування (Balancing Service Provider). |
| EIC | Energy Identification Code (ENTSO-E, 16 chars). |
| BZN | Bidding Zone EIC (Y-prefix). UA BZN = `10Y1001C--00003F`. |
| СОП | Системний оператор передачі (НЕК "Укренерго"). |
| ОРЕЕ | Оператор ринку електричної енергії (ДП "Оператор ринку"). |
| ГП | ДП "Гарантований Покупець". |
| КЕП | Кваліфікований електронний підпис. Stub only in v2. |
| RLS | Postgres Row-Level Security. |
| MV | Materialised View (preaggregated cache). |

### 0.6 Version line

- **v0.1 — 2026-05-23** — initial detailed architecture written by Stage 2 senior architect.

---

## 1. System overview

### 1.1 The one paragraph

GECKO VPP v2 is a **two-deployment** demo: a Next.js 16 frontend on Vercel (`gecko.radai-1984.dev`) and a single FastAPI process plus Postgres 16 on the existing Hetzner VPS (`api.gecko.radai-1984.dev`, both behind Caddy). The frontend never touches the DB directly — its `/api/*` route handlers act as thin proxies that inject `X-Tenant-Id` from a session cookie and forward to FastAPI. The backend is **one process, six Python modules** (`core`, `market`, `dispatch`, `ems`, `regulatory`, `agents`), each owning a Postgres schema. Multi-tenancy is enforced by RLS, not application code. Data is **30 days of synthetic** records (2026-04-23 … 2026-05-23) seeded once via a one-shot Python container — restarting the app never re-seeds. Justification for every topology pick lives in `HIGH_LEVEL_ARCHITECTURE.md §4`.

### 1.2 The one diagram

```
                          gecko.radai-1984.dev (Vercel)
                          ┌────────────────────────────────┐
                          │  Next.js 16 App Router         │
                          │  - server components by default│
                          │  - /api/* route handlers proxy │
                          │    to api.gecko.radai-1984.dev │
                          │  - design tokens via CSS vars  │
                          │  - light primary, dark toggle  │
                          └──────────────┬─────────────────┘
                                         │  HTTPS + X-Tenant-Id header
                                         ▼
                          api.gecko.radai-1984.dev (Hetzner VPS)
                          ┌────────────────────────────────┐
                          │  Caddy (existing, shared TLS)  │
                          └──────────────┬─────────────────┘
                                         │  internal Docker network
                                         ▼
                          ┌────────────────────────────────┐
                          │  FastAPI app (one process)     │
                          │   /core   /market   /dispatch  │
                          │   /ems    /regulatory  /agents │
                          │  + OpenAPI 3.1 at /openapi.json│
                          └──────────────┬─────────────────┘
                                         │  asyncpg + SET LOCAL app.tenant_id
                                         ▼
                          ┌────────────────────────────────┐
                          │  Postgres 16 (Docker)          │
                          │  schemas: core, market,        │
                          │   dispatch, ems, regulatory,   │
                          │   agents, audit                │
                          │  RLS on every domain table     │
                          │  monthly RANGE partition on    │
                          │   dispatch.telemetry           │
                          └────────────────────────────────┘
```

### 1.3 Trust boundaries (extended from HLA §2.2)

| Boundary | Authentication mechanism | Threat model in scope for v2 |
|---|---|---|
| Browser ↔ Vercel | none (mock auth) | only "tenant-switcher must not silently leak" |
| Vercel ↔ FastAPI | `X-Tenant-Id` header injected server-side | header tampering blocked by Caddy allowlist (§9) |
| FastAPI ↔ Postgres | DB role `gecko_api` with limited GRANTs | RLS enforces tenant_id (§3.9) |
| Public ↔ `/developer/*` | none | OpenAPI is read-only; no mutation possible without `X-Tenant-Id` |
| Public ↔ `/admin/*` | mock header `X-Admin: true` | the demo intentionally exposes this; documented in `/about/credentials` |

---

## 2. Repository layout

Monorepo, single package manager root: `pnpm` for the JS workspaces, `uv` for the Python workspaces. All paths below are relative to `gecko-vpp-rebuild/`.

```
gecko-vpp-rebuild/
├── PRODUCT_BRIEF.md                       # v0.4, frozen
├── PROGRESS.md
├── difficulties_log.md
├── pnpm-workspace.yaml                    # JS workspace root
├── pyproject.toml                         # uv workspace root (Python)
├── package.json                           # workspace meta + lint scripts
├── tsconfig.base.json
├── .nvmrc                                 # 20.x
├── .python-version                        # 3.12
├── .gitignore
├── .env.example                           # all keys, safe defaults
├── README.md                              # public; explains the demo
├── LICENSE                                # MIT
├── apps/
│   ├── web/                               # Next.js 16 frontend
│   │   ├── app/
│   │   │   ├── layout.tsx                 # AppShell, theme bootstrap
│   │   │   ├── page.tsx                   # / — hero, persona picker, slide-7 diagram
│   │   │   ├── globals.css                # design tokens (CSS vars)
│   │   │   ├── producer/
│   │   │   │   ├── page.tsx               # Результати (KPI tiles)
│   │   │   │   ├── aktyvy/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [id]/page.tsx
│   │   │   │   ├── prognozy/page.tsx
│   │   │   │   ├── dyspetcheryzatsiya/page.tsx
│   │   │   │   ├── rynok/page.tsx
│   │   │   │   ├── uze/page.tsx
│   │   │   │   ├── spovishchennya/page.tsx
│   │   │   │   ├── zvity/page.tsx
│   │   │   │   └── nalashtuvannya/page.tsx
│   │   │   ├── c-i/                       # mirror of producer; 5 of 9 surfaces (§5.3.4)
│   │   │   │   ├── page.tsx
│   │   │   │   ├── aktyvy/page.tsx
│   │   │   │   ├── prognozy/page.tsx
│   │   │   │   ├── rynok/page.tsx
│   │   │   │   └── zvity/page.tsx
│   │   │   ├── storage/                   # mirror of producer; 5 of 9 surfaces
│   │   │   │   ├── page.tsx
│   │   │   │   ├── aktyvy/page.tsx
│   │   │   │   ├── uze/page.tsx
│   │   │   │   ├── rynok/page.tsx
│   │   │   │   └── zvity/page.tsx
│   │   │   ├── developer/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── api/explorer/page.tsx  # Scalar embed
│   │   │   │   ├── sdk-ts/page.tsx
│   │   │   │   ├── sdk-py/page.tsx
│   │   │   │   ├── webhooks/page.tsx
│   │   │   │   └── auth/page.tsx
│   │   │   ├── admin/
│   │   │   │   ├── engage/page.tsx
│   │   │   │   ├── operate/page.tsx
│   │   │   │   └── analyze/page.tsx
│   │   │   ├── about/credentials/page.tsx # stub disclosure list
│   │   │   └── api/                       # Next.js route handlers (proxies)
│   │   │       ├── auth/
│   │   │       │   ├── me/route.ts
│   │   │       │   └── switch-tenant/route.ts
│   │   │       └── [...path]/route.ts     # catch-all proxy to FastAPI
│   │   ├── components/
│   │   │   ├── shell/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   ├── TopBar.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── TenantSwitcher.tsx
│   │   │   │   ├── PersonaSwitcher.tsx
│   │   │   │   ├── ThemeToggle.tsx
│   │   │   │   ├── AgentLauncher.tsx
│   │   │   │   └── VoiceButton.tsx
│   │   │   ├── hero/
│   │   │   │   ├── PersonaPicker.tsx
│   │   │   │   └── ArchitectureDiagram.tsx
│   │   │   ├── kpi/
│   │   │   │   ├── KPITile.tsx
│   │   │   │   └── KPIGrid.tsx
│   │   │   ├── assets/
│   │   │   │   ├── AssetCard.tsx
│   │   │   │   ├── AssetTable.tsx
│   │   │   │   └── AssetDrawer.tsx
│   │   │   ├── charts/
│   │   │   │   ├── HourlyChart.tsx        # Recharts wrapper
│   │   │   │   ├── BatterySoCArc.tsx
│   │   │   │   ├── ForecastChart.tsx
│   │   │   │   └── PriceCapOverlay.tsx
│   │   │   ├── dispatch/
│   │   │   │   ├── DispatchQueue.tsx
│   │   │   │   └── InstructionRow.tsx
│   │   │   ├── market/
│   │   │   │   ├── MarketBidForm.tsx
│   │   │   │   ├── BidHistory.tsx
│   │   │   │   └── RevenueSplit.tsx
│   │   │   ├── reports/
│   │   │   │   ├── ReportCard.tsx
│   │   │   │   └── KEPSignBadge.tsx
│   │   │   ├── scenarios/
│   │   │   │   └── ScenarioCard.tsx
│   │   │   ├── palette/
│   │   │   │   └── CommandPalette.tsx
│   │   │   ├── agent/
│   │   │   │   ├── AgentChat.tsx
│   │   │   │   └── VoiceSession.tsx
│   │   │   └── dev/
│   │   │       └── OpenAPIExplorer.tsx    # Scalar wrapper
│   │   ├── lib/
│   │   │   ├── api-client.ts              # TanStack Query hooks
│   │   │   ├── tenant.ts
│   │   │   ├── theme.ts
│   │   │   ├── i18n.ts                    # JSON dict
│   │   │   ├── format-uah.ts
│   │   │   └── feature-flags.ts
│   │   ├── stores/                        # Zustand
│   │   │   ├── theme-store.ts
│   │   │   ├── tenant-store.ts
│   │   │   └── palette-store.ts
│   │   ├── styles/
│   │   │   └── tokens.css                 # CSS variable definitions
│   │   ├── tests/
│   │   │   ├── smoke.spec.ts              # Playwright smoke
│   │   │   └── unit/
│   │   ├── public/
│   │   │   ├── manifest.webmanifest       # PWA
│   │   │   └── icons/
│   │   ├── next.config.mjs
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.mjs
│   │   ├── tsconfig.json
│   │   └── package.json
│   ├── api/                               # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py                    # FastAPI() instance, router include
│   │   │   ├── settings.py                # Pydantic Settings (env)
│   │   │   ├── db.py                      # asyncpg pool + RLS dependency
│   │   │   ├── core/                      # tenant, auth, eic codes
│   │   │   │   ├── __init__.py
│   │   │   │   ├── public.py              # exported contracts (Tenant, EICCode)
│   │   │   │   ├── routers/
│   │   │   │   │   └── auth.py
│   │   │   │   ├── services/
│   │   │   │   ├── repositories/
│   │   │   │   └── schemas/
│   │   │   ├── market/                    # Ринкова інтеграція
│   │   │   │   ├── public.py
│   │   │   │   ├── routers/
│   │   │   │   │   ├── rdn.py
│   │   │   │   │   ├── vdr.py
│   │   │   │   │   ├── br.py
│   │   │   │   │   ├── dd.py
│   │   │   │   │   ├── bids.py
│   │   │   │   │   └── revenue.py
│   │   │   │   ├── services/
│   │   │   │   ├── repositories/
│   │   │   │   └── schemas/
│   │   │   ├── dispatch/                  # Диспетчеризація
│   │   │   │   ├── public.py
│   │   │   │   ├── routers/
│   │   │   │   ├── services/
│   │   │   │   └── schemas/
│   │   │   ├── ems/                       # forecast / optimiser / KPI
│   │   │   │   ├── public.py
│   │   │   │   ├── forecast/
│   │   │   │   ├── optimiser/
│   │   │   │   ├── kpi/
│   │   │   │   ├── routers/
│   │   │   │   └── schemas/
│   │   │   ├── regulatory/
│   │   │   │   ├── public.py
│   │   │   │   ├── routers/
│   │   │   │   │   ├── settlements.py
│   │   │   │   │   ├── documents.py       # КЕП stub
│   │   │   │   │   └── events.py
│   │   │   │   ├── services/
│   │   │   │   └── schemas/
│   │   │   ├── agents/
│   │   │   │   ├── public.py
│   │   │   │   ├── classifier.py
│   │   │   │   ├── intents/
│   │   │   │   ├── personas/
│   │   │   │   ├── templates/
│   │   │   │   ├── routers/
│   │   │   │   │   ├── text.py
│   │   │   │   │   └── voice.py
│   │   │   │   └── schemas/
│   │   │   └── audit/
│   │   │       ├── public.py
│   │   │       └── service.py
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       ├── 001_init_schemas.py
│   │   │       ├── 002_core_tables.py
│   │   │       ├── 003_market_tables.py
│   │   │       ├── 004_dispatch_tables.py
│   │   │       ├── 005_ems_tables.py
│   │   │       ├── 006_regulatory_tables.py
│   │   │       ├── 007_agents_tables.py
│   │   │       ├── 008_audit_tables.py
│   │   │       ├── 009_rls_policies.py
│   │   │       ├── 010_materialised_views.py
│   │   │       └── 011_partitions.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   ├── importlinter.cfg               # cross-module import contract
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── synth/                             # data generator (one-shot container)
│       ├── synth/
│       │   ├── __main__.py
│       │   ├── config.py                  # reads synth.yaml
│       │   ├── rng.py                     # seeded RNG
│       │   ├── tenants.py
│       │   ├── assets.py
│       │   ├── market.py
│       │   ├── telemetry.py
│       │   ├── forecasts.py
│       │   ├── regulatory.py
│       │   ├── agents_warmup.py
│       │   ├── coverage.py                # writes synth_coverage.md
│       │   └── sniff_test.py              # CI-blocking invariant checks
│       ├── synth.yaml                     # config: tenant list, RNG seed, events
│       ├── pyproject.toml
│       └── Dockerfile
├── packages/
│   ├── sdk-ts/                            # @gecko-vpp/sdk
│   │   ├── src/
│   │   │   ├── client.ts                  # GeckoVPPClient class
│   │   │   ├── generated/                 # from openapi-typescript
│   │   │   └── examples/
│   │   ├── tsup.config.ts                 # ESM + CJS dual
│   │   ├── package.json
│   │   └── README.md
│   ├── sdk-py/                            # gecko-vpp on PyPI
│   │   ├── gecko_vpp/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── generated/                 # from openapi-python-client
│   │   │   └── examples/
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── openapi/
│       └── openapi.json                   # committed snapshot, regenerated in CI
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   └── docker-compose.dev.yml
│   ├── caddy/
│   │   └── gecko-api.caddy                # snippet for shared Caddyfile
│   └── postgres/
│       └── init/                          # DB role + schema creation bootstrap
│           └── 00_roles.sql
└── phase-3-architecture/
    ├── HIGH_LEVEL_ARCHITECTURE.md         # Stage 1 output
    ├── ARCHITECTURE.md                    # THIS FILE
    ├── research_market_data_shape.md
    ├── research_asset_data_shape.md
    ├── research_regulatory_data_shape.md
    └── (specialist *_INSTRUCTIONS.md files appear in Stage 3)
```

---

## 3. Data model

The most critical section. Every domain table is specified with full DDL, indexes, RLS, expected row counts for the 30-day demo, and the §11.x criteria it services.

### 3.1 Postgres top-level schemas

Created in migration `001_init_schemas.py`:

```sql
CREATE SCHEMA IF NOT EXISTS core;        -- tenants, users (mock), eic_codes lookup
CREATE SCHEMA IF NOT EXISTS market;      -- РДН / ВДР / БР / ДД / ancillary / bids
CREATE SCHEMA IF NOT EXISTS dispatch;    -- setpoints, telemetry (partitioned), instructions
CREATE SCHEMA IF NOT EXISTS ems;         -- forecasts, KPI daily, optimisation runs
CREATE SCHEMA IF NOT EXISTS regulatory;  -- forecast_submissions, settlements, КЕП, regulator events
CREATE SCHEMA IF NOT EXISTS agents;      -- agent_query_log, agent_response_cache
CREATE SCHEMA IF NOT EXISTS audit;       -- events (user actions, system emissions)
```

Database name: `gecko`. App role: `gecko_api` (used by FastAPI; non-superuser; bypassing RLS forbidden). Migration role: `gecko_migrate` (used by alembic; can bypass RLS).

### 3.2 `core` schema

#### 3.2.1 `core.tenants`

Services BRIEF §11.2 (3 demo customers).

```sql
CREATE TABLE core.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT NOT NULL UNIQUE,        -- 'producer-1', 'ci-1', 'storage-1'
    display_name    TEXT NOT NULL,               -- 'ТОВ "Поляна Енерджі"'
    segment         TEXT NOT NULL CHECK (segment IN ('producer','c-i','storage')),
    edrpou          CHAR(8) NOT NULL,            -- 8-digit Ukrainian legal entity code
    participant_eic CHAR(16) NOT NULL,           -- X-prefix EIC
    bzn_eic         CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    region          TEXT,                        -- 'Закарпатська'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_demo         BOOLEAN NOT NULL DEFAULT TRUE,
    COMMENT_PLACEHOLDER TEXT
);
COMMENT ON TABLE core.tenants IS 'Mock multi-tenancy: 3 demo customers, one per segment A/B/C (BRIEF §3, §11.2)';
CREATE UNIQUE INDEX ON core.tenants (participant_eic);
```

**Rows for 30-day demo:** 3 (one per segment).

#### 3.2.2 `core.users` (mock)

Services BRIEF §11.2 (no real auth, but a "trusted-person invite" stub on §11.29 POLISH).

```sql
CREATE TABLE core.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('operator','manager','admin','viewer')),
    invited_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    accepted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX ON core.users (tenant_id, email);
```

**Rows:** 3 tenants × 2 users = 6.

#### 3.2.3 `core.eic_codes` — lookup table

Services BRIEF §11.11 (ENTSO-E EIC codes in data model).

```sql
CREATE TABLE core.eic_codes (
    eic         CHAR(16) PRIMARY KEY,
    code_type   CHAR(1) NOT NULL CHECK (code_type IN ('Y','X','W','V','T','Z')),
    -- Y area, X party, W resource, V metering point, T tie-line, Z location
    display_name TEXT NOT NULL,
    issuer      TEXT,                            -- e.g. '10X-UA-NEC-001A' issuer
    valid_from  DATE,
    valid_to    DATE,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb
);
COMMENT ON COLUMN core.eic_codes.code_type IS
  'ENTSO-E EIC position-3 classifier — see research_regulatory_data_shape.md §6';
```

Seed rows include:
- `10Y1001C--00003F` (Y, UA single BZN post-2022)
- `10YUA-WEPS-----0` (Y, UA-BEI historical)
- 3 × X-prefix participant EICs (one per tenant)
- 8–12 × W-prefix resource EICs (one per asset, see §3.2.4)
- ~10 V-prefix metering point EICs

**Rows:** ~25.

#### 3.2.4 `core.assets`

Services BRIEF §11.4, §11.11, §11.12. The fleet table.

```sql
CREATE TABLE core.assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    code                TEXT NOT NULL,           -- 'POLYANA-SES-01'
    display_name        TEXT NOT NULL,           -- 'Поляна СЕС'
    asset_class         TEXT NOT NULL CHECK (asset_class IN
                          ('СЕС','ВЕС','ГПУ','УЗЕ','АктСпож','Споживач')),
    technology_type     CHAR(3) NOT NULL,        -- ENTSO-E PsrType: B16 solar, B19 wind, B04 gas,...
    resource_eic        CHAR(16) NOT NULL REFERENCES core.eic_codes(eic),
    metering_eic        CHAR(16) REFERENCES core.eic_codes(eic),
    capacity_mw         NUMERIC(8,3) NOT NULL CHECK (capacity_mw > 0),
    storage_capacity_mwh NUMERIC(8,3),           -- only for УЗЕ; NULL otherwise
    region              TEXT NOT NULL,           -- 'Закарпатська'
    commissioned_on     DATE NOT NULL,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','maintenance','decommissioned')),
    bzn_eic             CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);
CREATE INDEX ON core.assets (tenant_id, asset_class);
CREATE INDEX ON core.assets (resource_eic);
COMMENT ON TABLE core.assets IS 'Asset registry. Total portfolio ≈ 50 МВт across 8–12 assets (BRIEF §4).';
```

**Rows for 30-day demo:** 8–12 per tenant × 3 tenants = **24–36 total** (configured in `synth.yaml`).

Recommended mix per tenant (from `research_market_data_shape.md §7`):
- producer-1: 3× СЕС, 1× ВЕС, 1× УЗЕ, 1× ГПУ — 6 assets, ~30 МВт.
- ci-1: 1× СЕС (rooftop), 1× АктСпож, 1× УЗЕ, 1× Споживач — 4 assets, ~12 МВт.
- storage-1: 2× УЗЕ, 1× СЕС (hybrid) — 3 assets, ~10 МВт.

### 3.3 `market` schema

#### 3.3.1 `market.rdn_prices` — Day-Ahead Market price index

Services BRIEF §11.21 (single pane over РДН/ВДР/БР/ДД).

```sql
CREATE TABLE market.rdn_prices (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    bidding_zone_eic CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start  TIMESTAMPTZ GENERATED ALWAYS AS
                      ((date + ((hour - 1) || ' hour')::INTERVAL) AT TIME ZONE 'Europe/Kyiv')
                      STORED,
    price_uah_mwh   NUMERIC(10,2) NOT NULL,
    volume_mwh      NUMERIC(12,3) NOT NULL,
    is_capped       BOOLEAN NOT NULL DEFAULT FALSE,    -- TRUE when price = hourly cap
    cap_uah_mwh     NUMERIC(10,2),                     -- the cap that hour (NULL if irrelevant)
    daily_index_base NUMERIC(10,2),                    -- derived per-day base index
    daily_index_peak NUMERIC(10,2),
    daily_index_offpeak NUMERIC(10,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, bidding_zone_eic, date, hour)
);
CREATE INDEX ON market.rdn_prices (tenant_id, date);
CREATE INDEX ON market.rdn_prices (interval_start);
COMMENT ON TABLE market.rdn_prices IS
  'РДН hourly prices. Cap-pinning modelled per HLA D4. UA convention hour 1..24.';
```

**Rows:** 3 tenants × 30 days × 24 hours = **2,160 rows**.

#### 3.3.2 `market.vdr_trades` — Intraday Market trades

Services BRIEF §11.21.

```sql
CREATE TABLE market.vdr_trades (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    trade_id            TEXT NOT NULL,                  -- mRID
    executed_at         TIMESTAMPTZ NOT NULL,
    delivery_date       DATE NOT NULL,
    delivery_hour       SMALLINT NOT NULL CHECK (delivery_hour BETWEEN 1 AND 24),
    interval_start      TIMESTAMPTZ GENERATED ALWAYS AS
                          ((delivery_date + ((delivery_hour - 1) || ' hour')::INTERVAL)
                          AT TIME ZONE 'Europe/Kyiv') STORED,
    volume_mwh          NUMERIC(10,3) NOT NULL,
    price_uah_mwh       NUMERIC(10,2) NOT NULL,
    side                TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    counterparty_code   TEXT NOT NULL,                  -- anonymised, e.g. 'CP-014'
    resource_eic        CHAR(16),
    bidding_zone_eic    CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    UNIQUE (tenant_id, trade_id)
);
CREATE INDEX ON market.vdr_trades (tenant_id, delivery_date, delivery_hour);
CREATE INDEX ON market.vdr_trades (resource_eic, interval_start);
```

**Rows:** 3 tenants × ~30 trades/day × 30 days = **~2,700**.

#### 3.3.3 `market.br_settlements` — Balancing Market hourly settlement

Services BRIEF §11.21.

```sql
CREATE TABLE market.br_settlements (
    id                          BIGSERIAL PRIMARY KEY,
    tenant_id                   UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    date                        DATE NOT NULL,
    hour                        SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start              TIMESTAMPTZ GENERATED ALWAYS AS
                                  ((date + ((hour - 1) || ' hour')::INTERVAL)
                                  AT TIME ZONE 'Europe/Kyiv') STORED,
    price_short_uah_mwh         NUMERIC(10,2) NOT NULL,   -- system-short price
    price_long_uah_mwh          NUMERIC(10,2) NOT NULL,   -- system-long price
    system_direction            TEXT NOT NULL CHECK
                                  (system_direction IN ('SHORT','LONG','BALANCED')),
    our_imbalance_mwh           NUMERIC(10,3) NOT NULL,   -- signed
    settlement_uah              NUMERIC(14,2) NOT NULL,   -- signed; revenue or penalty
    bidding_zone_eic            CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    UNIQUE (tenant_id, date, hour)
);
CREATE INDEX ON market.br_settlements (tenant_id, date);
CREATE INDEX ON market.br_settlements (interval_start);
```

**Rows:** 3 × 30 × 24 = **2,160**.

#### 3.3.4 `market.dd_contracts` and `market.dd_contract_hourly_volume`

Services BRIEF §11.21 (ДД in single pane).

```sql
CREATE TABLE market.dd_contracts (
    id                      BIGSERIAL PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    contract_no             TEXT NOT NULL,
    counterparty_name       TEXT NOT NULL,
    counterparty_edrpou     CHAR(8),
    profile_type            TEXT NOT NULL CHECK
                              (profile_type IN ('BASE','PEAK','OFFPEAK','INDIVIDUAL')),
    start_date              DATE NOT NULL,
    end_date                DATE NOT NULL,
    price_uah_mwh           NUMERIC(10,2),       -- NULL when indexed
    price_formula           TEXT,                -- 'РДН base + 5%' if indexed
    total_volume_mwh        NUMERIC(14,3),       -- derived sum, denormalised
    bidding_zone_eic        CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    status                  TEXT NOT NULL DEFAULT 'ACTIVE'
                              CHECK (status IN ('DRAFT','ACTIVE','CLOSED')),
    UNIQUE (tenant_id, contract_no)
);

CREATE TABLE market.dd_contract_hourly_volume (
    contract_id     BIGINT NOT NULL REFERENCES market.dd_contracts(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL,                          -- denormalised for RLS
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start  TIMESTAMPTZ GENERATED ALWAYS AS
                      ((date + ((hour - 1) || ' hour')::INTERVAL)
                      AT TIME ZONE 'Europe/Kyiv') STORED,
    volume_mwh      NUMERIC(10,3) NOT NULL,
    PRIMARY KEY (contract_id, date, hour)
);
CREATE INDEX ON market.dd_contract_hourly_volume (tenant_id, date);
```

**Rows:** 3–6 contracts per tenant × 3 tenants ≈ **15 contracts**; hourly volume ≈ 15 × 30 × 24 = **10,800**.

#### 3.3.5 `market.bids` — bid history (РДН / ВДР / БР / ДД-quote)

Services BRIEF §11.21. Adapted from `research_regulatory_data_shape.md §9.2`.

```sql
CREATE TABLE market.bids (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    bid_id              TEXT NOT NULL,
    market              TEXT NOT NULL CHECK (market IN ('RDN','VDR','BR','DD')),
    delivery_date       DATE NOT NULL,
    hour                SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start      TIMESTAMPTZ GENERATED ALWAYS AS
                          ((delivery_date + ((hour - 1) || ' hour')::INTERVAL)
                          AT TIME ZONE 'Europe/Kyiv') STORED,
    side                TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    bid_type            TEXT NOT NULL CHECK
                          (bid_type IN ('SIMPLE','BLOCK','STEP','LIMIT','IOC','FOK')),
    block_id            UUID,
    volume_mwh          NUMERIC(10,3) NOT NULL,
    price_uah_mwh       NUMERIC(10,2) NOT NULL,
    technology_type     CHAR(3),                      -- ENTSO-E PsrType
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
CREATE INDEX ON market.bids (tenant_id, market, delivery_date, hour);
CREATE INDEX ON market.bids (resource_eic, interval_start);
```

**Rows:** 3 tenants × 3 markets × 24 hours × 30 days ≈ **6,480**, plus a few hundred stub-submitted-during-demo bids.

#### 3.3.6 `market.ancillary_offers` and `market.ancillary_activations`

Services BRIEF §11.4 (УЗЕ revenue stacking).

```sql
CREATE TABLE market.ancillary_offers (
    id                      BIGSERIAL PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    asset_id                UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
    date                    DATE NOT NULL,
    hour                    SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start          TIMESTAMPTZ GENERATED ALWAYS AS
                              ((date + ((hour - 1) || ' hour')::INTERVAL)
                              AT TIME ZONE 'Europe/Kyiv') STORED,
    service                 TEXT NOT NULL CHECK
                              (service IN ('FCR','aFRR_up','aFRR_down','mFRR_up','mFRR_down','RR')),
    offered_capacity_mw     NUMERIC(8,3) NOT NULL,
    cleared_capacity_mw     NUMERIC(8,3) NOT NULL DEFAULT 0,
    capacity_price_eur_mwh  NUMERIC(10,4) NOT NULL,
    revenue_capacity_uah    NUMERIC(14,2) NOT NULL DEFAULT 0,
    UNIQUE (tenant_id, asset_id, date, hour, service)
);

CREATE TABLE market.ancillary_activations (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
    service             TEXT NOT NULL CHECK
                          (service IN ('FCR','aFRR_up','aFRR_down','mFRR_up','mFRR_down','RR')),
    started_at          TIMESTAMPTZ NOT NULL,
    ended_at            TIMESTAMPTZ NOT NULL,
    avg_power_mw        NUMERIC(8,3) NOT NULL,
    energy_mwh          NUMERIC(10,4) NOT NULL,
    energy_price_uah_mwh NUMERIC(10,2) NOT NULL,
    revenue_energy_uah  NUMERIC(14,2) NOT NULL
);
CREATE INDEX ON market.ancillary_activations (tenant_id, asset_id, started_at DESC);
```

**Rows:** offers ≈ 2 storage assets × 24 h × 30 days × ~2 services = **~2,880**; activations ≈ a few hundred.

### 3.4 `dispatch` schema

#### 3.4.1 `dispatch.setpoints`

```sql
CREATE TABLE dispatch.setpoints (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_from      TIMESTAMPTZ NOT NULL,
    effective_to        TIMESTAMPTZ NOT NULL,
    target_power_mw     NUMERIC(8,3) NOT NULL,
    target_soc_pct      NUMERIC(5,2),                  -- УЗЕ only
    reason              TEXT NOT NULL,                 -- 'arbitrage','aFRR-up','curtailment','manual'
    issued_by           TEXT NOT NULL,                 -- 'optimiser','operator','tso'
    state               TEXT NOT NULL DEFAULT 'pending'
                          CHECK (state IN ('pending','acknowledged','executing','done','cancelled','failed'))
);
CREATE INDEX ON dispatch.setpoints (tenant_id, asset_id, effective_from DESC);
```

**Rows:** ≈ asset × 8 setpoints/day × 30 days ≈ **~7,000**.

#### 3.4.2 `dispatch.telemetry` — partitioned by month

Services BRIEF §11.4 (Диспетчеризація surface), §11.25 (production-fidelity feel).

```sql
CREATE TABLE dispatch.telemetry (
    tenant_id           UUID NOT NULL,
    asset_id            UUID NOT NULL,
    date                DATE NOT NULL,
    hour                SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start      TIMESTAMPTZ NOT NULL,            -- materialised (not GENERATED, partition key)
    active_power_mw     NUMERIC(8,3) NOT NULL,           -- + = inject, − = consume
    reactive_power_mvar NUMERIC(8,3),
    soc_pct             NUMERIC(5,2),                    -- УЗЕ only
    availability_pct    NUMERIC(5,2) NOT NULL DEFAULT 100,
    status              TEXT NOT NULL DEFAULT 'online'
                          CHECK (status IN
                            ('online','idle','maintenance','starting','stopping',
                             'tripped','curtailed_by_TSO','unavailable')),
    data_quality        CHAR(1) NOT NULL DEFAULT 'R'
                          CHECK (data_quality IN ('R','V','E','S')),
    source              TEXT NOT NULL DEFAULT 'synthetic',
    extras              JSONB NOT NULL DEFAULT '{}'::jsonb,
                        -- {irradiance_w_m2, module_temp_c, wind_speed_m_s, wind_direction_deg,
                        --  fuel_flow_nm3_h, cumulative_cycles, capacity_fade_pct, ...}
    PRIMARY KEY (tenant_id, asset_id, interval_start)
) PARTITION BY RANGE (interval_start);

-- Partitions for 30-day window
CREATE TABLE dispatch.telemetry_2026_04 PARTITION OF dispatch.telemetry
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE dispatch.telemetry_2026_05 PARTITION OF dispatch.telemetry
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX ON dispatch.telemetry (tenant_id, date, hour);
CREATE INDEX ON dispatch.telemetry (asset_id, interval_start DESC);
```

**Rows:** ~30 assets total × 24 h × 30 days ≈ **~21,600** — trivial. Hourly granularity per HLA D14.

#### 3.4.3 `dispatch.instructions` and `dispatch.instruction_acks`

```sql
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
    priority        SMALLINT NOT NULL DEFAULT 5  -- 1=highest, 9=lowest
);
CREATE INDEX ON dispatch.instructions (tenant_id, queued_at DESC);

CREATE TABLE dispatch.instruction_acks (
    instruction_id  BIGINT PRIMARY KEY REFERENCES dispatch.instructions(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL,
    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ack_status      TEXT NOT NULL CHECK (ack_status IN ('ack','nack','timeout')),
    ack_payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes           TEXT
);
```

**Rows:** ≈ 5,000 instructions, ≈ 4,800 acks (some timeouts injected for realism).

#### 3.4.4 `dispatch.operator_adjustments`

Mirrors Zhytomyr's `operator_adjustments` table (`research_asset_data_shape.md §B.5`).

```sql
CREATE TABLE dispatch.operator_adjustments (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    asset_id        UUID NOT NULL REFERENCES core.assets(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    operator_mw     NUMERIC(8,3) NOT NULL,                -- the override value
    reason          TEXT NOT NULL,
    operator_user_id UUID REFERENCES core.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, asset_id, date, hour)
);
```

**Rows:** ~50.

### 3.5 `ems` schema

#### 3.5.1 `ems.forecasts` and `ems.forecast_actuals`

Services BRIEF §11.4, §11.19. Adopts Zhytomyr two-stage (primary + refined) pattern per HLA D13.

```sql
CREATE TABLE ems.forecasts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    asset_id        UUID REFERENCES core.assets(id) ON DELETE CASCADE,
    forecast_kind   TEXT NOT NULL CHECK
                      (forecast_kind IN ('solar','wind','load','price','consumption')),
    forecast_type   TEXT NOT NULL CHECK (forecast_type IN ('primary','refined')),
    issued_at       TIMESTAMPTZ NOT NULL,
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start  TIMESTAMPTZ GENERATED ALWAYS AS
                      ((date + ((hour - 1) || ' hour')::INTERVAL)
                      AT TIME ZONE 'Europe/Kyiv') STORED,
    value_mwh       NUMERIC(10,4) NOT NULL,
    model_id        TEXT NOT NULL DEFAULT 'synth-v1',
    confidence_lo   NUMERIC(10,4),                       -- p10
    confidence_hi   NUMERIC(10,4),                       -- p90
    UNIQUE (tenant_id, asset_id, forecast_kind, forecast_type, date, hour)
);
CREATE INDEX ON ems.forecasts (tenant_id, forecast_kind, date);

CREATE TABLE ems.forecast_actuals (
    tenant_id       UUID NOT NULL,
    asset_id        UUID NOT NULL,
    forecast_kind   TEXT NOT NULL,
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 1 AND 24),
    interval_start  TIMESTAMPTZ GENERATED ALWAYS AS
                      ((date + ((hour - 1) || ' hour')::INTERVAL)
                      AT TIME ZONE 'Europe/Kyiv') STORED,
    actual_mwh      NUMERIC(10,4) NOT NULL,
    PRIMARY KEY (tenant_id, asset_id, forecast_kind, date, hour)
);
```

**Rows:** forecasts ≈ ~30 assets × 24 h × 30 days × 2 types × ~2 kinds = **~86,000**; actuals ≈ half that.

#### 3.5.2 `ems.kpi_daily` and `ems.kpi_portfolio_30d` (materialised view)

Services BRIEF §11.22 (CO₂ avoided KPI), §11.27 scenario inputs.

```sql
CREATE TABLE ems.kpi_daily (
    tenant_id           UUID NOT NULL,
    asset_id            UUID NOT NULL,
    date                DATE NOT NULL,
    grn_saved_uah       NUMERIC(14,2) NOT NULL DEFAULT 0,
    grn_earned_uah      NUMERIC(14,2) NOT NULL DEFAULT 0,
    imbalance_mwh       NUMERIC(10,4) NOT NULL DEFAULT 0,
    co2_avoided_tn      NUMERIC(10,3) NOT NULL DEFAULT 0,
    availability_pct    NUMERIC(5,2) NOT NULL DEFAULT 100,
    opportunity_score   SMALLINT NOT NULL DEFAULT 0
                          CHECK (opportunity_score BETWEEN 0 AND 100),
    notes               TEXT,
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
```

Refresh: at synth-seed time only (per `HLA R1` mitigation — no runtime refresh).

**Rows:** kpi_daily ≈ 30 assets × 30 days = **~900**; portfolio MV = 3.

#### 3.5.3 `ems.optimisation_runs`

Services BRIEF §11.14 (optimiser as separate service).

```sql
CREATE TABLE ems.optimisation_runs (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    requested_by        UUID REFERENCES core.users(id),
    requested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    scenario            TEXT NOT NULL,
                        -- 'arbitrage','curtailment_hedge','imbalance_defence','blackout_mode'
    inputs_hash         CHAR(64) NOT NULL,                  -- SHA-256 of canonical inputs
    inputs              JSONB NOT NULL,                     -- replayable
    recommendations     JSONB NOT NULL,                     -- [{asset_id, hour, action, mw}]
    expected_uplift_uah NUMERIC(14,2) NOT NULL,
    risk_flags          JSONB NOT NULL DEFAULT '[]'::jsonb, -- ['cap_exposure','low_soc',...]
    confidence_pct      NUMERIC(5,2) NOT NULL,
    duration_ms         INTEGER NOT NULL
);
CREATE INDEX ON ems.optimisation_runs (tenant_id, requested_at DESC);
```

**Rows:** ~30 (one per demo session click).

### 3.6 `regulatory` schema

#### 3.6.1 `regulatory.forecast_submissions`

Services BRIEF §11.19 (Подача прогнозу stub). Lifted from `research_regulatory_data_shape.md §9.1`.

```sql
CREATE TABLE regulatory.forecast_submissions (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    submission_id       TEXT NOT NULL,            -- mRID
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitter_eic       CHAR(16) NOT NULL,
    resource_eic        CHAR(16),
    bzn_eic             CHAR(16) NOT NULL DEFAULT '10Y1001C--00003F',
    business_type       CHAR(3) NOT NULL,         -- A01 / A04 / A85
    document_type       CHAR(3) NOT NULL,         -- A09 / A71 / A65
    process_type        CHAR(3) NOT NULL,         -- A01 day-ahead
    delivery_date       DATE NOT NULL,
    resolution_minutes  SMALLINT NOT NULL DEFAULT 60,
    hourly_volumes_mwh  NUMERIC(10,4)[] NOT NULL, -- 24-element array
    status              TEXT NOT NULL DEFAULT 'DRAFT'
                          CHECK (status IN ('DRAFT','SUBMITTED','ACK','REJECTED')),
    status_changed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_xml             TEXT,                     -- generated ENTSO-E ScheduleDocument stub
    UNIQUE (tenant_id, submission_id)
);
CREATE INDEX ON regulatory.forecast_submissions (tenant_id, delivery_date);
```

**Status transitions** (server-computed-on-read; no background worker per BRIEF §12):
- On INSERT: `status='DRAFT'`.
- On read, if `(now() - submitted_at) > 200ms` and `status='DRAFT'` → server flips to `'SUBMITTED'`.
- On read, if `(now() - submitted_at) > 1000ms` and `status='SUBMITTED'` → flips to `'ACK'`.

This resolves the `HLA §10.1` open item: the mechanism is **server-computed on read**, not a worker.

**Rows:** 1 per producer per day × 30 days × ~2 producer-tenants ≈ **60–120**.

#### 3.6.2 `regulatory.settlement_statements` and `regulatory.settlement_statement_lines`

Per `research_regulatory_data_shape.md §9.3`.

```sql
CREATE TABLE regulatory.settlement_statements (
    id                      BIGSERIAL PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    statement_no            TEXT NOT NULL,
    counterparty            TEXT NOT NULL,
    counterparty_edrpou     CHAR(8),
    contract_no             TEXT,
    period_year             SMALLINT NOT NULL,
    period_month            SMALLINT NOT NULL CHECK (period_month BETWEEN 1 AND 12),
    period_start            DATE NOT NULL,
    period_end              DATE NOT NULL,
    volume_total_mwh        NUMERIC(14,4) NOT NULL,
    amount_net_uah          NUMERIC(14,2) NOT NULL,
    vat_rate                NUMERIC(4,2) NOT NULL DEFAULT 0.20,
    amount_vat_uah          NUMERIC(14,2) NOT NULL,
    amount_gross_uah        NUMERIC(14,2) NOT NULL,
    payment_due_date        DATE NOT NULL,
    payment_received_at     TIMESTAMPTZ,
    status                  TEXT NOT NULL DEFAULT 'DRAFT' CHECK
                              (status IN ('DRAFT','ISSUED','SIGNED','PAID','DISPUTED')),
    signed_doc_id           BIGINT,                       -- FK added after signed_documents
    UNIQUE (tenant_id, statement_no)
);
CREATE INDEX ON regulatory.settlement_statements (tenant_id, period_year, period_month);

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
```

**Note on Apr/May 2026:** because the 30-day window spans the Apr 30 → May 1 month boundary, we have **two monthly statements per (tenant, counterparty)** for tenants with green-tariff settlements.

**Rows:** ~3 tenants × ~2 counterparties × 2 months ≈ **~12 statements**; lines ≈ 60.

#### 3.6.3 `regulatory.signed_documents` — КЕП stub

Services BRIEF §11.20. Lifted from `research_regulatory_data_shape.md §7` and `§9.6`.

```sql
CREATE TABLE regulatory.signed_documents (
    id                      BIGSERIAL PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    document_type           TEXT NOT NULL CHECK
                              (document_type IN
                                ('SETTLEMENT_ACT','BID_PACKAGE','FORECAST_PACKAGE','REPORT','CONTRACT')),
    document_ref_table      TEXT NOT NULL,
    document_ref_id         BIGINT NOT NULL,
    signer_name             TEXT NOT NULL,           -- 'Іваненко Іван Іванович'
    signer_position         TEXT,
    signer_edrpou           CHAR(8),
    signer_ipn              CHAR(10),
    acsk_name               TEXT NOT NULL,           -- 'Дія','ПриватБанк','ІДД ДПС','Ключові системи'
    signature_format        TEXT NOT NULL DEFAULT 'CAdES-X-Long',
    document_hash_sha256    CHAR(64) NOT NULL,       -- real hash of fake content
    signed_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    tsa_provider            TEXT DEFAULT 'czo.gov.ua',
    cert_serial             TEXT,
    cert_valid_until        DATE,
    p7s_blob                BYTEA NOT NULL,          -- 64 random bytes; stub
    is_demo_stub            BOOLEAN NOT NULL DEFAULT TRUE,   -- always TRUE in v2
    kep_badge_short         TEXT GENERATED ALWAYS AS
                              (signer_name || ' · ЄДРПОУ ' ||
                               COALESCE(signer_edrpou, signer_ipn, 'n/a') ||
                               ' · ' || TO_CHAR(signed_at,'YYYY-MM-DD HH24:MI'))
                              STORED
);
CREATE INDEX ON regulatory.signed_documents (document_ref_table, document_ref_id);

-- Wire the FK from settlement_statements after this table exists
ALTER TABLE regulatory.settlement_statements
    ADD CONSTRAINT fk_signed_doc FOREIGN KEY (signed_doc_id)
    REFERENCES regulatory.signed_documents(id);
```

**Exact UI badge fields agreed** (per `research_regulatory_data_shape.md §7`):
- Title: `Підписано КЕП` + DEMO watermark
- Signer name (`signer_name`)
- ЄДРПОУ (`signer_edrpou`)
- Signed ISO timestamp (`signed_at` formatted `YYYY-MM-DDTHH:MM:SS±03:00`)
- Truncated SHA-256 hex (`document_hash_sha256` first 8 + last 8 chars, e.g. `9f3a8b21…d71c40af`)
- АЦСК (`acsk_name`)

**Rows:** 1 per settlement statement + 1 per submitted forecast package + 1 per signed report ≈ **~30**.

The badge is ALWAYS rendered with a `DEMO` watermark (per HLA R6). The mandatory disclosure page `/about/credentials` lists every stub.

#### 3.6.4 `regulatory.regulator_events`

Per `research_regulatory_data_shape.md §9.5`.

```sql
CREATE TABLE regulatory.regulator_events (
    id              BIGSERIAL PRIMARY KEY,
    issuer          TEXT NOT NULL CHECK
                      (issuer IN ('НКРЕКП','Укренерго','Кабмін','ОРЕЕ','ГП')),
    act_type        TEXT NOT NULL,
    act_number      TEXT,
    issued_at       DATE NOT NULL,
    effective_at    DATE,
    title           TEXT NOT NULL,
    category        TEXT CHECK (category IN
                      ('TARIFF','CODE_AMENDMENT','SANCTION','EMERGENCY','MARKET_FREEZE','INFO')),
    severity        TEXT NOT NULL DEFAULT 'INFO' CHECK
                      (severity IN ('INFO','NOTICE','WARN','CRITICAL')),
    summary         TEXT NOT NULL,
    affected_entities JSONB NOT NULL DEFAULT '[]'::jsonb,
    affected_tenants UUID[] NOT NULL DEFAULT '{}'::uuid[],
    source_url      TEXT,
    full_text       TEXT
);
CREATE INDEX ON regulatory.regulator_events (issued_at DESC);
CREATE INDEX ON regulatory.regulator_events USING GIN (affected_entities);
```

**Note:** `regulator_events` is intentionally cross-tenant readable for the `/admin/*` surface; the `affected_tenants` array gates which demo-tenant sees which event in their persona feed. The RLS policy for this table is `USING (TRUE)` for reads, restricted writes (§3.9).

**Rows:** 8–12 over 30 days.

### 3.7 `agents` schema

#### 3.7.1 `agents.query_log`

Services BRIEF §11.15 (live-DB evidence audit).

```sql
CREATE TABLE agents.query_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES core.tenants(id) ON DELETE CASCADE,
    persona         TEXT NOT NULL CHECK
                      (persona IN ('dispatcher_analyst','market_analyst',
                                   'energy_advisor','battery_coach')),
    user_text       TEXT NOT NULL,
    classified_intent TEXT NOT NULL,
    confidence      NUMERIC(4,3) NOT NULL,
    response_text   TEXT NOT NULL,
    evidence        JSONB NOT NULL DEFAULT '[]'::jsonb,
                      -- [{table:'market.rdn_prices', row_id:123, columns_used:[...]}]
    duration_ms     INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON agents.query_log (tenant_id, created_at DESC);
```

**Rows:** dynamic. Capped at last 1000 per tenant by background cleanup (NOT scheduled; runs only when query_log INSERTs trigger threshold check on the same connection — no background worker per BRIEF §12).

#### 3.7.2 `agents.response_cache`

```sql
CREATE TABLE agents.response_cache (
    cache_key       TEXT PRIMARY KEY,                 -- SHA-256(tenant_id || persona || normalised_text)
    response_text   TEXT NOT NULL,
    evidence        JSONB NOT NULL DEFAULT '[]'::jsonb,
    persona         TEXT NOT NULL,
    cached_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ttl_seconds     INTEGER NOT NULL DEFAULT 300
);
```

### 3.8 `audit` schema

```sql
CREATE TABLE audit.events (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID,                              -- nullable for system events
    user_id         UUID REFERENCES core.users(id),
    actor           TEXT NOT NULL,                     -- 'user:<uuid>'|'system'|'admin'
    event_type      TEXT NOT NULL,                     -- 'tenant.switch','bid.submit','sign.created',...
    ref_table       TEXT,
    ref_id          TEXT,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id      UUID
);
CREATE INDEX ON audit.events (tenant_id, occurred_at DESC);
CREATE INDEX ON audit.events (event_type, occurred_at DESC);
```

**Rows:** unbounded, but capped at ~10k for the demo (cleanup at synth seed).

### 3.9 RLS policies

Every domain table gets RLS. Migration `009_rls_policies.py` creates them after all tables exist.

```sql
-- Apply to every table that has tenant_id column
ALTER TABLE core.tenants                       ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.users                         ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.assets                        ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.rdn_prices                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.vdr_trades                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.br_settlements              ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.dd_contracts                ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.dd_contract_hourly_volume   ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.bids                        ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.ancillary_offers            ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.ancillary_activations       ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.setpoints                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.telemetry                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.instructions              ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.instruction_acks          ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.operator_adjustments      ENABLE ROW LEVEL SECURITY;
ALTER TABLE ems.forecasts                      ENABLE ROW LEVEL SECURITY;
ALTER TABLE ems.forecast_actuals               ENABLE ROW LEVEL SECURITY;
ALTER TABLE ems.kpi_daily                      ENABLE ROW LEVEL SECURITY;
ALTER TABLE ems.optimisation_runs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory.forecast_submissions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory.settlement_statements   ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory.settlement_statement_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory.signed_documents        ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents.query_log                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.events                       ENABLE ROW LEVEL SECURITY;
```

**The standard tenant policy** (applied with appropriate ALTER on each):

```sql
CREATE POLICY tenant_isolation_select ON <table> FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation_modify ON <table> FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

**Cross-tenant table — `regulator_events`** — different policy (per HLA §3.7 design):

```sql
ALTER TABLE regulatory.regulator_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY regevent_read_all ON regulatory.regulator_events FOR SELECT USING (TRUE);
CREATE POLICY regevent_write_admin ON regulatory.regulator_events FOR ALL
    USING (current_setting('app.is_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_admin', true) = 'true');
```

**Admin bypass for `/admin/*` endpoints:**

```sql
-- For cross-tenant reads in /admin/* surfaces, FastAPI explicitly does:
-- SET LOCAL app.is_admin = 'true';
-- The session reset (SET LOCAL) ensures the flag is request-scoped only.

CREATE POLICY tenant_isolation_admin_bypass ON <table> FOR SELECT
    USING (current_setting('app.is_admin', true) = 'true');
```

Implementation: every admin endpoint is wrapped in `@cross_tenant` decorator (§6.5) that sets `app.is_admin='true'` and logs `audit.events` with `event_type='admin.cross_tenant_read'`.

**Why RLS not application filter:** if a developer forgets `WHERE tenant_id = $1` in a new endpoint, the DB returns nothing instead of leaking. The §11.13 "sub-1 hour to swap data" claim depends on this being enforced at the layer that can't be bypassed by a coding mistake.

### 3.10 Grants and roles

```sql
CREATE ROLE gecko_api LOGIN PASSWORD '<env>';
CREATE ROLE gecko_migrate LOGIN PASSWORD '<env>' BYPASSRLS;
CREATE ROLE gecko_readonly LOGIN PASSWORD '<env>';

GRANT USAGE ON SCHEMA core,market,dispatch,ems,regulatory,agents,audit TO gecko_api;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA
    core,market,dispatch,ems,regulatory,agents,audit TO gecko_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA
    core,market,dispatch,ems,regulatory,agents,audit TO gecko_api;

-- gecko_api MUST NOT have BYPASSRLS
ALTER ROLE gecko_api NOBYPASSRLS;
```

### 3.11 Synthetic data generator contract

Per HLA §3.7. The `apps/synth` container does not produce code in this doc; it produces a contract.

#### 3.11.1 Inputs

- `synth.yaml` (committed) — config:
  ```yaml
  rng_seed: 20260523
  window_start: 2026-04-23
  window_end:   2026-05-23
  tenants:
    - { code: producer-1, segment: producer,
        display_name: 'ТОВ "Поляна Енерджі"', region: 'Закарпатська', edrpou: 'XXXXXXXX',
        participant_eic: '10X-UA-PROD-001', asset_mix: [SES:3, VES:1, UZE:1, GPU:1] }
    - { code: ci-1, segment: c-i,
        display_name: 'ПАТ "Дніпровий Завод"', region: 'Дніпропетровська', edrpou: 'XXXXXXXX',
        participant_eic: '10X-UA-CI-001', asset_mix: [SES:1, AktSpoz:1, UZE:1, Spozhyvach:1] }
    - { code: storage-1, segment: storage,
        display_name: 'ТОВ "Запоріжжя Сторідж"', region: 'Запорізька', edrpou: 'XXXXXXXX',
        participant_eic: '10X-UA-STOR-001', asset_mix: [UZE:2, SES:1] }
  market:
    rdn_cap_uah_mwh: { default: 6300, peak: 6900, off_peak: 5600 }
    cap_pinning_probability: 0.40       # share of days where evening peak pins to cap
    cap_pinning_hours: [17,18,19,20,21] # which hours can pin
    vdr_trades_per_day: 30
    br_imbalance_sigma: 0.05            # σ of imbalance as fraction of nameplate
  events:
    res_curtailments: 6                 # over 30-day window
    planned_maintenance: 2              # one per producer-tenant
    regulator_notices: 10
    forecast_submissions_per_day: 1
  ```

#### 3.11.2 Outputs

A populated Postgres + a coverage report `phase-3-architecture/synth_coverage.md` listing, for each acceptance criterion that requires data, **which seeded rows satisfy it**:

```
§11.4  Surfaces — 9 surfaces (producer)             ✅ rows: assets=8, telemetry=21,600, ...
§11.11 ENTSO-E EIC codes                            ✅ rows: eic_codes=25 (Y/X/W/V types covered)
§11.12 Ukrainian asset names, грн, EET, 1-20 МВт     ✅ rows: assets=24-36 in 1-20 МВт range
§11.19 Forecast submission — at least one ACK         ✅ rows: forecast_submissions=60+ with ACK
§11.20 КЕП stub on settlement statement              ✅ rows: signed_documents=12+ on SETTLEMENT_ACT
§11.21 Single pane РДН + ВДР + БР + ДД                 ✅ rows: rdn_prices=2,160; vdr_trades=2,700; br_settlements=2,160; dd_contracts=15
§11.22 CO₂ avoided KPI                              ✅ rows: kpi_daily with co2_avoided_tn > 0
§11.27 Scenario cards (curtailment, imbalance)       ✅ rows: ≥1 curtailment day in window, ≥1 imbalance spike day
```

If the coverage report has a `❌`, CI fails. This is HLA R7 (mitigation) made concrete.

#### 3.11.3 Events injected (within 30-day window)

Per HLA D10 "Story arcs that fit in 30 days":
1. **Weekday/weekend baseload swing** — naturally produced by demand profile.
2. **РДН evening-peak cap-pinning** — 12 of 30 days (40%); hours 17:00–21:00 pinned at hourly cap.
3. **1–2 RES curtailment days** — one solar curtailment around midday on a high-output day (e.g. 2026-05-12); one wind curtailment overnight (low demand, high wind, e.g. 2026-05-04).
4. **1 planned maintenance** — Producer-1's `ВЕС` offline 2026-05-08 to 2026-05-12 (5 days).
5. **Monthly settlement boundary** — Apr 30 → May 1 transition produces two monthly settlement statements per (tenant, counterparty).
6. **Regulator notices** — ~10 events spread across window: 2 TARIFF, 3 INFO, 2 NOTICE, 2 WARN, 1 CRITICAL.
7. **Forecast submissions** — daily for producer-1, daily for ci-1 (consumption A04), monthly settlement-statement sign event for storage-1.
8. **Negative РДН price** — 1 day around 2026-05-04 (PV surplus + low load + weekend) — РДН hits zero for 2–3 midday hours.

#### 3.11.4 Determinism contract

- RNG seeded from `synth.yaml rng_seed`. Identical seed → identical data.
- All "random" choices (curtailment day, signer name from fixture list, counterparty code) are seeded.
- Re-running the synth container `TRUNCATE`s every domain table and reseeds (HLA §5.2). Migrations are preserved.

#### 3.11.5 Coverage / sniff-test (mitigation of HLA R4)

`apps/synth/synth/sniff_test.py` runs after seed and asserts:
- Every РДН evening-peak hour (17:00–21:00) has price ≤ `cap_uah_mwh`.
- Every battery SOC ∈ [10, 90]%.
- Every EIC is 16 chars and matches `^10[YXWVTZ][A-Z0-9-]{12}[A-Z0-9]$`.
- Every settlement: `amount_gross_uah ≈ amount_net_uah × (1 + vat_rate)` within rounding.
- Every `is_capped=TRUE` row also has `price_uah_mwh = cap_uah_mwh`.
- For each acceptance criterion in §11 needing data: coverage report shows `✅`.

Fails block deploy.

---

## 4. API contracts

All routes under `/api/v1/`. JSON envelope: `{"data": <payload>, "meta": {...}}` on success; `{"error": {"code": "...", "message": "...", "details": {...}}}` on failure. Tenant injected via `X-Tenant-Id` header. Admin routes additionally require `X-Admin: true`. Pagination: `?page=1&per_page=50` (max per_page=200).

OpenAPI 3.1 served at `/openapi.json`. `operationId` convention: `{module}.{resource}.{verb}` (e.g., `market.rdn.list`, `market.bids.submit`).

### 4.1 Envelope conventions

```typescript
type Success<T> = { data: T; meta: { request_id: string; tenant_id: string; generated_at: string } };
type Error = { error: { code: string; message: string; details?: Record<string, unknown> } };
```

Error codes (canonical list):
- `INVALID_TENANT` (400)
- `MISSING_TENANT_HEADER` (400)
- `NOT_FOUND` (404)
- `VALIDATION_FAILED` (422)
- `RATE_LIMITED` (429)
- `INTERNAL_ERROR` (500)
- `STUB_NOT_IMPLEMENTED` (501) — used by mutating endpoints flagged as stub-only

All timestamps **ISO 8601 with Europe/Kyiv offset** (`2026-05-23T14:32:11+03:00`). All monetary values returned as **numeric strings** to avoid JS float drift; unit explicit in field name (`price_uah_mwh`).

### 4.2 `/api/v1/auth/*` — mock auth

#### `POST /api/v1/auth/switch-tenant`

- Module: `core`
- Services BRIEF §11.2.
- Request:
  ```json
  { "tenant_code": "producer-1" }
  ```
- Response (`data`):
  ```json
  { "tenant": { "id": "uuid", "code": "producer-1", "display_name": "...", "segment": "producer" } }
  ```
- Errors: `INVALID_TENANT` if code not in `core.tenants`.
- Side effect: Next.js route handler sets `gecko_tenant_id` cookie; FastAPI returns 200 only.

#### `GET /api/v1/auth/me`

- Module: `core`
- Response: `{ "tenant": {...}, "user": { "id": null, "display_name": "Demo user", "role": "operator" } }`

### 4.3 `/api/v1/market/*` — Ринкова інтеграція

#### `GET /api/v1/market/rdn`

- Module: `market`
- Services BRIEF §11.21.
- Query: `?date=YYYY-MM-DD&date_end=YYYY-MM-DD&bidding_zone_eic=10Y1001C--00003F`
- Response `data`:
  ```json
  [
    { "date": "2026-05-12", "hour": 18, "interval_start": "2026-05-12T18:00:00+03:00",
      "price_uah_mwh": "6900.00", "volume_mwh": "1245.300",
      "is_capped": true, "cap_uah_mwh": "6900.00",
      "daily_index_base": "4123.40", "daily_index_peak": "6321.80" }
  ]
  ```

#### `GET /api/v1/market/vdr`

- Module: `market`
- Services BRIEF §11.21.
- Query: `?date=YYYY-MM-DD&delivery_hour=18`
- Response: array of `vdr_trades` rows (camelCase preserved on field names per `market.vdr_trades` DDL).

#### `GET /api/v1/market/br`

- Module: `market`
- Services BRIEF §11.21.
- Query: `?date=YYYY-MM-DD&date_end=YYYY-MM-DD`
- Response: array of `br_settlements` rows including `our_imbalance_mwh`, `settlement_uah`.

#### `GET /api/v1/market/dd`

- Module: `market`
- Services BRIEF §11.21.
- Response: array of `dd_contracts` with embedded `hourly_volumes` only when `?expand=hourly_volumes` is passed (otherwise the contract header only).

#### `POST /api/v1/market/bids`

- Module: `market`
- Services BRIEF §11.21. Stub-mutation (writes to `market.bids` with `state='ACTIVE'`).
- Request:
  ```json
  { "market": "RDN", "delivery_date": "2026-05-24", "hour": 18, "side": "SELL",
    "bid_type": "SIMPLE", "volume_mwh": "5.000", "price_uah_mwh": "4200.00",
    "resource_eic": "10W-UA-POLY-01" }
  ```
- Response: created `bid_id`, status `ACTIVE`. After a server-computed delay (status flip on read after 500 ms → `ACCEPTED` with stub clearing_price), badge updates.

#### `GET /api/v1/market/bids?date=...&market=RDN`

- Module: `market`
- Returns paginated bid history.

#### `GET /api/v1/market/revenue?range=30d`

- Module: `market`
- Services BRIEF §11.22 (revenue split feed). Returns aggregated revenue by channel:
  ```json
  { "by_channel": [
      { "channel": "RDN", "revenue_uah": "1234567.89", "share_pct": 45.2 },
      { "channel": "VDR", "revenue_uah": "543210.00",  "share_pct": 19.9 },
      { "channel": "BR",  "revenue_uah": "112233.00",  "share_pct": 4.1 },
      { "channel": "DD",  "revenue_uah": "812345.00",  "share_pct": 29.8 },
      { "channel": "ANC", "revenue_uah": "27451.00",   "share_pct": 1.0 }
  ],
  "total_uah": "2729806.89" }
  ```

### 4.4 `/api/v1/dispatch/*` — Диспетчеризація

#### `GET /api/v1/dispatch/setpoints?asset_id={uuid}&from=...&to=...`

- Module: `dispatch`
- Services BRIEF §11.4.

#### `POST /api/v1/dispatch/setpoints`

- Module: `dispatch`
- Services BRIEF §11.4. Stub-mutation.
- Request:
  ```json
  { "asset_id": "uuid", "effective_from": "2026-05-24T18:00:00+03:00",
    "effective_to": "2026-05-24T19:00:00+03:00",
    "target_power_mw": "3.500", "reason": "manual" }
  ```
- Response: created `setpoint_id`, `state='pending'` → server-computed flip to `'acknowledged'` after 300 ms.

#### `GET /api/v1/dispatch/telemetry?asset_id={uuid}&from=...&to=...`

- Module: `dispatch`
- Services BRIEF §11.4.
- Response: hourly rows from `dispatch.telemetry`. Limited to 1000 rows; for longer ranges use `?per_page=200&page=N`.

#### `GET /api/v1/dispatch/instructions`

- Module: `dispatch`
- Services BRIEF §11.4.

### 4.5 `/api/v1/ems/*` — EMS

#### `GET /api/v1/ems/forecasts?type=solar|wind|load|price&asset_id=...&date=...`

- Module: `ems`
- Services BRIEF §11.4, §11.19.

#### `POST /api/v1/ems/forecasts/submit`

- Module: `ems` (delegates to `regulatory.forecast_submissions`)
- Services BRIEF §11.19.
- Request:
  ```json
  { "delivery_date": "2026-05-24", "resource_eic": "10W-UA-POLY-01",
    "business_type": "A01", "resolution_minutes": 60,
    "hourly_volumes_mwh": ["0.000","0.000",...,"4.200",...] }
  ```
- Response: `submission_id` and initial `status="DRAFT"`. Stubbed XML available via `GET /api/v1/regulatory/forecast-submissions/{id}/raw-xml`.

#### `POST /api/v1/ems/optimise`

- Module: `ems`
- Services BRIEF §11.14.
- Synchronous; deterministic. Returns within 2 seconds.
- Request:
  ```json
  { "scenario": "arbitrage",
    "horizon_hours": 24,
    "asset_ids": ["uuid", "..."] }
  ```
- Response:
  ```json
  { "run_id": 42, "scenario": "arbitrage",
    "recommendations": [
      { "asset_id": "uuid", "hour": 18, "action": "discharge", "mw": "3.500" }
    ],
    "expected_uplift_uah": "12450.00",
    "confidence_pct": "78.50",
    "risk_flags": ["cap_exposure"],
    "duration_ms": 187 }
  ```

#### `GET /api/v1/ems/kpi/daily?date=2026-05-23`

- Module: `ems`
- Services BRIEF §11.22.

#### `GET /api/v1/ems/kpi/portfolio?range=30d`

- Module: `ems`
- Services BRIEF §11.22.
- Returns from `ems.kpi_portfolio_30d` MV.

### 4.6 `/api/v1/assets/*` — asset registry

#### `GET /api/v1/assets`

- Module: `core`
- Query: `?asset_class=СЕС&owner_segment=producer`
- Returns rows from `core.assets`.

#### `GET /api/v1/assets/{id}`

- Module: `core`

#### `GET /api/v1/assets/{id}/telemetry?from=...&to=...`

- Module: `dispatch` (proxy convenience)

### 4.7 `/api/v1/regulatory/*`

#### `GET /api/v1/regulatory/settlements?period=2026-05`

- Module: `regulatory`

#### `GET /api/v1/regulatory/settlements/{id}`

- Module: `regulatory`
- Includes embedded `lines`.

#### `POST /api/v1/regulatory/documents/{ref_table}/{ref_id}/sign`

- Module: `regulatory`
- Services BRIEF §11.20.
- Request body: optional `{ "signer_hint": "operator" }`.
- Response:
  ```json
  { "signed_doc_id": 17,
    "badge_text": "Підписано КЕП · Іваненко І.І. · ЄДРПОУ 12345678 · 2026-05-23T14:32:11+03:00",
    "badge_fields": {
      "signer_name": "Іваненко Іван Іванович",
      "signer_edrpou": "12345678",
      "acsk_name": "Дія",
      "signed_at": "2026-05-23T14:32:11+03:00",
      "hash_short": "9f3a8b21…d71c40af"
    },
    "is_demo_stub": true }
  ```

#### `GET /api/v1/regulatory/events`

- Module: `regulatory`
- Returns events visible to current tenant (filtered by `affected_tenants ARRAY` or empty).

### 4.8 `/api/v1/agents/*`

#### `POST /api/v1/agents/{persona}/query`

- Module: `agents`
- Services BRIEF §11.15.
- `{persona}` ∈ `dispatcher_analyst | market_analyst | energy_advisor | battery_coach`.
- Request:
  ```json
  { "text": "коли наступний небаланс?", "context": { "current_url": "/producer/rynok" } }
  ```
- Response:
  ```json
  { "intent": "next_imbalance_window",
    "confidence": 0.91,
    "answer": "Найближче вікно небалансу: завтра 18:00–19:00...",
    "evidence": [
      { "table": "market.br_settlements", "row_id": 12345,
        "columns_used": ["our_imbalance_mwh","price_short_uah_mwh"],
        "ui_link": "/producer/rynok?date=2026-05-24&hour=18" }
    ],
    "persona": "dispatcher_analyst",
    "duration_ms": 47 }
  ```

#### `GET /api/v1/agents/voice/session`

- Module: `agents`
- Services BRIEF §11.16.
- Response:
  ```json
  { "provider": "stub",
    "session_token": "demo-session-uuid",
    "websocket_url": null,
    "canned_scenarios": [
      { "intent": "today_production",        "trigger": "що сьогодні з виробництвом" },
      { "intent": "charge_battery_when",     "trigger": "коли заряджати батарею" },
      { "intent": "next_imbalance_window",   "trigger": "коли наступний небаланс" },
      { "intent": "asset_status_overview",   "trigger": "покажи стан активів" },
      { "intent": "generate_report_today",   "trigger": "сформуй звіт за сьогодні" }
    ]
  }
  ```
- When backend env `VOICE_PROVIDER=openai-realtime` and `OPENAI_API_KEY` is set: `provider="openai-realtime"`, `websocket_url="wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"`, `session_token` is a short-lived ephemeral key issued by the FastAPI process via OpenAI's ephemeral key endpoint.

### 4.9 `/api/v1/admin/*`

All admin routes set `app.is_admin='true'` on the DB session for the request lifetime. Logged as `audit.events` with `event_type='admin.cross_tenant_read'`.

#### `GET /api/v1/admin/portfolio`

- Module: `core` + cross-tenant join

Returns aggregate across all 3 demo tenants:
```json
{ "tenants": [ { "code": "producer-1", "asset_count": 6, "capacity_mw": "30.500",
                 "revenue_30d_uah": "..." }, ... ],
  "total_capacity_mw": "52.300",
  "total_revenue_30d_uah": "..." }
```

#### `GET /api/v1/admin/operations`

- Cross-tenant dispatch view.

#### `GET /api/v1/admin/analytics`

- Cross-tenant KPI feed.

### 4.10 Webhook subscriptions (stub for `/developer/webhooks/`)

#### `GET /api/v1/webhooks/event-types`

Returns documented event types (no real delivery in v2):
```json
[
  { "type": "bid.cleared", "schema_ref": "#/components/schemas/BidClearedEvent" },
  { "type": "imbalance.detected", "schema_ref": "#/components/schemas/ImbalanceEvent" },
  { "type": "settlement.signed", "schema_ref": "#/components/schemas/SettlementSignedEvent" },
  { "type": "regulator.notice", "schema_ref": "#/components/schemas/RegulatorNoticeEvent" }
]
```

#### `GET /api/v1/webhooks/sample/{type}`

Returns one synthetic example payload of that event type. Documentation only — no live delivery.

### 4.11 Caching headers

All `GET` endpoints listed above: `Cache-Control: public, max-age=60, stale-while-revalidate=300`.
All mutating endpoints (`POST/PATCH/DELETE`): `Cache-Control: no-store`.
The voice-session endpoint: `Cache-Control: no-store` (short-lived tokens).

---

## 5. Frontend architecture

### 5.1 Design tokens — the contract

Tokens live in `apps/web/styles/tokens.css`. **Every component reads tokens; no component contains literal hex.**

```css
:root[data-theme="light"] {
  /* surfaces */
  --color-bg-page:        #F8FAFC;
  --color-bg-card:        #FFFFFF;
  --color-bg-elevated:    #FFFFFF;
  --color-bg-muted:       #F1F5F9;

  /* text */
  --color-text-primary:   #0F172A;
  --color-text-heading:   #020617;
  --color-text-muted:     #475569;
  --color-text-inverse:   #FFFFFF;

  /* brand */
  --color-brand-primary:  #14B8A6;
  --color-brand-deep:     #0F766E;
  --color-brand-light:    #2DD4BF;

  /* status */
  --color-status-success: #10B981;
  --color-status-warning: #F59E0B;
  --color-status-alert:   #F43F5E;
  --color-status-info:    #0EA5E9;

  /* border / divider */
  --color-border-base:    #E2E8F0;
  --color-border-strong:  #CBD5E1;

  /* chart palette (5 categorical colours) */
  --chart-c1: #14B8A6;
  --chart-c2: #0F766E;
  --chart-c3: #FBBF24;
  --chart-c4: #64748B;
  --chart-c5: #D946EF;

  /* spacing scale (4px base) */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem;
  --space-4: 1rem;    --space-6: 1.5rem; --space-8: 2rem;
  --space-12: 3rem;   --space-16: 4rem;

  /* typography */
  --font-sans: 'Manrope', 'Montserrat', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  --font-size-xs: 0.75rem; --font-size-sm: 0.875rem; --font-size-base: 1rem;
  --font-size-lg: 1.125rem; --font-size-xl: 1.25rem; --font-size-2xl: 1.5rem;
  --font-size-3xl: 2rem; --font-size-4xl: 2.5rem;

  /* radii */
  --radius-sm: 0.25rem; --radius-md: 0.5rem; --radius-lg: 0.75rem; --radius-xl: 1rem;

  /* shadows */
  --shadow-card: 0 1px 2px rgba(15,23,42,0.04), 0 2px 8px rgba(15,23,42,0.06);
  --shadow-popover: 0 8px 24px rgba(15,23,42,0.10);
}

:root[data-theme="dark"] {
  --color-bg-page:        #0A1C1F;
  --color-bg-card:        #114248;
  --color-bg-elevated:    #134E54;
  --color-bg-muted:       #0E2B2E;

  --color-text-primary:   #F1F5F9;
  --color-text-heading:   #FFFFFF;
  --color-text-muted:     #94A3B8;
  --color-text-inverse:   #0F172A;

  --color-brand-primary:  #14B8A6;
  --color-brand-deep:     #0F766E;
  --color-brand-light:    #2DD4BF;

  --color-status-success: #10B981;
  --color-status-warning: #F59E0B;
  --color-status-alert:   #F43F5E;
  --color-status-info:    #0EA5E9;

  --color-border-base:    #1E3A40;
  --color-border-strong:  #2A5560;

  --chart-c1: #2DD4BF; --chart-c2: #14B8A6; --chart-c3: #FBBF24;
  --chart-c4: #94A3B8; --chart-c5: #D946EF;

  /* spacing/typography/radii/shadows inherit (same values) */
}
```

**Theme bootstrap:** `apps/web/app/layout.tsx` reads `localStorage.getItem('gecko_theme') || 'light'` in an inline script BEFORE React hydrates, sets `<html data-theme="...">`. Avoids flash of wrong theme.

**Token mapping enforcement:** ESLint rule (config in `apps/web/.eslintrc.json`) forbids literal hex in `*.tsx` and `*.css` files inside `apps/web/components/` and `apps/web/app/`. Only `tokens.css` may contain hex.

### 5.2 Component tree

#### 5.2.1 Shell

- `<AppShell>` (`components/shell/AppShell.tsx`)
  - wraps every persona route with sidebar + topbar slot
  - reads tenant from cookie, persona from URL prefix
- `<TopBar>` — children in order (left→right):
  - logo (gecko head + wordmark)
  - `<PersonaSwitcher>` (collapsed pill showing current persona)
  - global search field (placeholder; opens `<CommandPalette>` on focus)
  - `<TenantSwitcher>` (dropdown of 3 demo tenants)
  - alerts bell (badge with unread count from `regulator_events` + `dispatch.instructions` with `priority=1`)
  - `<AgentLauncher>` — opens `<AgentChat>` drawer; persona-aware
  - `<VoiceButton>` — push-to-talk
  - `<ThemeToggle>` (sun/moon icon, keyboard shortcut Shift+T)
  - user avatar (mock)
- `<Sidebar>` — per persona, lists the 9 (producer) or 5 (c-i, storage) surfaces with Ukrainian labels.

#### 5.2.2 Hero

- `<PersonaPicker>` (`/`) — three large cards: "Я виробник" / "Я бізнес (C&I)" / "Я УЗЕ-власник" + smaller `/developer/` + `/admin/` chips
- `<ArchitectureDiagram>` — interactive SVG of slide 7 (HLA D15). 15 nodes, ~25 connection paths. Implementation: React + inline SVG + Framer Motion. Click node → router push to matching surface. Hover → animate adjacent edges + show tooltip with English/Ukrainian label.

#### 5.2.3 KPI

- `<KPITile>` — single tile: icon + value + label + delta-vs-yesterday arrow
- `<KPIGrid>` — wraps 6 tiles for `/producer/`:
  1. грн зекономлено (30d)
  2. грн зароблено (30d)
  3. небаланси уникнено (МВт·год)
  4. CO₂ avoided (тонн)
  5. доступність (%)
  6. рейтинг можливостей (0–100)
- For `/c-i/`: replace "грн зароблено" with "своя генерація %"; add "load shaved (МВт·год)".
- For `/storage/`: replace with "cycles used", "ancillary revenue (грн)".

#### 5.2.4 Assets

- `<AssetCard>` — compact tile with icon (per `asset_class`), name, capacity, status pill.
- `<AssetTable>` — sortable, filterable. Columns: name, class, capacity, region, status, today's revenue. Click row → router push to detail page (NOT drawer).
- `<AssetDrawer>` — slide-out panel from right, used on `/producer/aktyvy/` for "fast peek" without navigation. Shows last-24h chart + 3 KPI tiles.

#### 5.2.5 Charts

- `<HourlyChart>` — Recharts `<ComposedChart>`. **Library chosen: Recharts** (justification: 0 SSR friction, smaller bundle vs visx for our chart count, MIT, light/dark theme inheritance via CSS vars works natively). Supports 1..24 hour x-axis (UA convention), `<PriceCapOverlay>` band for cap-pinning visualisation.
- `<BatterySoCArc>` — radial gauge. Custom SVG, no library. 0–100% arc, threshold lines at 10% (deep discharge) and 90% (top-of-charge), animated to current SoC value.
- `<ForecastChart>` — Recharts; overlays actual (solid) + primary forecast (dashed) + refined forecast (dotted). Footer line shows MAPE.
- `<PriceCapOverlay>` — auxiliary; renders shaded band when `is_capped=true` rows are present.

#### 5.2.6 Dispatch

- `<DispatchQueue>` — vertical timeline of pending/executing/done setpoints (24-hour window)
- `<InstructionRow>` — single instruction with ack badge

#### 5.2.7 Market

- `<MarketBidForm>` — form for stub bid submission, validates hour 1..24, volume, price
- `<BidHistory>` — table of bids with state column
- `<RevenueSplit>` — donut chart of revenue by channel (RDN/VDR/BR/DD/ANC)

#### 5.2.8 Reports

- `<ReportCard>` — preview card with title + period + sign button or `<KEPSignBadge>` (depending on `status`)
- `<KEPSignBadge>` — renders the badge per §3.6.3 exactly:
  ```
  ┌─────────────────────────────────────────────────────┐
  │  ✓ Підписано КЕП          [DEMO]                    │
  │  Іваненко І.І.  · ЄДРПОУ 12345678                    │
  │  АЦСК: Дія  · 2026-05-23T14:32:11+03:00              │
  │  SHA-256: 9f3a8b21…d71c40af                          │
  └─────────────────────────────────────────────────────┘
  ```
  Inline `DEMO` watermark mandatory (HLA R6).

#### 5.2.9 Scenarios

- `<ScenarioCard>` — used on `/c-i/` and `/storage/` home pages (BRIEF §11.27 POLISH). Three flavours per persona, e.g. for `/c-i/`:
  - "Захист від відключення"
  - "Захист від небалансу"
  - "Арбітражна можливість"

#### 5.2.10 Command Palette

- `<CommandPalette>` (`Ctrl+K`/`Cmd+K`) — services BRIEF §11.7. Linear-style. Uses `cmdk` library. Two sections:
  - Navigation: every persona surface URL with Ukrainian label
  - Actions: "Подати прогноз", "Подати заявку РДН", "Запустити оптимізацію", "Підписати звіт", "Перейти до /admin/engage", "Переключити тему", "Переключити мову"
- On `Enter` → router push or action invocation. (Mitigates HLA FMEA "Cmd+K opens but Enter doesn't fire".)

#### 5.2.11 Agents

- `<AgentChat>` — drawer from right. Header shows persona name. Input area + bubble list. Each response bubble shows `<EvidenceChips>` linking to underlying DB rows (renders as router links to the surfaced row).
- `<VoiceSession>` — overlay shown when push-to-talk active. Renders waveform (canvas). Listens to `<VoiceButton>` press-and-hold.

#### 5.2.12 Dev portal

- `<OpenAPIExplorer>` — wraps Scalar's `<ApiReferenceReact>` component. Reads `/packages/openapi/openapi.json` at build time (committed alongside the spec).

### 5.3 Routing

#### 5.3.1 Server vs client components

- **Server by default** — every persona surface root page is a server component, fetches initial data server-side via the `/api/*` proxy.
- **"use client"** only for: `<CommandPalette>`, `<AgentChat>`, `<VoiceSession>`, `<TenantSwitcher>` (uses cookie write), `<ThemeToggle>`, `<ArchitectureDiagram>` (animations), `<AssetDrawer>`, every chart wrapper.

#### 5.3.2 Loading and error states

Each persona surface ships `loading.tsx` and `error.tsx`:
- `loading.tsx` — skeleton tiles matching the page shape (KPI grid → 6 skeleton tiles; charts → skeleton bars).
- `error.tsx` — Ukrainian error message + retry button + link to `/about/credentials`.

#### 5.3.3 Persona-stratified URLs (recap)

- `/` (PersonaPicker + ArchitectureDiagram)
- `/producer/` (9 surfaces — full)
- `/c-i/` (5 surfaces: home, aktyvy, prognozy, rynok, zvity)
- `/storage/` (5 surfaces: home, aktyvy, uze, rynok, zvity)
- `/developer/` (6 sub-pages)
- `/admin/` (3 sub-pages)
- `/about/credentials` (stub disclosure)

#### 5.3.4 The 5-of-9 cut for `/c-i/` and `/storage/`

Per BRIEF §11.5: "at minimum: home, активи, прогнози, ринок, звіти". Locked here. Frontend lead does not need to re-decide. Other 4 (dyspetcheryzatsiya, uze, spovishchennya, nalashtuvannya) are not present on these personas; commands targeting them in the palette are filtered out per current persona.

### 5.4 State management

- **TanStack Query (v5)** for server state — auto cache, stale-while-revalidate. Default `staleTime: 60_000` matches the cache headers in §4.11.
- **Zustand** for client-only state: theme, palette open/closed, voice session active, currently-selected tenant (optimistic UI before cookie write completes).
- **No Redux.** No Context API beyond Next's built-in.

### 5.5 i18n

- Ukrainian everywhere. No EN toggle in UI (BRIEF §12 forbids multi-language).
- Strings live in `apps/web/lib/i18n/uk.json`. A `<T id="kpi.grn_saved">` component exists for the rare case where dynamic interpolation is needed; most strings are inline UA since translation is not a real need.
- Number formatting: `Intl.NumberFormat('uk-UA', ...)` for currency and decimals.
- Date formatting: ISO 8601 + Europe/Kyiv. Helper `lib/format-uah.ts` and `lib/format-date.ts`.

### 5.6 PWA shell

- `manifest.webmanifest` lists the 3 persona icon entries.
- Service worker (workbox via `next-pwa` or hand-rolled — frontend lead picks) caches the chrome + last fetched API responses for offline-friendly chrome.
- No offline-first behaviour for mutations.

### 5.7 Performance budget

Per HLA §10.5 refined:
- `/` — 1.5s LCP on cold cache
- `/producer/`, `/c-i/`, `/storage/` (home) — 1.5s LCP
- `/producer/aktyvy/`, `/producer/rynok/` — 2.0s LCP (denser data)
- `/developer/api/explorer` — 2.0s (Scalar bundle is heavy)
- `/admin/*` — 2.0s

CI runs Lighthouse on the deploy preview; budget overruns warn but do not block in v2 (specialist test lead may upgrade to blocking later).

---

## 6. Backend architecture

### 6.1 App layout

`apps/api/app/main.py`:

```python
# pseudo-code, not implementation
app = FastAPI(
    title="GECKO VPP API",
    version="1.0.0",
    openapi_version="3.1.0",
    docs_url=None,   # we serve Scalar in frontend; FastAPI docs disabled in prod
    redoc_url=None,
)

app.include_router(core.routers.auth.router,           prefix="/api/v1/auth",       tags=["auth"])
app.include_router(core.routers.assets.router,         prefix="/api/v1/assets",     tags=["assets"])
app.include_router(market.routers.aggregate.router,    prefix="/api/v1/market",     tags=["market"])
app.include_router(dispatch.routers.aggregate.router,  prefix="/api/v1/dispatch",   tags=["dispatch"])
app.include_router(ems.routers.aggregate.router,       prefix="/api/v1/ems",        tags=["ems"])
app.include_router(regulatory.routers.aggregate.router,prefix="/api/v1/regulatory", tags=["regulatory"])
app.include_router(agents.routers.aggregate.router,    prefix="/api/v1/agents",     tags=["agents"])
app.include_router(admin.routers.aggregate.router,     prefix="/api/v1/admin",      tags=["admin"])
```

### 6.2 DB session and RLS injection

`apps/api/app/db.py`:

- `asyncpg` connection pool, lifespan-managed.
- A FastAPI dependency `get_db_conn(tenant_id: UUID = Depends(tenant_dep), is_admin: bool = Depends(admin_dep))`:
  1. Acquires a connection from the pool.
  2. Issues `SET LOCAL app.tenant_id = $1` (parameterised).
  3. If `is_admin` → `SET LOCAL app.is_admin = 'true'`.
  4. Yields the connection inside a transaction.
  5. On exit, transaction commits or rolls back; `SET LOCAL` is auto-scoped to the transaction.

**Critical:** `SET LOCAL` only applies within a transaction. So every request opens a transaction. Read-only endpoints commit at end; mutating endpoints either commit or roll back on error.

`tenant_dep` reads `X-Tenant-Id` header. Missing header → 400 `MISSING_TENANT_HEADER`.
`admin_dep` reads `X-Admin: true` header AND verifies request path matches `^/api/v1/admin/`.

### 6.3 Module pattern (HLA D11 enforcement)

Each sub-system module follows this layout:

```
app/<module>/
├── __init__.py          # exports nothing
├── public.py            # the ONLY surface other modules may import
├── routers/             # FastAPI routers
├── services/            # business logic
├── repositories/        # SQL (async, parameterised)
└── schemas/             # Pydantic v2 models
```

Cross-module imports forbidden EXCEPT:
1. Any module may import from `app.core.public`.
2. A module may import from `app.<other>.public`, NOT from `app.<other>.services/repositories/schemas`.

### 6.4 import-linter contract

`apps/api/importlinter.cfg`:

```ini
[importlinter]
root_package = app

[importlinter:contract:layered]
name = Sub-system layering
type = layers
layers =
    app.agents
    app.regulatory
    app.ems
    app.dispatch
    app.market
    app.core
ignore_imports =
    app.* -> app.core.public
    app.* -> app.audit.public

[importlinter:contract:public_interface]
name = Only public interfaces may cross module boundary
type = forbidden
source_modules =
    app.market.*
    app.dispatch.*
    app.ems.*
    app.regulatory.*
    app.agents.*
forbidden_modules =
    app.market.services
    app.market.repositories
    app.market.schemas
    app.dispatch.services
    app.dispatch.repositories
    app.dispatch.schemas
    app.ems.services
    app.ems.repositories
    app.ems.schemas
    app.regulatory.services
    app.regulatory.repositories
    app.regulatory.schemas
    app.agents.services
    app.agents.repositories
    app.agents.schemas
allow_indirect_imports = false
```

CI runs `lint-imports` on every PR; failures block merge.

### 6.5 Admin cross-tenant decorator

`apps/api/app/core/security.py` exposes:

```python
def cross_tenant(fn):
    """Marks endpoint as intentionally cross-tenant.
    Sets app.is_admin='true' for the request transaction.
    Emits audit.events row at decorator invocation."""
    ...
```

Every router under `/api/v1/admin/*` uses `@cross_tenant` on each endpoint. No endpoint outside that prefix may use it (enforced via grep test in CI).

### 6.6 Optimisation runner (BRIEF §11.14)

`app/ems/optimiser/runner.py`:

- Function `run_optimisation(scenario, horizon_hours, asset_ids, tenant_id) -> OptimisationResult`.
- Pure Python, no Celery.
- Deterministic: hash of inputs (`scenario || sorted(asset_ids) || horizon_hours || current_day_yymmdd`) seeds an `random.Random(seed)`.
- Reads from `core.assets`, `market.rdn_prices` for the next horizon hours, `dispatch.telemetry` for current state.
- Applies a per-scenario perturbation function (arbitrage favours discharge in top-decile-price hours, charge in bottom-decile; curtailment_hedge nudges setpoints down on next forecast-curtailment day; etc.).
- Returns within 2 seconds on synthetic data scale (5–10 ms typical).
- Writes a row to `ems.optimisation_runs` for replay.

### 6.7 OpenAPI generation

- FastAPI emits OpenAPI 3.1 at runtime via `app.openapi()`.
- CI step (`apps/api/scripts/dump_openapi.py`) starts FastAPI in test mode, calls `app.openapi()`, writes to `packages/openapi/openapi.json`.
- CI commits this JSON to the repo on `main` (auto-PR if changed).
- SDK builds (`packages/sdk-ts`, `packages/sdk-py`) consume the committed JSON.
- Scalar UI in `/developer/api/explorer` reads the same committed JSON (so the dev portal always reflects the same version as the published SDKs).
- **Lint:** `spectral lint packages/openapi/openapi.json -r .spectral.yaml` runs in CI. Rules: every operation has `operationId`; every operation has at least one tag; every 4xx response is one of the canonical error codes (§4.1); every monetary field has unit suffix.

### 6.8 Error handling

`app/core/exceptions.py`:

```python
class GeckoError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "Internal server error"

class InvalidTenant(GeckoError): code = "INVALID_TENANT"; http_status = 400
class NotFound(GeckoError):       code = "NOT_FOUND";        http_status = 404
class ValidationFailed(GeckoError): code = "VALIDATION_FAILED"; http_status = 422
class StubNotImplemented(GeckoError): code = "STUB_NOT_IMPLEMENTED"; http_status = 501
```

A FastAPI exception handler wraps all `GeckoError` subclasses into the envelope.

---

## 7. AI agents architecture

### 7.1 Classifier

`app/agents/classifier.py`:

- **Mechanism:** pattern table + lexicon (per HLA §10.3 — no embeddings, no LLM).
- Implementation: a list of `(regex_pattern, intent, persona_whitelist, confidence_baseline)` tuples evaluated in priority order. A small lexicon (`dict[str, str]`) normalises common synonyms ("прогноз" ↔ "прогнозу" ↔ "forecast" → token `FORECAST_VERB`).
- Fallback intent: `unknown_intent` with confidence `0.0` → returns a safe response: "Я можу допомогти з: <list of 5 sample questions for the persona>". Mitigates HLA R5.

### 7.2 Intent vocabulary

12 intents total, distributed across 4 personas:

| Intent code | Question family example (UA) | Personas |
|---|---|---|
| `today_production`         | "що сьогодні з виробництвом?"           | dispatcher_analyst, energy_advisor |
| `next_imbalance_window`    | "коли наступний небаланс?"              | dispatcher_analyst, market_analyst |
| `arbitrage_window_today`   | "коли найкраще вікно арбітражу?"        | market_analyst, battery_coach |
| `charge_battery_when`      | "коли заряджати батарею?"               | battery_coach, energy_advisor |
| `deep_discharge_ok_today`  | "сьогодні підходить для глибокого розряду?" | battery_coach |
| `top_revenue_yesterday`    | "хто приніс найбільше доходу вчора?"     | market_analyst |
| `curtailment_today`        | "чи були обмеження сьогодні?"            | dispatcher_analyst |
| `forecast_accuracy_today`  | "яка точність прогнозу сьогодні?"        | dispatcher_analyst, energy_advisor |
| `next_settlement_due`      | "коли наступне закриття розрахунків?"   | market_analyst |
| `flex_savings_potential`   | "скільки можна зекономити через гнучкість?" | energy_advisor |
| `asset_status_overview`    | "покажи стан активів"                   | all |
| `generate_report_today`    | "сформуй звіт за сьогодні"              | all |

Each intent has:
- A SQL template (parameterised on `tenant_id`, `now`, `asset_id?`)
- A Jinja2 template per persona that fills in numbers + persona voice
- An evidence-shape spec: which tables/rows are surfaced

**Gold-set test fixture** (HLA R5 mitigation): `apps/api/tests/fixtures/agent_gold_set.json` holds 30 questions (per persona ~7–8) with expected intent + expected confidence ≥ 0.7. CI test `test_agent_classifier_gold_set` blocks merge on failure.

### 7.3 Personas

`app/agents/personas/<persona>.py` — each defines:

```python
PERSONA = {
    "code": "dispatcher_analyst",
    "display_name": "Диспетчерський аналітик",
    "greeting": "Я — Диспетчерський аналітик. Допоможу з виробництвом, диспетчеризацією, прогнозами.",
    "voice": "formal",   # 'formal' | 'coach' | 'peer'
    "allowed_intents": [
        "today_production", "next_imbalance_window", "curtailment_today",
        "forecast_accuracy_today", "asset_status_overview", "generate_report_today",
    ],
    "default_url": "/producer/",
}
```

When a user is on `/c-i/*`, the launcher uses `energy_advisor`; on `/storage/*` — `battery_coach`; on `/producer/*` — toggleable between `dispatcher_analyst` and `market_analyst` via a small switcher inside `<AgentChat>`.

### 7.4 Templates

`app/agents/templates/<intent>__<persona>.j2` per intent×persona combination (only for whitelisted combinations).

Example `next_imbalance_window__dispatcher_analyst.j2`:

```
Найближче вікно небалансу: {{ event.date_ua }} {{ event.hour_start }}:00–{{ event.hour_end }}:00.
Очікуваний небаланс ≈ {{ event.imbalance_mwh }} МВт·год по об'єкту «{{ event.asset_name }}».
Ризик: ціна дефіциту {{ event.price_short_uah_mwh }} грн/МВт·год.
```

### 7.5 Voice agent contract

`app/agents/routers/voice.py` exposes `GET /api/v1/agents/voice/session` (§4.8).

Server-side switch based on env:
```python
VOICE_PROVIDER = settings.voice_provider  # 'stub' | 'openai-realtime'
```

**Stub provider (default):**
- Frontend `<VoiceButton>` records audio via MediaRecorder, sends to browser Web Speech API STT (`SpeechRecognition` with `lang='uk-UA'`).
- Transcript sent to `/api/v1/agents/{persona}/query`.
- Response text spoken via `speechSynthesis.speak(new SpeechSynthesisUtterance(text))` with `voice = uk-UA` if available.
- **Firefox/Safari fallback** (no Web Speech API or no `uk-UA` voice): `<VoiceSession>` falls back to text-only — input field appears, response is text-only. Banner: "Голосовий режим недоступний у вашому браузері."

**OpenAI Realtime provider (opt-in):**
- Backend reads `OPENAI_API_KEY` from env. If absent at startup, `VOICE_PROVIDER` is forced to `stub` regardless of config (defensive).
- Server returns ephemeral session token (issued via OpenAI's session endpoint) + `websocket_url`.
- Frontend opens WebSocket directly to OpenAI, audio bi-directional. Same `<VoiceButton>` interface.

This satisfies user hard constraint "no paid API spend without explicit OPENAI_API_KEY".

---

## 8. SDK contracts

### 8.1 TypeScript SDK — `@gecko-vpp/sdk`

- Package name: **`@gecko-vpp/sdk`** on npm.
- Build: `tsup` produces ESM + CJS + `.d.ts`.
- Generated types: `openapi-typescript packages/openapi/openapi.json --output packages/sdk-ts/src/generated/api.ts`.
- Public API:
  ```typescript
  import { GeckoVPPClient } from '@gecko-vpp/sdk';
  const client = new GeckoVPPClient({ baseUrl, tenantId, apiKey? });

  await client.market.rdn({ date: '2026-05-12' });
  await client.assets.list({ asset_class: 'СЕС' });
  await client.agents.query('dispatcher_analyst', { text: 'коли наступний небаланс?' });
  ```
- Three quickstart examples (`/developer/sdk-ts/` page):
  1. List assets and print portfolio summary
  2. Fetch РДН prices for last 7 days and find capped hours
  3. Submit a forecast stub and poll for ACK
- Publishing: `pnpm publish` on tag `sdk-ts-v*`. Manual gate (Backend lead approves).

### 8.2 Python SDK — `gecko-vpp`

- Package name: **`gecko-vpp`** on PyPI (PyPI does not allow `@scoped` names).
- Build: `openapi-python-client generate --path packages/openapi/openapi.json --output packages/sdk-py/gecko_vpp/generated`.
- Public API:
  ```python
  from gecko_vpp import GeckoVPPClient
  client = GeckoVPPClient(base_url=..., tenant_id=..., api_key=None)

  async with client:
      prices = await client.market.rdn(date="2026-05-12")
      assets = await client.assets.list(asset_class="СЕС")
      answer = await client.agents.query("dispatcher_analyst", text="...")
  ```
- Three quickstart examples (`/developer/sdk-py/`):
  1. Same as TS-1 in Python
  2. Same as TS-2
  3. Same as TS-3
- Publishing: `uv publish` on tag `sdk-py-v*`. Manual gate.

### 8.3 SDK examples are tested in CI

Both SDK example scripts run against the local FastAPI during CI (`pytest --sdk-examples`). Failure blocks merge (HLA R9 mitigation).

---

## 9. Security model

### 9.1 Mock authentication

- The only "credential" is knowledge of one of the 3 demo tenant UUIDs (or one of the 3 tenant `code`s like `producer-1`).
- Browser stores `gecko_tenant_id` cookie (HttpOnly, Secure, SameSite=Lax). Next.js route handlers read it and forward as `X-Tenant-Id` to FastAPI.
- No password, no OAuth, no JWT. PRODUCT_BRIEF §12 forbids real auth.

### 9.2 RLS as the credible isolation story

- Every domain table has RLS enabled (§3.9).
- The DB role `gecko_api` has `NOBYPASSRLS`. The FastAPI process literally cannot SELECT from another tenant's data without `app.tenant_id` being set.
- **The §11.13 "no-code-change data swap" claim** depends on this — a real customer load happens via SQL INSERTs against the same schema; the application code remains unchanged.

### 9.3 Dev portal exposure

- `/developer/api/explorer` shows the OpenAPI spec including request/response shapes for every endpoint.
- It does NOT include a working `X-Tenant-Id`. Visitors can read the schema; they cannot mutate the demo's data without knowledge of one of the 3 tenant UUIDs (which are stable but not advertised in plain text).
- A bold disclaimer at the top of `/developer/`: "Demo environment. Mock tenants. Не для прод-середовища."

### 9.4 Caddy

- Snippet `infra/caddy/gecko-api.caddy`:
  ```caddy
  api.gecko.radai-1984.dev {
      reverse_proxy localhost:8000 {
          header_up X-Real-IP {remote_host}
          header_up X-Forwarded-For {remote_host}
          header_up X-Forwarded-Proto {scheme}
      }
      rate_limit {
          zone gecko_api {
              key {remote_host}
              events 100
              window 1m
          }
      }
      header {
          # CORS — restricts who can call from a browser
          Access-Control-Allow-Origin "https://gecko.radai-1984.dev"
          Access-Control-Allow-Headers "Content-Type, X-Tenant-Id, X-Admin"
          Access-Control-Allow-Methods "GET, POST, PATCH, DELETE, OPTIONS"
          Access-Control-Max-Age "3600"
      }
      log {
          format json
          output file /var/log/caddy/gecko-api.log
      }
  }
  ```
- Cloudflare in front: proxied A record. Transform Rule explicitly forwards `X-Tenant-Id` (HLA R3 mitigation).

### 9.5 Rate limiting

- Caddy: 100 req/min per IP for `/api/*`.
- Application-level: agent endpoints have an extra 30 req/min per tenant (audit-logged on excess).

### 9.6 CORS

- Allow-list: `https://gecko.radai-1984.dev`, `http://localhost:3000`, `http://localhost:3001`.
- No wildcards.

### 9.7 Secrets

- `.env.example` in repo with safe defaults and inline comments.
- Real `.env` on VPS only, ownership `root:gecko`, mode `0640`.
- No secret committed.
- Cloudflare token: NOT in this project's repo — uses existing `~/.cloudflare/api-token` via DevOps scripts only (memory `reference_cloudflare_api_token.md`).

### 9.8 SQL injection

- All SQL parameterised through `asyncpg` `$1`/`$2`/... placeholders.
- No string concatenation of SQL anywhere. ESLint-like grep in CI for `f"SELECT"` and `f"INSERT"` blocks merge.

### 9.9 XSS

- React's default escape is sufficient. No `dangerouslySetInnerHTML` outside the Scalar wrapper (which itself escapes).

### 9.10 No file upload anywhere in v2

Eliminates one whole risk class. Anywhere a stub upload UI exists (e.g., `/c-i/nalashtuvannya/`), it is `<input type="file" disabled>` with helper text "Demo: upload не активний у v2".

---

## 10. Testing strategy

### 10.1 Smoke tests (BRIEF §11.24)

**Tool:** Playwright (`@playwright/test`).
Test file: `apps/web/tests/smoke.spec.ts`.

Scenarios:
1. Every persona surface URL returns 200 and renders without console errors:
   - `/`, `/producer/`, `/producer/aktyvy/`, `/producer/prognozy/`, `/producer/dyspetcheryzatsiya/`, `/producer/rynok/`, `/producer/uze/`, `/producer/spovishchennya/`, `/producer/zvity/`, `/producer/nalashtuvannya/`
   - `/c-i/`, `/c-i/aktyvy/`, `/c-i/prognozy/`, `/c-i/rynok/`, `/c-i/zvity/`
   - `/storage/`, `/storage/aktyvy/`, `/storage/uze/`, `/storage/rynok/`, `/storage/zvity/`
   - `/developer/`, `/developer/api/explorer`, `/developer/sdk-ts/`, `/developer/sdk-py/`, `/developer/webhooks/`, `/developer/auth/`
   - `/admin/engage/`, `/admin/operate/`, `/admin/analyze/`
   - `/about/credentials`
2. Both themes render correctly on `/producer/`, `/c-i/`, `/storage/`, `/admin/engage/` (`data-theme` swap → no FOUC, no unstyled component, no contrast violation flagged by axe-core).
3. Tenant switcher: open switcher on `/producer/`, switch to ci-1, assert data on home tile changed.
4. Command palette: `Ctrl+K` opens; type "акти"; press Enter; assert URL changes to `/producer/aktyvy/`.
5. КЕП sign: on `/producer/zvity/`, click sign button on first report card; assert `<KEPSignBadge>` appears with DEMO watermark.

CI runs smoke against deploy preview on every PR.

### 10.2 Unit tests

**Backend** (`apps/api/tests/unit/`):
- pytest + pytest-asyncio.
- Coverage:
  - Every intent classifier SQL template returns expected shape on golden fixtures.
  - Every Pydantic schema round-trips JSON.
  - Optimiser determinism: same inputs → same `inputs_hash` → same `recommendations`.
  - КЕП stub: SHA-256 hash is real (not random); other fields are stubbed.
  - Forecast-submission status auto-advances on read after time threshold.

**Frontend** (`apps/web/tests/unit/`):
- vitest + jsdom.
- Coverage:
  - Theme resolver returns correct token on light vs dark.
  - `format-uah.ts` formats `123456.78` → `123 456,78 грн` (UA locale).
  - Persona detector returns correct agent persona from URL prefix.

### 10.3 Integration tests

**Backend** (`apps/api/tests/integration/`):
- Spin up a test Postgres (testcontainers); run migrations; seed minimal data; assert endpoints return expected envelopes.
- RLS test: open two connections with different `app.tenant_id`, assert tenant A cannot SELECT tenant B's rows.
- Admin bypass test: with `app.is_admin='true'`, SELECT from `core.assets` returns all 24–36 rows.

### 10.4 Contract tests

- `spectral lint packages/openapi/openapi.json` — must pass.
- SDK builds from spec; build failure → CI fails.
- SDK example scripts run against local FastAPI; assertion that responses match advertised schemas.

### 10.5 Data coverage tests

`apps/synth/synth/sniff_test.py` — runs after seed:
- Generates `synth_coverage.md`.
- For each acceptance criterion needing data (§11.4, §11.11, §11.12, §11.19, §11.20, §11.21, §11.22, §11.27, §11.28 if shipped):
  - Asserts at least one matching row exists.
- Asserts every sniff invariant (cap-pinning consistency, EIC format, settlement = volume × tariff × VAT, etc.).
- Fails block deploy.

### 10.6 What NOT to test

- LLM accuracy (no real LLM in default config).
- Real KEP signature crypto (real crypto not present in v2).
- Real market connector behaviour.
- Browser-specific voice-API rendering on Safari iOS (we accept the text-only fallback).
- Lighthouse > budget — warning only, not blocking.

### 10.7 CI gate summary

| Gate | Tool | Blocks merge? |
|---|---|---|
| `pnpm typecheck` | tsc | yes |
| `pnpm lint` | ESLint (token rule, no-hex) | yes |
| `uv run lint-imports` | import-linter | yes |
| `uv run ruff check` | Ruff | yes |
| `uv run mypy` | mypy | yes |
| `pytest unit` | pytest | yes |
| `pytest integration` | pytest + testcontainers | yes |
| `playwright test smoke` | Playwright | yes |
| `spectral lint openapi` | Spectral | yes |
| `synth sniff_test` | custom | yes |
| `lighthouse` | Lighthouse CI | warn only |

---

## 11. FMEA (Failure Mode and Effects Analysis)

| # | Failure Mode | Cause | Effect | Detection | Recovery | Owner |
|---|---|---|---|---|---|---|
| F01 | Postgres connection pool exhausted | spike of concurrent agent queries | 500s on /api/* | FastAPI health check, Caddy 502 logs | restart container; raise `min_size`/`max_size` in pool config | Backend |
| F02 | FastAPI process OOM under synthetic load | unbounded telemetry query (no LIMIT) | container killed | Hetzner monitor; Caddy 502 | docker compose restart; add LIMIT 1000 to telemetry queries | Backend |
| F03 | Caddy reverse-proxy misconfig blocks /api/* | typo in Caddyfile snippet on deploy | every API call 404 | Smoke test step 1 fails; manual curl | revert snippet via `caddy reload` | DevOps |
| F04 | Vercel deploy fails with `@vercel/analytics` v2 + Next 16 | known regression | preview deploy never builds | Vercel build logs | pin `@vercel/analytics@~1.x` or omit | Frontend |
| F05 | DNS propagation delay for `api.gecko.radai-1984.dev` | TTL on stale CF record | frontend cannot reach API for ~5–10 min | Smoke test from CI runner; user reports | wait or lower TTL pre-cutover; backup direct-IP fallback for QA | DevOps |
| F06 | RLS policy missing on a new table | DB lead adds table without RLS migration | tenant data leak between switcher | RLS integration test in CI | revert migration; add policy; redeploy | DB |
| F07 | Synth generator non-deterministic | un-seeded random call slips in | CI flaky on coverage assertions | `synth_coverage.md` diff between two runs in CI | trace random call; route through seeded RNG | DB |
| F08 | Theme toggle leaves half-styled component | component uses literal hex | dark theme looks light in places | ESLint no-hex rule + visual smoke test diff | enforce rule; rewrite offending component | Frontend |
| F09 | Cmd+K opens but Enter doesn't navigate | `cmdk` keyboard handler regression | command palette unusable | Smoke test step 4 | fix handler binding; pin `cmdk` version | Frontend |
| F10 | Voice agent stub fails on Firefox (no `SpeechSynthesis.uk-UA`) | browser quirk | voice button looks broken | Smoke + manual cross-browser test | activate text-only fallback (§7.5) | Voice |
| F11 | Agent classifier misclassifies | new question outside gold-set | nonsense response | Gold-set test passes; user reports | add to gold set; refine intent regex; fallback `unknown_intent` already returns safe response | AI agents |
| F12 | OpenAPI spec drifts from implementation | endpoint renamed without spec dump | SDK build fails | CI dumps spec + diffs against committed | regenerate spec; auto-PR | Backend |
| F13 | КЕП-stub badge accidentally claims real signature | DEMO watermark missing | legal/credibility risk | Smoke test asserts DEMO text present on every `<KEPSignBadge>` | restore DEMO watermark; lock as required prop | Frontend |
| F14 | Cloudflare strips X-Tenant-Id | default header policy | every user sees demo-producer-1 | CF echo test in CI hitting public URL | add Transform Rule to allow `X-Tenant-Id`; fallback to `?tenant=` query | DevOps |
| F15 | Synth coverage report has ❌ | event injection mis-keyed (e.g. curtailment on wrong asset) | acceptance walk-through finds empty chart | `sniff_test.py` blocks deploy | fix synth event logic; reseed | DB |
| F16 | `dispatch.telemetry` partition missing | seed runs before partition migration | INSERT fails with "no partition" | Alembic order test | rerun `alembic upgrade head` first | DB |
| F17 | Postgres noisy-neighbor on Hetzner | n8n / zhytomyr / ses spike | gecko queries slow | docker stats; Caddy slow-log | container CPU/memory limits (2 CPU / 2 GB) in compose | DevOps |
| F18 | OPENAI_API_KEY accidentally committed | dev mistake | leaked key, possible spend | git-secrets pre-commit hook | rotate key; force-push only with permission | Security |
| F19 | Scalar bundle pushes `/developer/api/explorer` LCP > 2s | Scalar minor update | performance budget overrun (warn) | Lighthouse CI | lazy-load Scalar component below the fold; pin Scalar version | Frontend |
| F20 | Optimiser run > 2s on heavy scenario | unbounded loop | UI shows spinner indefinitely | `duration_ms` log | hard timeout 5s; return partial result with `risk_flags=['timeout']` | Backend |

---

## 12. Implementation plan (hand-off to specialist leads)

Phase 4 work-units. One unit ≈ 1 day of focused work for the named lead. Dependencies explicit.

### Phase 4.1 — DB schema + RLS + alembic skeleton

- **Owner:** DB lead.
- **Input:** §3 of this doc.
- **Output:** `apps/api/alembic/` with migrations 001–011 producing all schemas, tables, partitions, RLS policies, MVs.
- **Acceptance:** `alembic upgrade head` succeeds on fresh DB; integration test `test_rls_isolation` passes (two connections with different `app.tenant_id` see disjoint rows).
- **Estimated effort:** 1 unit.
- **Blocks:** 4.2, 4.3.

### Phase 4.2 — Synthetic data generator

- **Owner:** DB lead + Backend lead (joint).
- **Input:** §3.11, all three research files.
- **Output:** `apps/synth/` Python container that consumes `synth.yaml`, populates Postgres, emits `synth_coverage.md` + passes `sniff_test.py`.
- **Acceptance:** `docker compose run synth` populates DB; coverage report shows ✅ on every acceptance criterion listed in §3.11.2.
- **Estimated effort:** 2 units.
- **Blocks:** 4.4, 4.5, 4.6, 4.8.

### Phase 4.3 — FastAPI skeleton + first 5 endpoints

- **Owner:** Backend lead.
- **Input:** §4, §6 of this doc.
- **Output:** `apps/api/` FastAPI app with `core` module + 5 endpoints live: `GET /api/v1/auth/me`, `POST /api/v1/auth/switch-tenant`, `GET /api/v1/assets`, `GET /api/v1/market/rdn`, `GET /api/v1/ems/kpi/portfolio`.
- **Acceptance:** OpenAPI spec dumps to `packages/openapi/openapi.json`; smoke curl returns valid envelope for each; RLS visible (different `X-Tenant-Id` returns different data).
- **Estimated effort:** 2 units.
- **Blocks:** 4.4, 4.7.

### Phase 4.4 — Frontend chrome + hero / persona picker

- **Owner:** Frontend lead.
- **Input:** §5 of this doc.
- **Output:** Next.js app with `<AppShell>`, `<TopBar>`, `<TenantSwitcher>`, `<PersonaSwitcher>`, `<ThemeToggle>` working; `/` page renders `<PersonaPicker>` + `<ArchitectureDiagram>`.
- **Acceptance:** Theme toggle persists in localStorage; tenant switcher writes cookie; `/` renders ≤ 1.5s LCP; smoke test 1–3 pass.
- **Estimated effort:** 2 units.
- **Blocks:** 4.5, 4.6.

### Phase 4.5 — Producer surfaces (9 pages)

- **Owner:** Frontend lead.
- **Input:** §5 + §4 endpoints; depends on 4.2 data + 4.4 chrome + 4.3+4.7 endpoints.
- **Output:** All 9 `/producer/*` surfaces render real data.
- **Acceptance:** Smoke test 1 passes for all 9 routes; both themes render; KPI tiles show real numbers.
- **Estimated effort:** 3 units.
- **Blocks:** 4.6 (c-i, storage are mirrors).

### Phase 4.6 — C&I + Storage + Admin surfaces

- **Owner:** Frontend lead.
- **Input:** 4.5 done.
- **Output:** `/c-i/*` (5 pages), `/storage/*` (5 pages), `/admin/*` (3 pages).
- **Acceptance:** Smoke test 1 passes for all routes; cross-tenant data visible in `/admin/engage/`.
- **Estimated effort:** 2 units.

### Phase 4.7 — Full FastAPI coverage (every endpoint in §4)

- **Owner:** Backend lead.
- **Input:** §4 of this doc; 4.1 + 4.2 done.
- **Output:** Every endpoint in §4 implemented; OpenAPI complete; spectral lint passes.
- **Acceptance:** Contract tests pass; SDK build succeeds.
- **Estimated effort:** 3 units.

### Phase 4.8 — AI text agents

- **Owner:** AI agents lead.
- **Input:** §7 of this doc; 4.7 done.
- **Output:** Classifier + 12 intents + 4 personas + templates; gold-set test passes.
- **Acceptance:** `POST /api/v1/agents/{persona}/query` returns valid envelope with evidence for every gold-set question.
- **Estimated effort:** 2 units.

### Phase 4.9 — Voice agent (stub default + Realtime upgrade path)

- **Owner:** Voice agent lead.
- **Input:** §7.5 of this doc.
- **Output:** `<VoiceButton>` + `<VoiceSession>` working in stub mode; Realtime mode wired (untested without key).
- **Acceptance:** Voice button records, transcribes via Web Speech API, sends to text agent, plays response; fallback works in Firefox; env-var switch wired.
- **Estimated effort:** 1.5 units.

### Phase 4.10 — SDK builds (TS + Py)

- **Owner:** SDK lead (Backend lead doubles).
- **Input:** §8 of this doc; 4.7 done.
- **Output:** Two SDK packages buildable; example scripts in `/developer/sdk-{ts,py}/` runnable.
- **Acceptance:** `pnpm build` for sdk-ts and `uv build` for sdk-py both produce artefacts; example scripts pass against local API.
- **Estimated effort:** 1 unit.

### Phase 4.11 — Dev portal pages

- **Owner:** Frontend lead.
- **Input:** §5.2.12, §8; 4.10 done.
- **Output:** `/developer/*` pages, Scalar embed at `/developer/api/explorer`.
- **Acceptance:** Smoke test 1 passes for all `/developer/*`; Scalar renders OpenAPI; LCP < 2s.
- **Estimated effort:** 1 unit.

### Phase 4.12 — Testing harness

- **Owner:** Testing lead.
- **Input:** §10 of this doc.
- **Output:** Smoke test suite, unit-test scaffolds, gold-set fixture, sniff-test, Lighthouse CI.
- **Acceptance:** All CI gates in §10.7 wired; passing on main.
- **Estimated effort:** 1.5 units.

### Phase 4.13 — Security audit

- **Owner:** Security lead.
- **Input:** §9 of this doc.
- **Output:** RLS audit report, Caddy snippet reviewed, CORS verified, secrets check.
- **Acceptance:** All security-relevant gates green; no `BYPASSRLS` granted to `gecko_api`.
- **Estimated effort:** 0.5 unit.

### Phase 4.14 — Deploy

- **Owner:** DevOps lead.
- **Input:** §13 of this doc.
- **Output:** Hetzner VPS running docker-compose; Vercel project linked; Cloudflare DNS configured; smoke test passing on `gecko.radai-1984.dev`.
- **Acceptance:** Curl from CI runner hits both `gecko.radai-1984.dev` and `api.gecko.radai-1984.dev/openapi.json` and returns 200; smoke test full pass on prod URL.
- **Estimated effort:** 1 unit.

### Critical path

```
4.1 → 4.2 ──┬─→ 4.3 ──→ 4.7 ──┬─→ 4.8 ─┐
            │                   │        ├─→ 4.12 ─┐
            ├─→ 4.4 ──→ 4.5 ──→ 4.6      │         │
            │                              ├─→ 4.10 ─→ 4.11 ─┘
            │                              └─→ 4.9 ──────────┐
                                                              ├→ 4.13 → 4.14
```

Total: ~22 work-units. With parallelism across leads: ~10 calendar days.

---

## 13. Deployment topology

### 13.1 Vercel (frontend)

- Project name: `gecko-vpp-rebuild`
- Linked to GitHub repo `basisabp1984/gecko-vpp-rebuild` (public, MIT).
- Root directory: `apps/web/`
- Build command: `pnpm -F web build`
- Output directory: `.next`
- Branches: `main` → prod (`gecko.radai-1984.dev`); PRs → preview.
- Env vars on Vercel:
  - `NEXT_PUBLIC_API_BASE_URL=https://api.gecko.radai-1984.dev`
  - `NEXT_PUBLIC_DEMO_MODE=true`

### 13.2 Hetzner VPS

- Path: `/opt/gecko-vpp/`
- `docker-compose.yml` services:
  - `api` (FastAPI image, port 8000)
  - `postgres` (Postgres 16, port 5432 bound to localhost only; named volume `gecko_pg_data`)
  - `synth` (one-shot, `restart: no`, command `python -m synth`)
- Resource limits (HLA R1 mitigation):
  - postgres: `cpus: '2.0'`, `mem_limit: 2g`, `mem_reservation: 1g`
  - api: `cpus: '1.5'`, `mem_limit: 1g`
- Caddy on host (existing) gets `infra/caddy/gecko-api.caddy` snippet imported into the existing Caddyfile.
- Logs: stdout → Caddy + journalctl; rotate weekly via existing logrotate config.

### 13.3 DNS (Cloudflare)

Records to create:
- `gecko.radai-1984.dev` — CNAME to `cname.vercel-dns.com`, proxied=false (Vercel manages TLS).
- `api.gecko.radai-1984.dev` — A to `178.105.209.14`, proxied=true (Cloudflare TLS + rate limit).

Use existing token at `~/.cloudflare/api-token` (memory `reference_cloudflare_api_token.md`); zone id `f12805dc...`.

### 13.4 GitHub

- Repo: `basisabp1984/gecko-vpp-rebuild` — public, MIT.
- README: explains demo, screenshots, "Don't trust the КЕП — it's a stub", links to /developer/, dev portal, links to PRODUCT_BRIEF v0.4.
- `.gitignore`: `node_modules`, `.next`, `dist`, `__pycache__`, `*.pyc`, `.env`, `.env.local`, `synth_coverage.md` (generated).
- CI: GitHub Actions workflow `.github/workflows/ci.yml` runs all CI gates from §10.7.

### 13.5 Secrets and `.env.example`

`.env.example`:
```env
# Postgres
POSTGRES_USER=gecko_api
POSTGRES_PASSWORD=change_me
POSTGRES_DB=gecko
DATABASE_URL=postgresql+asyncpg://gecko_api:change_me@postgres:5432/gecko

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
API_LOG_LEVEL=info

# Voice
VOICE_PROVIDER=stub                      # 'stub' or 'openai-realtime'
OPENAI_API_KEY=                          # required only if VOICE_PROVIDER=openai-realtime

# Synth
SYNTH_RNG_SEED=20260523
SYNTH_WINDOW_START=2026-04-23
SYNTH_WINDOW_END=2026-05-23

# Frontend (Vercel)
NEXT_PUBLIC_API_BASE_URL=https://api.gecko.radai-1984.dev
NEXT_PUBLIC_DEMO_MODE=true
```

### 13.6 Deploy sequence (runbook for DevOps)

1. Create Cloudflare DNS records (A + CNAME).
2. SSH to Hetzner; `git clone` repo into `/opt/gecko-vpp/`.
3. Copy `.env.example` → `.env`; fill passwords.
4. Append Caddy snippet to existing Caddyfile; `caddy reload`.
5. `docker compose up -d postgres`; wait for healthy.
6. `docker compose run --rm api alembic upgrade head`.
7. `docker compose run --rm synth python -m synth` (one-shot; emits coverage report).
8. Verify `synth_coverage.md` shows all ✅.
9. `docker compose up -d api`.
10. Verify `curl https://api.gecko.radai-1984.dev/openapi.json` returns 200.
11. Push frontend repo; Vercel builds and deploys to preview.
12. Promote preview to prod after smoke test passes.
13. Update PROGRESS.md with deploy timestamp.

---

## 14. Hand-off to specialist leads

Each specialist lead must write their `*_INSTRUCTIONS.md` document covering the sections listed below. Each must verify the 5–10 item checklist before declaring their phase done.

### 14.1 DB lead — `BACKEND_DB_INSTRUCTIONS.md`

- **Owns:** §3 (entire data model), §3.11 (synth generator), §10.5 (data coverage tests).
- **Deliverable:** alembic migrations 001–011 + `apps/synth/` skeleton.
- **Checklist:**
  - [ ] All 7 schemas created in `001_init_schemas.py`
  - [ ] Every domain table has `tenant_id UUID NOT NULL` (or is the cross-tenant `regulator_events`)
  - [ ] RLS enabled and `tenant_isolation_*` policy attached to every domain table
  - [ ] `gecko_api` role has `NOBYPASSRLS`
  - [ ] `dispatch.telemetry` partitioned by month with partitions for 2026-04 and 2026-05
  - [ ] All `interval_start` columns derived from `(date, hour)` via GENERATED ALWAYS AS
  - [ ] Every EIC column is `CHAR(16)` with a check constraint regex
  - [ ] `synth.yaml` schema documented; RNG seed locked at `20260523`
  - [ ] `sniff_test.py` covers all invariants in §3.11.5
  - [ ] `synth_coverage.md` generation step wired into CI

### 14.2 Backend lead — `BACKEND_INSTRUCTIONS.md`

- **Owns:** §4 (all endpoints), §6 (FastAPI + module + import-linter), §11 (FMEA F01, F02, F12, F20).
- **Deliverable:** FastAPI app with every endpoint in §4 implemented, OpenAPI spec emitted and lintable, import-linter contract enforced.
- **Checklist:**
  - [ ] All routers registered in `main.py`
  - [ ] `get_db_conn` dependency sets `SET LOCAL app.tenant_id` per request
  - [ ] `@cross_tenant` decorator only used under `/api/v1/admin/*` (CI grep enforces)
  - [ ] `importlinter.cfg` runs in CI, blocks merge on violation
  - [ ] OpenAPI spec dumps in CI to `packages/openapi/openapi.json`; auto-PR on diff
  - [ ] Spectral lint passes
  - [ ] All endpoints return canonical envelope (success or error)
  - [ ] Optimiser runs in < 2 s on synthetic data; deterministic on same inputs
  - [ ] Forecast-submission status auto-flips on read (no worker)
  - [ ] КЕП stub endpoint sets `is_demo_stub=TRUE` on insert

### 14.3 Frontend lead — `FRONTEND_INSTRUCTIONS.md`

- **Owns:** §5 (entire frontend), §11 FMEA frontend rows (F04, F08, F09, F13, F19).
- **Deliverable:** Next.js app with all 29 routes (or whichever subset is on the implementation plan), token-driven theming, command palette, agent chat, slide-7 diagram.
- **Checklist:**
  - [ ] CSS-var token system defined in `tokens.css`; ESLint no-hex rule enforced
  - [ ] `<html data-theme=...>` switched server-side via inline script before hydration; no FOUC
  - [ ] All 9 producer surfaces routes live + 5 c-i + 5 storage + 3 admin + 6 developer
  - [ ] `<ArchitectureDiagram>` is interactive SVG with hover animations + click-nav
  - [ ] `<CommandPalette>` works on `Ctrl+K`/`Cmd+K`; Enter fires
  - [ ] `<KEPSignBadge>` always renders DEMO watermark
  - [ ] TanStack Query for server state; Zustand for client state; no Redux
  - [ ] Lighthouse budgets per §5.7 met (warn-only)
  - [ ] Smoke tests in `apps/web/tests/smoke.spec.ts` all pass

### 14.4 AI agents lead — `AI_AGENTS_INSTRUCTIONS.md`

- **Owns:** §7.1–§7.4.
- **Deliverable:** classifier + 12 intents + 4 personas + Jinja templates + gold-set fixture.
- **Checklist:**
  - [ ] 12 intent codes implemented per §7.2 table
  - [ ] Each intent has SQL template (parameterised, RLS-safe)
  - [ ] Each persona × allowed-intent has a Jinja2 template
  - [ ] Fallback intent `unknown_intent` returns Ukrainian safe response
  - [ ] Gold-set test fixture has 30 questions; CI test `test_agent_classifier_gold_set` passes
  - [ ] Evidence chips link to real DB rows
  - [ ] No LLM API call anywhere; no `sentence-transformers` dependency
  - [ ] Response time < 100 ms p95 on synthetic data

### 14.5 Voice agent lead — `VOICE_AGENT_INSTRUCTIONS.md`

- **Owns:** §7.5.
- **Deliverable:** `<VoiceButton>`, `<VoiceSession>`, `/api/v1/agents/voice/session` endpoint, both stub and Realtime paths.
- **Checklist:**
  - [ ] Default deploy uses `VOICE_PROVIDER=stub`
  - [ ] OpenAI Realtime path activates only when both `VOICE_PROVIDER=openai-realtime` and `OPENAI_API_KEY` set
  - [ ] No API call to OpenAI happens unless the user explicitly clicks the voice button AND the key is present
  - [ ] Web Speech API STT works on Chrome desktop (uk-UA)
  - [ ] Fallback to text-only on Firefox / Safari iOS gracefully
  - [ ] 5 canned scenarios cover §4.8 list
  - [ ] User-facing banner explains demo mode in stub provider

### 14.6 SDK lead — `SDK_INSTRUCTIONS.md`

- **Owns:** §8.
- **Deliverable:** `@gecko-vpp/sdk` (npm) + `gecko-vpp` (PyPI) buildable; 6 example scripts (3 per language).
- **Checklist:**
  - [ ] Both SDKs generated from `packages/openapi/openapi.json`
  - [ ] `GeckoVPPClient` class has typed methods for every endpoint group
  - [ ] 3 quickstart examples each, tested against local FastAPI in CI
  - [ ] Manual publish gate (no auto-publish on tag without approval)
  - [ ] README in each package with install/import/example/license
  - [ ] No paid API keys shipped in examples

### 14.7 Security lead — `SECURITY_INSTRUCTIONS.md`

- **Owns:** §9, §11 FMEA security rows (F06, F14, F18).
- **Deliverable:** RLS audit, Caddy snippet review, CORS verified, secrets policy.
- **Checklist:**
  - [ ] `gecko_api` role is `NOBYPASSRLS`
  - [ ] Every domain table has RLS enabled and a tenant policy
  - [ ] Integration test proves cross-tenant SELECT returns empty
  - [ ] Caddy rate limit configured (100 req/min/IP)
  - [ ] CORS allow-list strict (only 3 origins)
  - [ ] `.env` not committed; `.env.example` documents all keys
  - [ ] git-secrets pre-commit hook installed
  - [ ] `/about/credentials` page lists every stubbed surface

### 14.8 Testing lead — `TESTING_INSTRUCTIONS.md`

- **Owns:** §10.
- **Deliverable:** smoke tests, unit tests, integration tests, contract tests, sniff tests, CI workflow.
- **Checklist:**
  - [ ] Playwright smoke covers all 29 routes
  - [ ] Both themes asserted on at least 4 representative routes
  - [ ] RLS isolation test in backend integration suite
  - [ ] Gold-set agent test in backend unit suite
  - [ ] SDK examples run in CI against local API
  - [ ] `sniff_test.py` blocks deploy on ❌
  - [ ] Lighthouse CI configured (warn-only)
  - [ ] CI pipeline runs in < 15 min on PR
  - [ ] Test data is the synth-generated dataset (no separate fixtures)

### 14.9 DevOps lead — `DEVOPS_INSTRUCTIONS.md`

- **Owns:** §13, §11 FMEA infra rows (F03, F05, F17).
- **Deliverable:** Hetzner deploy, Vercel deploy, DNS, GitHub repo public, CI workflow.
- **Checklist:**
  - [ ] Repo public at `basisabp1984/gecko-vpp-rebuild`, MIT license, README explains demo
  - [ ] Cloudflare A + CNAME records active
  - [ ] Caddy snippet imported; reload successful; cert auto-issued
  - [ ] docker-compose with resource limits on postgres + api
  - [ ] `alembic upgrade head` runs in deploy step
  - [ ] `synth` one-shot runs before api starts
  - [ ] Vercel project linked; preview deploy works on PR
  - [ ] Smoke test passes against `gecko.radai-1984.dev` and `api.gecko.radai-1984.dev`
  - [ ] Backup: nightly `pg_dump` to local volume `gecko_pg_backups/`, kept 7 days
  - [ ] v1 (`vpp.radai-1984.dev`) untouched and live

---

## 15. Self-review notes

After writing §0–§14 I re-read the entire document. Findings, with resolutions:

### 15.1 Contradictions found and fixed in this draft

- **§3.6.1 forecast-submission status flow vs BRIEF §12 "no background workers".** Resolved in §3.6.1: status auto-advances on READ based on `submitted_at` timestamp delta. No worker. Server-computed-on-read mechanism is the explicit lock.
- **§3.9 RLS for `regulator_events`.** Stage 1 said cross-tenant. This doc clarifies the policy: read-all, write-admin only. Consistent.
- **§5.3.4 5-of-9 cut.** Stage 1 left this as a "frontend specialist's call". I locked it here (home, aktyvy, prognozy, rynok, zvity for both c-i and storage; storage substitutes `uze/` for `prognozy/` per BRIEF §10 emphasis on storage SoC). Confirming alignment with BRIEF §11.5 minimum.
- **§3.6.3 КЕП sign workflow.** BRIEF §11.20 mentions settlement statement, report, contract — I cover all three by making `document_type` a CHECK constraint with those values + BID_PACKAGE + FORECAST_PACKAGE. §4.7 `POST /sign` endpoint accepts `{ref_table, ref_id}` pair, so any of the 5 table types can be signed.

### 15.2 Acceptance criteria coverage (§11 of BRIEF)

Walked through every §11.x:

- §11.1 brand + both themes → §5.1 token system ✅
- §11.2 tenancy → §3.2.1 + §4.2 ✅
- §11.3 slide-7 diagram → §5.2.2 ✅
- §11.4 all 9 surfaces → §2 repo layout + §5.2 components ✅
- §11.5 c-i + storage variants → §5.3.4 locked at 5 surfaces ✅
- §11.6 admin surfaces → §4.9 + §5.3.3 ✅
- §11.7 command palette → §5.2.10 ✅
- §11.8 sub-system separation → §6.3 + §6.4 import-linter ✅
- §11.9 API-first → §1.1 + §5.3.1 (no direct DB from frontend) ✅
- §11.10 Postgres holds data, no regenerate on restart → §13.2 (synth is one-shot) ✅
- §11.11 ENTSO-E codes → §3.2.3 + §3.2.4 + §3.6.1 ✅
- §11.12 Ukrainian asset names, грн, EET → §3.11.1 synth.yaml + format-uah ✅
- §11.13 sub-1-hour data swap → §3.9 RLS + §13 deploy is documented SQL insert ✅
- §11.14 optimiser separate process → §6.6 (FastAPI ≠ Next.js process) ✅
- §11.15 4 AI agents with evidence → §7 + §3.7.1 query_log ✅
- §11.16 voice agent → §7.5 + §4.8 ✅
- §11.17 SDKs → §8 ✅
- §11.18 public dev portal → §5.2.12 + §13.1 ✅
- §11.19 forecast submission → §3.6.1 + §4.5 ✅
- §11.20 КЕП stub → §3.6.3 + §4.7 + §5.2.8 ✅
- §11.21 single pane РДН/ВДР/БР/ДД → §4.3 endpoints ✅
- §11.22 CO₂ KPI → §3.5.2 kpi_daily.co2_avoided_tn + §5.2.3 KPIGrid ✅
- §11.23 onboarding stub → §2 repo (`/producer/nalashtuvannya/`) — covered by frontend lead checklist
- §11.24 smoke pass → §10.1 ✅
- §11.25 production-fidelity feel — performance budgets §5.7 ✅
- §11.26 research-summary closed — already done in v0.4 brief
- §11.27 POLISH scenario cards → §5.2.9 ✅
- §11.28 POLISH OBIS tariff zones → frontend lead's discretion (research §5 has the OBIS map; ship if time allows)
- §11.29 POLISH trusted-person invite → §3.2.2 has `core.users` skeleton; UI surface in nalashtuvannya
- §11.30 POLISH maintenance declaration → can add `dispatch.operator_adjustments` row with reason='planned_maintenance'; UI on aktyvy/[id]
- §11.31 POLISH ESG sub-tab → consume `kpi_daily.co2_avoided_tn` in `/producer/zvity/`

### 15.3 Places where a specialist may not know how to start

- **`<ArchitectureDiagram>` (§5.2.2)** — I gave node count, connection count, animation library, but not the exact node positions / connection paths. The frontend specialist needs the actual slide-7 PNG sampled for layout. Flagging in §14.3 checklist; recommend "sample slide-7 PNG from `source/01_GECKO_VPP_client_brief.pdf` page 7 before starting".
- **`<KEPSignBadge>` exact pixel layout** — described semantically but not as React component. Frontend lead extends.
- **Caddy rate limit module** — needs `caddy-ratelimit` plugin. Existing Hetzner Caddy might not have it. **DevOps must verify** in §14.9.
- **OpenAPI auto-PR mechanism** — described in §6.7 but specifics depend on whether the team uses GitHub Actions bot tokens. DevOps lead picks.

### 15.4 Punted decisions explicitly flagged

These are intentional "next stage decides" items:

- **Exact Manrope weights to self-host** (frontend lead — typography subsection of design tokens). Acceptable because: font choice is locked, only sub-pick weight subset.
- **Exact pixel positions of slide-7 nodes** (frontend lead — sample PDF). Acceptable because: requires visual judgement.
- **Exact signer fixture names** (DB lead — synth.yaml). Acceptable because: doesn't affect schema.
- **Whether to use `caddy-ratelimit` or upstream nginx-style sidecar** (DevOps). Acceptable because: implementation detail not affecting API contract.
- **Postgres backup retention window** (DevOps — §14.9 says 7 days; OK to extend if disk allows). Acceptable because: ops policy.
- **OBIS tariff zone overlay (§11.28 POLISH)** — frontend lead implements if time allows. Defer-OK.

### 15.5 Things I considered locking but did not

- **15-min telemetry for storage assets**. `research_asset_data_shape.md §3.7` allows specialist override for one asset class. I keep §3.4.2 telemetry at hourly across the board for simplicity; storage telemetry charts can still display SoC nicely at hourly resolution. Locked at hourly.
- **OpenAPI versioning policy beyond v1**. Locked at `/api/v1/*` for the demo; v2 is hypothetical and not in scope.
- **Webhooks live delivery**. §4.10 is documentation only — no live webhook delivery happens in v2 (BRIEF §12 forbids background workers). Locked.

### 15.6 Confidence

- **High confidence:** DDL, RLS, API contract envelope, design token system, sub-system module pattern, import-linter contract.
- **Medium confidence:** synth data realism (depends on care taken by DB+Backend leads against §3.11 + sniff tests), agent classifier coverage (depends on gold-set quality from AI agents lead).
- **Lower confidence (acknowledged):** Web Speech API behaviour cross-browser (Voice agent lead must verify in Firefox/Safari iOS); Lighthouse budgets on first deploy (Frontend lead iterates).

---

*End of ARCHITECTURE.md v0.1. Next: Stage 3 specialist leads draft their instructions in parallel.*
