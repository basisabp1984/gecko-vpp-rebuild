# ARCHITECTURE — Krytsia VPP + EMS

> A 10-minute orientation for an engineer about to click into the code.
> For the full 38-page deep dive see [`phase-3-architecture/ARCHITECTURE.md`](phase-3-architecture/ARCHITECTURE.md).

---

## 1. System overview

Krytsia is a production-fidelity demo of a Virtual Power Plant (VPP) +
Energy Management Platform (EMS) for the Ukrainian energy market. It
aggregates solar (СЕС), wind (ВЕС), gas (ГПУ) and storage (УЗЕ) assets
of multiple owner-tenants into one disciplined trading-and-dispatch
entity, and presents each owner a single screen for their generation,
storage, consumption and revenue.

The product is two deployments wired through one HTTPS hop:

```
Browser
  │
  ▼
Vercel Edge — Next.js 16 (krytsia.radai-1984.dev)
  │   server components, /api/* route handlers proxy to FastAPI,
  │   X-Tenant-Id injected from cookie
  ▼ HTTPS
Caddy (Hetzner VPS) ── reverse proxy, Let's Encrypt
  │   api.gecko.radai-1984.dev
  ▼ docker internal network (caddy_web)
FastAPI (gecko-api container)
  │   one process, seven routers, OpenAPI 3.1
  ▼ asyncpg + SET LOCAL app.tenant_id
Postgres 16 (gecko-postgres container)
  │   schemas: core / market / dispatch / ems / regulatory / agents / audit
  │   Row-Level Security on every tenant-scoped table
```

The frontend never touches Postgres directly. The backend is a single
process running seven Python modules; multi-tenancy is enforced by
Postgres RLS, not by Python code.

Data is **30 days of synthetic records** (2026-04-23 → 2026-05-23)
seeded once. Restarting any container never re-seeds; the seed step is
explicit (`python -m data_generator.main --reset`).

---

## 2. Three sub-systems (per client deck slide 6)

Inside FastAPI the code is laid out around the three sub-systems the
client deck names. Each is a Python package under
`apps/api/src/gecko_vpp/`:

| Sub-system | Code module(s) | Function |
|---|---|---|
| **Ринкова інтеграція** | `routers/market.py` | Bids and confirmations to РДН / ВДР / БР / ДД; ancillary; bilateral bookkeeping; revenue ledger |
| **Комерційна диспетчеризація** | `routers/dispatch.py` | Setpoints, telemetry ingest, instruction acks, operator overrides |
| **EMS (Програмна платформа)** | `routers/ems.py`, `routers/agents.py`, `agents_engine/` | Forecast, optimise, KPI engine, AI agents, report generator |

Cross-cutting routers: `core` (tenants, assets, auth), `regulatory`
(settlements, КЕП stub, regulator events), `admin` (cross-tenant
operator views).

Internal data flow: **EMS → Диспетчеризація → Ринкова інтеграція.**
Reverse signals (market prices, regulator notices) flow back into EMS.

---

## 3. Data model

### 3.1 Schemas

Seven Postgres schemas, created by migration `001_init_schemas.py`:

| Schema | Owns | Examples of what lives here |
|---|---|---|
| `core` | tenants, users, assets, EIC code lookups | `core.tenants`, `core.assets`, `core.eic_codes` |
| `market` | РДН / ВДР / БР / ДД, bids, ancillary | `market.rdn_prices`, `market.vdr_trades`, `market.br_settlements`, `market.bids` |
| `dispatch` | setpoints, telemetry, instructions | `dispatch.telemetry` (RANGE-partitioned by month), `dispatch.setpoints` |
| `ems` | forecasts, KPI, optimiser runs | `ems.forecasts`, `ems.kpi_daily`, `ems.optimisation_runs` |
| `regulatory` | submissions, settlements, КЕП-signed docs | `regulatory.forecast_submissions`, `regulatory.settlement_statements`, `regulatory.signed_documents` |
| `agents` | AI agent query log + cache | `agents.query_log`, `agents.response_cache` |
| `audit` | user-action / system-emission events | `audit.events` |

### 3.2 Key tables (the ones you will touch first)

- **`core.tenants`** — three rows for the demo (`producer-1`, `ci-1`,
  `storage-1`). Each has an 8-digit EDRPOU and a 16-char ENTSO-E
  participant EIC.
- **`core.assets`** — 24–36 rows total. Asset class is one of
  `СЕС / ВЕС / ГПУ / УЗЕ / АктСпож / Споживач`. Every asset has a
  16-char W-prefix resource EIC.
- **`core.eic_codes`** — ENTSO-E lookup. Includes the UA bidding-zone
  EIC `10Y1001C--00003F` plus all participant/resource/metering EICs.
- **`market.rdn_prices`** — 2,160 rows (3 tenants × 30 days × 24 hours).
  Cap-pinning modelled on ~40% of evenings.
- **`market.bids`** — bid history across all 4 markets.
- **`dispatch.telemetry`** — RANGE-partitioned by month
  (`telemetry_2026_04`, `telemetry_2026_05`). ~21,600 rows.
- **`ems.forecasts`** — two-stage (`primary` + `refined`) per asset,
  per hour, per forecast kind (`solar / wind / load / price`).
- **`regulatory.signed_documents`** — КЕП stub. Every emitted document
  (settlement, report, contract) gets one; `is_demo_stub = TRUE` always.

### 3.3 Row-Level Security

Every tenant-scoped table has RLS enabled and a policy like:

```sql
CREATE POLICY tenant_isolation ON market.rdn_prices
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

The application connects as the `gecko_api` role — explicitly
`NOBYPASSRLS`. On every request FastAPI does:

```sql
SET LOCAL app.tenant_id = '<uuid from X-Tenant-Id header>';
```

If a developer forgets a `WHERE tenant_id = $1` in a new endpoint, the
DB returns nothing instead of leaking. Migrations run as the
`gecko_migrate` role (`BYPASSRLS`).

`/admin/*` routes additionally set `app.is_admin = 'true'` and rely on a
secondary cross-tenant policy.

### 3.4 UA market conventions

- Hour ordinal `1..24`, **not** ISO timestamps. Tables that need a
  timestamp materialise it via a `GENERATED ALWAYS AS` column anchored
  in `Europe/Kyiv` (`EET/EEST`).
- All monetary values in **UAH (грн)**, returned over the wire as
  decimal strings to avoid JS float drift. Unit is in the field name
  (`price_uah_mwh`, `settlement_uah`).
- Geography uses Ukrainian oblast names
  (`Закарпатська`, `Київська`, `Запорізька`, etc.).
- ENTSO-E **16-char EIC codes** are the spine of asset identity:
  `Y` (area), `X` (party), `W` (resource), `V` (metering point).

---

## 4. API surface

OpenAPI 3.1 is auto-generated by FastAPI. Production base URL:
`https://api.gecko.radai-1984.dev`.

| Concern | Path |
|---|---|
| Machine-readable spec (FastAPI) | `GET /openapi.json` |
| Machine-readable spec (Next.js proxy) | `GET /api/openapi` |
| Swagger docs | `GET /docs` |
| Interactive Scalar UI (production frontend) | `/developer/api/explorer` |

All real endpoints live under `/api/v1/`. There are seven routers
(35+ endpoints in total):

| Router | Prefix | Highlights |
|---|---|---|
| `core` | `/api/v1` | `/auth/me`, `/auth/switch-tenant`, `/assets`, `/assets/{id}` |
| `market` | `/api/v1/market` | `/rdn`, `/vdr`, `/br`, `/dd`, `/bids`, `/revenue` |
| `dispatch` | `/api/v1/dispatch` | `/setpoints`, `/telemetry`, `/instructions` |
| `ems` | `/api/v1/ems` | `/forecasts`, `/forecasts/submit`, `/optimise`, `/kpi/daily`, `/kpi/portfolio` |
| `regulatory` | `/api/v1/regulatory` | `/settlements`, `/documents/{ref}/{id}/sign`, `/events` |
| `agents` | `/api/v1/agents` | `/{persona}/query`, `/voice/session` |
| `admin` | `/api/v1/admin` | `/portfolio`, `/operations`, `/analytics` (cross-tenant) |

### Envelope conventions

```jsonc
// success
{ "data": { /* … */ }, "meta": { "request_id": "uuid", "tenant_id": "uuid", "generated_at": "2026-05-23T14:32:11+03:00" } }

// error
{ "error": { "code": "VALIDATION_FAILED", "message": "…", "details": {} } }
```

Canonical error codes: `INVALID_TENANT` (400), `MISSING_TENANT_HEADER`
(400), `NOT_FOUND` (404), `VALIDATION_FAILED` (422), `RATE_LIMITED`
(429), `INTERNAL_ERROR` (500), `STUB_NOT_IMPLEMENTED` (501).

Multi-tenancy: every authenticated request carries `X-Tenant-Id: <uuid>`;
admin routes additionally require `X-Admin: true`. Tenant UUIDs for the
demo are fixed by env (`TENANT_PRODUCER_UUID`, `TENANT_CI_UUID`,
`TENANT_STORAGE_UUID`).

Caching: GETs use `Cache-Control: public, max-age=60,
stale-while-revalidate=300`. Mutating endpoints are `no-store`.

---

## 5. AI agents

Four personas, each scoped to a persona surface:

| Persona code | Display name | Surface |
|---|---|---|
| `dispatcher_analyst` | Диспетчерський аналітик | `/producer/*` |
| `market_analyst` | Ринковий аналітик | `/producer/*` |
| `energy_advisor` | Енергетичний радник | `/c-i/*` |
| `battery_coach` | Тренер по батареях | `/storage/*` |

All four share one engine
(`apps/api/src/gecko_vpp/agents_engine/`) composed of:

- **Deterministic classifier** (`classifier.py`) — regex + keyword
  scoring; **no LLM at runtime**. Removes prompt-injection surface and
  makes the demo offline-reliable.
- **20 intent handlers** (`intents/handlers/*.py`) — each pulls live
  data from Postgres through the same `tenant_id`-scoped session as
  any other request.
- **Evidence chips** — every response includes a `evidence` array
  pointing at the exact `(table, row_id, columns_used)` and a UI link
  back to the dashboard cell. This is the BRIEF §11.15 audit contract.

The voice agent is a stub by default (`VOICE_PROVIDER=stub`) — the
browser uses the Web Speech API for STT/TTS and posts the recognised
text to the same `/api/v1/agents/{persona}/query` endpoint. Setting
`VOICE_PROVIDER=openai-realtime` plus `OPENAI_API_KEY` switches to
ephemeral-key flow against the OpenAI Realtime API.

---

## 6. Frontend architecture

29 routes across five persona surfaces, all under `apps/web/app/`:

| Surface | Path prefix | Surfaces |
|---|---|---|
| Hero / persona picker | `/` | 1 (homepage with HeroVideo + AgentShowcase + interactive architecture diagram) |
| Виробник (hero persona) | `/producer/*` | 9 (Результати, Активи, Прогнози, Диспетчеризація, Ринок, УЗЕ, Сповіщення, Звіти, Налаштування) |
| C&I prosumer | `/c-i/*` | 5 (thin variants of the producer surfaces) |
| Storage owner | `/storage/*` | 5 |
| Cross-tenant operator | `/admin/*` | 3 (Engage / Operate / Analyze) |
| Developer portal | `/developer/*` | 5 (OpenAPI explorer, SDK-TS, SDK-PY, webhooks, top page) — **hidden from nav but routes are live** |

Stack:

- **Next.js 16** App Router (React 19, TypeScript). Uses `--webpack`
  (not Turbopack) — `@scalar/api-reference-react` and `cmdk` have
  Turbopack-incompatible imports today.
- **TanStack Query** for server state; **Zustand** for client state
  (theme, tenant, command-palette open).
- **Tailwind 3.4** plus a design-token CSS variable layer in
  `styles/tokens.css` — every component reads tokens, no literal hex
  outside the tokens file. Light primary + dark accent toggle.
- **Framer Motion** for the architecture-diagram animations,
  **Recharts** for charts, **cmdk** for the `Ctrl+K` palette,
  **lucide-react** for icons.
- **`@scalar/api-reference-react`** wraps the OpenAPI spec inside
  `/developer/api/explorer`.

### i18n

Four locales (`en` default, `uk`, `pl`, `ru`) via **next-intl 4.x**.

**No path-prefix routing.** Locale is decided server-side in
`apps/web/i18n/request.ts` by:

1. `krytsia-locale` cookie if set
2. else `Accept-Language` header (parsed with q-weights)
3. else `defaultLocale = "en"`

`LocaleSwitcher` in the top bar writes the cookie. The same 29 routes
serve all four locales — locale switching is a re-render, not a
re-route.

UA domain terms (РДН, ВДР, БР, ENTSO-E codes, oblast names) are
**never translated** — they are proper names, like NASDAQ.

### Analytics

Google Analytics 4 via `@next/third-parties/google`. Loaded only when
`NEXT_PUBLIC_GA_ID` is set. **Do not install `@vercel/analytics`** — its
2.x branch breaks Vercel's `modifyConfig` on Next 16 (see
`apps/web/next.config.ts` comment).

---

## 7. Deployment architecture

Two deployments, both wired to one repository:

| Component | Where | URL |
|---|---|---|
| Frontend | Vercel — auto-deploy from `master` | `krytsia.radai-1984.dev` |
| Backend | Hetzner VPS — `/opt/gecko-vpp/`, Docker Compose | `api.gecko.radai-1984.dev` |
| Reverse proxy | Caddy on same Hetzner host (shared with other apps) | TLS via Let's Encrypt |
| DNS | Cloudflare zone `radai-1984.dev` | A + CNAME records |

Two containers on the Hetzner side:

- **`gecko-postgres`** — `postgres:16-alpine`, volume `gecko_pgdata`.
  Bound only to `127.0.0.1:5433` for dev convenience; no host port in
  production.
- **`gecko-api`** — built from `apps/api/Dockerfile`
  (python:3.11-slim, uvicorn). Joins **both** `gecko-internal` and
  `caddy_web` networks in production.

Production requires **both** compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Without the `.prod.yml` overlay `gecko-api` does not attach to
`caddy_web` and the shared Caddy container returns 502s. See
[`DEPLOYMENT.md`](DEPLOYMENT.md) for the full runbook.

---

## 8. Synthetic data

- **Window:** 2026-04-23 → 2026-05-23 (31 days × 24 hours).
- **Seed:** deterministic — `SYNTH_RNG_SEED=42` by default in
  `.env.example`. Same seed → identical dataset.
- **Portfolio:** ~50 МВт total across **8–12 assets per tenant
  × 3 tenants = 24–36 assets** in five oblasts.
- **Tenants:**
  - `producer-1` — `ТОВ "Поляна Енерджі"`, Закарпатська, ~30 МВт
    (3× СЕС, 1× ВЕС, 1× УЗЕ, 1× ГПУ).
  - `ci-1` — `ПАТ "Дніпровий Завод"`, Дніпропетровська, ~12 МВт
    (1× СЕС-rooftop, 1× АктСпож, 1× УЗЕ, 1× Споживач).
  - `storage-1` — `ТОВ "Запоріжжя Сторідж"`, Запорізька, ~10 МВт
    (2× УЗЕ, 1× СЕС hybrid).
- **Story arcs injected** to make the demo legible:
  - ~40% of evenings pin to РДН hourly cap (17:00–21:00).
  - One solar curtailment around midday (~2026-05-12) and one wind
    curtailment overnight (~2026-05-04).
  - One planned maintenance (Producer-1's ВЕС, 2026-05-08 → 2026-05-12).
  - 1 day of negative РДН midday prices (~2026-05-04 weekend + PV
    surplus).
  - ~10 regulator notices spread across the window.
  - Monthly settlement statements straddle the Apr 30 → May 1 boundary.

The generator lives at `data-generator/data_generator/` (the dash is in
the directory, the module name is underscore). Run:

```bash
cd data-generator
python -m data_generator.main --reset
python -m data_generator.coverage    # asserts every BRIEF §11 criterion has rows
```

`coverage.py` exits non-zero if a §11 criterion has no matching data —
CI gate.

---

## 9. For the deep dive

When this 10-minute orientation is not enough:

- [`phase-3-architecture/ARCHITECTURE.md`](phase-3-architecture/ARCHITECTURE.md)
  — the full ~38-page detailed contract: every table with full DDL,
  RLS policies, all endpoints with request/response shapes, design
  tokens, FMEA, import-linter rules, alembic migration order.
- [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md) — v0.4 frozen spec: what was
  built and why, all 31 acceptance criteria, three personas, out-of-scope
  list.
- [`BRIEF_V05_AMENDMENT.md`](BRIEF_V05_AMENDMENT.md) — the most recent
  amendment: cinematic hero + AI-first positioning + i18n EN/PL/UK/RU +
  GA4 wiring.
- [`phase-3-architecture/HIGH_LEVEL_ARCHITECTURE.md`](phase-3-architecture/HIGH_LEVEL_ARCHITECTURE.md)
  — Stage 1 topology decisions (the "why we picked this stack" log).
- Per-domain instruction sheets in `phase-3-architecture/` — separate
  files for backend DB, backend API, frontend, AI agents, voice agent,
  SDK, security, testing, DevOps.
- [`apps/api/README.md`](apps/api/README.md),
  [`apps/web/README.md`](apps/web/README.md),
  [`data-generator/README.md`](data-generator/README.md),
  [`packages/sdk-ts/README.md`](packages/sdk-ts/README.md),
  [`packages/sdk-py/README.md`](packages/sdk-py/README.md) — package-level
  quickstarts.

Onboarding: see [`CONTRIBUTING.md`](CONTRIBUTING.md). Self-hosting
runbook: see [`DEPLOYMENT.md`](DEPLOYMENT.md).
