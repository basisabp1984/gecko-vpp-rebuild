# HIGH_LEVEL_ARCHITECTURE — GECKO VPP v2

**Status:** Draft v0.1 · written by Stage-1 agent (Synthesizer + High-Level Architect) on 2026-05-23
**Parent:** `PRODUCT_BRIEF.md` v0.4 (frozen 2026-05-23) — the immutable source of truth
**Inputs synthesised:** `phase-2-solution/RESEARCH_FINDINGS.md` v0.1; `phase-3-architecture/research_market_data_shape.md`; `phase-3-architecture/research_asset_data_shape.md`; `phase-3-architecture/research_regulatory_data_shape.md`; `PROGRESS.md`
**Next reader:** Stage-2 agent (Detailed Senior Architect) — must read this end-to-end before writing `ARCHITECTURE.md`.

---

## 1. Document conventions and status

### What this document is
- A **topology and component-boundary lock**. After it ships, no later stage may move a sub-system across the Vercel ↔ Hetzner line, swap Postgres for another DB, change the persona-URL layout, or merge the three GECKO sub-systems (Ринкова інтеграція / Диспетчеризація / EMS).
- A **technology-choice justification**. Every non-obvious pick is defended in §4.
- A **risk register at architectural level** (§7), to be threaded forward to FMEA in `ARCHITECTURE.md`.
- A **hand-off contract** to the Detailed Architect (§9), with explicit *locked decisions* and *delegated questions*.

### What this document is NOT
- Not SQL DDL. Tables are sketched at column-count level only; field types and constraints belong to the Detailed Architect.
- Not API contracts. No route paths, no request/response schemas, no error codes — Stage 2.
- Not React component trees, not Tailwind utility lists, not file layouts. Frontend specialist's job.
- Not deployment runbooks. DevOps specialist's job.

### Acceptance-criterion tagging
Throughout this doc, references like `[§11.3]` mean "services PRODUCT_BRIEF acceptance criterion §11.3". Every major component must service at least one criterion.

### Status flag
This draft has been **self-reviewed once** (see §10). Open items flagged to next stage are listed there.

---

## 2. System topology

### 2.1 High-level block diagram

```
                                     INTERNET
                                        |
                            +-----------+-----------+
                            |                       |
                            v                       v
                  +-------------------+   +-------------------+
                  | Cloudflare DNS    |   | Cloudflare DNS    |
                  | gecko.radai-      |   | api.gecko.radai-  |
                  | 1984.dev (A/AAAA  |   | 1984.dev (proxied |
                  | to Vercel edge)   |   | A to Hetzner IP)  |
                  +---------+---------+   +---------+---------+
                            |                       |
                            v                       v
                  +-------------------+   +-------------------+
                  | Vercel Edge       |   | Hetzner VPS       |
                  | (frontend host)   |   | 178.105.209.14    |
                  | - Next.js 16 SSR  |   | - Caddy reverse   |
                  | - App Router      |   |   proxy (existing,|
                  | - Edge functions  |   |   shared with     |
                  |   for /api/* proxy|   |   n8n + ses + zhy)|
                  |   to Hetzner      |   | - FastAPI app     |
                  +---------+---------+   |   in Docker       |
                            |             | - Postgres 16     |
                            |             |   in Docker       |
                            |    HTTPS    | - Static OpenAPI  |
                            +------------>|   served by       |
                                 (JSON)   |   FastAPI         |
                                          +-------------------+

  +--------------------------------------------------------------------+
  |                       Browser (any UA pro)                          |
  |  - Light/dark theme (CSS var swap on <html data-theme=...>)         |
  |  - LocalStorage: theme, tenant_id, persona                          |
  |  - Service worker (PWA shell; offline-friendly chrome)              |
  +--------------------------------------------------------------------+

  Build-time artefacts (CI/CD, not runtime):
  +--------------------------------------------------------------------+
  |  GitHub: basisabp1984/gecko-vpp-rebuild (public)                    |
  |    monorepo:                                                        |
  |      /apps/web              -> Next.js (deploys to Vercel)          |
  |      /apps/api              -> FastAPI (deploys to Hetzner Docker)  |
  |      /apps/synth            -> one-shot seed script                 |
  |      /packages/sdk-ts       -> @gecko-vpp/sdk → npm                 |
  |      /packages/sdk-py       -> gecko-vpp → PyPI                     |
  |      /packages/openapi      -> generated spec (single source)       |
  |      /infra                 -> docker-compose, caddy snippets       |
  +--------------------------------------------------------------------+
```

### 2.2 Trust boundaries

| Boundary | Crossing protocol | Mock-auth surface |
|---|---|---|
| Browser ↔ Vercel edge | HTTPS | None (no real auth) |
| Vercel ↔ Hetzner | HTTPS over Caddy | `X-Tenant-Id` header injected by Next.js route handler from session cookie |
| FastAPI ↔ Postgres | local socket inside Docker network | DB role with limited grants; `tenant_id` enforced by query filter and (Stage-2-decides) by RLS policy |
| Public ↔ `/developer/*` | HTTPS, no auth | Mock "API key" surface — UI shows the shape, key has no privilege |

### 2.3 Where DNS / CDN / caching sits

- **DNS:** Cloudflare zone `radai-1984.dev` (memory `reference_cloudflare_api_token.md` confirms zone-id and Edit token). New records:
  - `gecko.radai-1984.dev` → Vercel CNAME
  - `api.gecko.radai-1984.dev` → Hetzner A record (proxied through Cloudflare for TLS + rate-limit + DDoS shield)
- **CDN:** Vercel's edge handles static assets and SSR pages. Cloudflare in front of Hetzner gives a second cache layer for read-mostly endpoints (market prices, asset list).
- **Edge caching policy:** all `GET` endpoints returning synthetic data are `Cache-Control: public, max-age=60, stale-while-revalidate=300` — fine because data does not change during the demo session. Mutations (forecast submission stub, КЕП sign stub) carry `Cache-Control: no-store`.

### 2.4 v1 coexistence

`vpp.radai-1984.dev` (v1, the old build) stays live on its current Vercel project. It is **not** touched by this work. v2 uses a new Vercel project pointed at the new repo and the new subdomain. After user acceptance, v1 can be archived; the architectural diagram makes both subdomains valid simultaneously.

---

## 3. Component decomposition

Each component below is named, scoped, and assigned to a tech + an owning specialist for Stage 3.

### 3.1 Presentation — `/apps/web` (Next.js, Vercel)

- **Tech:** Next.js 16 App Router; React 19; TypeScript strict; Tailwind 4; CSS variables for design tokens; Lucide icons; Manrope from Google Fonts (self-hosted via Next font optimizer).
- **Role:** All pixels the user sees. Persona surfaces, chrome (tenant switcher, palette, theme toggle, voice button), interactive slide-7 diagram on `/`, developer portal pages, admin pages.
- **Constraint:** **No direct DB access** [§11.9]. Every page fetches from `/api/*` (Next.js route handlers) which proxy to FastAPI.
- **Theme system:** single component tree, `data-theme="light" | "dark"` attribute on `<html>` swaps a CSS-variable token set. Light is default; `localStorage` persists per user. [§11.1, NQ2-closed]
- **Servicing acceptance:** §11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.18, 11.20, 11.24, 11.25.
- **Specialist owner (Stage 3):** Frontend lead.

### 3.2 API gateway — `/apps/web/app/api/*` (Next.js route handlers)

- **Tech:** Next.js route handlers (edge runtime where possible; Node runtime when a library requires it).
- **Role:** *Thin proxy* to FastAPI. Adds `X-Tenant-Id` from cookie, forwards request, returns response. No business logic, no transformation beyond auth-shimming. Exists so the browser never sees `api.gecko.radai-1984.dev` directly (CORS-free, same-origin for browser).
- **Why a proxy and not direct browser → FastAPI:** lets us add per-tenant header server-side without exposing the mechanism client-side, lets future real auth slot in without touching pages, sidesteps preflight CORS.
- **Servicing acceptance:** §11.9 (API-first invariant).
- **Specialist owner:** Frontend lead with hand-off to Backend lead at the seam.

### 3.3 Sub-system: Ринкова інтеграція — FastAPI module

- **Tech:** Python module inside the FastAPI app: `app/market/`. Self-contained: routers, services, repositories, schemas.
- **Role:** Bids and confirmations to РДН / ВДР / БР; ancillary-service offers; bilateral-contract bookkeeping; settlement ledger; revenue P&L. Per slide 6 of client deck and PRODUCT_BRIEF §6.
- **Read-mostly during demo** — all market data is pre-seeded. Mutating endpoints (submit bid stub) write to journal tables (`market_bids` with `state='ACTIVE'` → flipped to `ACCEPTED` after a fake delay).
- **Servicing acceptance:** §11.8 (sub-system separation), §11.21 (single pane over РДН/ВДР/БР/ДД).
- **Specialist owner:** Backend lead.

### 3.4 Sub-system: Диспетчеризація — FastAPI module

- **Tech:** Python module `app/dispatch/`.
- **Role:** Setpoint queue, telemetry ingest (mocked from synthetic generator), instruction acknowledgement workflow, operator-adjustments table (re-using the Zhytomyr pattern explicitly, per `research_asset_data_shape.md` §B.5). Manual override surface.
- **Servicing acceptance:** §11.8.
- **Specialist owner:** Backend lead.

### 3.5 Sub-system: EMS — FastAPI module (with sub-modules)

- **Tech:** Python module `app/ems/` with internal sub-modules:
  - `app/ems/forecast/` — forecast surface (consumes pre-generated `forecast_runs` and `model_forecasts` tables; serves them; offers a "re-run" stub that perturbs the existing baseline rather than calling a model)
  - `app/ems/optimiser/` — the deterministic-perturbation optimiser. **Must run outside Next.js** per §11.14; FastAPI satisfies that out of the box.
  - `app/ems/kpi/` — KPI engine reads `asset_telemetry_hourly`, `market_bids`, `settlement_statements`, returns aggregates for home dashboards.
  - `app/ems/agents/` — AI text-agent backend (one classifier + 4 persona prompt templates). See §3.10.
- **Servicing acceptance:** §11.4, 11.14, 11.15, 11.22.
- **Specialist owner:** Backend lead + AI Agents lead (sub-module agents/).

### 3.6 Persistent storage — Postgres 16

- **Tech:** Postgres 16 in a Docker container on the Hetzner VPS. Single instance (no replica; this is a demo).
- **Volume:** Docker named volume `gecko_pg_data`, persisted across container restarts. **Restart does not regenerate data** [§11.10].
- **Role:** Holds the synthetic dataset (assets, telemetry, market data, settlements, regulator events, signed-doc stubs, forecast submissions, agent query log). Multi-tenant via `tenant_id` column on every business table + RLS policies (Stage 2 decides exact RLS syntax). Mirrors the Zhytomyr stack (FastAPI + psycopg3 + raw SQL, no ORM) which has shipped in production — proven path.
- **Why one Postgres serves all sub-systems and not per-sub-system DBs:** the three sub-systems share entities (asset, tenant, EIC); separating them into three DBs would require a federation layer the demo does not need. The *logical* separation is enforced by schema namespace (`market.*`, `dispatch.*`, `ems.*`, `regulatory.*`, `core.*`) — Stage 2 confirms schema layout.
- **Servicing acceptance:** §11.10, 11.11, 11.13.
- **Specialist owner:** DB lead.

### 3.7 Synthetic data generator — `/apps/synth` (Python, one-shot)

- **Tech:** Python script, run once at deploy time via `docker compose run synth`. No daemon, no cron [PRODUCT_BRIEF §12 forbids background workers].
- **Role:** Populates Postgres with 30 days of data spanning 2026-04-23 .. 2026-05-23 inclusive. Generates: assets (8–12, ~50 МВт total, Ukrainian names, ENTSO-E EIC codes), РДН prices (hourly, modelling cap-pinning per `research_market_data_shape.md` §1), ВДР trades (event-level), БР settlements (hourly, asymmetric prices), bilateral contracts (3–6 contract headers + hourly volumes), green-tariff settlements (monthly), ancillary offers + activations, asset telemetry hourly (the spine from `research_asset_data_shape.md` §0), forecasts (primary + refined per Zhytomyr pattern), regulator events (5–10 over the window), КЕП stub signatures.
- **Idempotency:** script truncates and reseeds; safe to re-run. Determinism: seeded RNG so two runs produce identical data.
- **Servicing acceptance:** §11.12, 11.13.
- **Specialist owner:** DB lead + Backend lead (joint).

### 3.8 SDK TypeScript — `/packages/sdk-ts`

- **Tech:** TypeScript package, ESM + CJS dual output, generated from OpenAPI 3.1 via `openapi-typescript` + a hand-written `GeckoClient` wrapper. Built and published as `@gecko-vpp/sdk` on npm.
- **Role:** Public consumer-facing SDK. Read-only methods for demo (list assets, get telemetry window, get market prices, get KPIs). Mutation methods present but documented as stubs (submit forecast, request sign).
- **Servicing acceptance:** §11.17, §11.18.
- **Specialist owner:** Backend lead (since OpenAPI is generated from FastAPI).

### 3.9 SDK Python — `/packages/sdk-py`

- **Tech:** Python package, async-first using `httpx`, generated from same OpenAPI. Published as `gecko-vpp` on PyPI under the `@gecko-vpp` user / org.
- **Role:** Mirror of TS SDK for Python consumers.
- **Servicing acceptance:** §11.17, §11.18.
- **Specialist owner:** Backend lead.

### 3.10 AI text agents — FastAPI sub-module `app/ems/agents/`

- **Tech:** Pure Python, no LLM API call. One **deterministic keyword classifier** (regex + bag-of-words + a small intent table) routes a user question into one of ~12 question families. Each family has a **per-persona prompt template** (Jinja2) that fills in numbers fetched fresh from Postgres at query time. Four agents, one engine, four template sets:
  - `dispatcher_analyst` (on `/producer/`)
  - `market_analyst` (on `/producer/`)
  - `energy_advisor` (on `/c-i/`)
  - `battery_coach` (on `/storage/`)
- **Role:** Provides the *visible* AI surface promised by §11.15. The user types a question → classifier picks an intent → SQL query against the live DB returns evidence → template renders the answer in Ukrainian.
- **Why deterministic and not LLM:** PRODUCT_BRIEF §12 explicitly out-of-scopes "Real LLM". Plus: no prompt-injection surface (risk §13 of brief), no API spend, deterministic for demo reliability, and no latency (response in < 100 ms).
- **Servicing acceptance:** §11.15.
- **Specialist owner:** AI Agents lead.

### 3.11 Voice agent — pluggable handler in `/apps/web` chrome + FastAPI endpoint

- **Tech, default (no key):** UI button always visible in topbar. Click → press-and-hold-to-talk simulation → POSTs to `/api/agents/voice` → FastAPI returns a **canned scripted response** for one of 5 pre-recognised scenarios ("що сьогодні з виробництвом?", "коли заряджати батарею?", "коли наступний небаланс?", "покажи стан активів", "сформуй звіт за сьогодні"). Browser plays the response via Web Speech API `speechSynthesis` (free, Ukrainian voice if available).
- **Tech, upgrade path (real):** If `OPENAI_API_KEY` is present in FastAPI env, the same endpoint switches to OpenAI Realtime API and proxies the WebSocket. The frontend behaviour is identical — the button, the press-to-talk UX, the result rendering are all unchanged.
- **Role:** Services §11.16 (1 voice agent, 3-5 scenarios). Hard constraint from user: **no paid API spend without explicit OPENAI_API_KEY**. Default deploy stays free.
- **Why this pattern:** the frontend has no knowledge of which backend is live, so an upgrade is a single env var. The demo "works" out of the box, and a credible upgrade path exists.
- **Servicing acceptance:** §11.16.
- **Specialist owner:** Voice agent lead (Stage 3).

### 3.12 Dev portal — `/apps/web/app/developer/*` + auto-generated OpenAPI

- **Tech:** Next.js subroutes serving Markdown content (MDX) for the prose, plus an embedded **Scalar** UI for the OpenAPI explorer (Scalar over Swagger UI because: better light/dark theming, faster, less JS — see §4).
- **Role:** Public, no-login, browsable [§11.18, NQ5-closed]. Pages: `/developer/`, `/developer/api/explorer`, `/developer/sdk-ts/`, `/developer/sdk-py/`, `/developer/webhooks/`, `/developer/auth/` (mock-API-key flow).
- **OpenAPI source:** FastAPI auto-generates at `/openapi.json`. Build step copies it to `/packages/openapi/openapi.json` for SDK generation. Stage 2 decides whether the spec is pulled at build time or at request time.
- **Servicing acceptance:** §11.18.
- **Specialist owner:** Frontend lead.

### 3.13 Admin module — `/apps/web/app/admin/*`

- **Tech:** Same Next.js stack, three subroutes (`/admin/engage`, `/admin/operate`, `/admin/analyze`). Reads cross-tenant aggregates from FastAPI (the API exposes admin endpoints distinguished by an `X-Admin: true` header — mock, but the shape is real).
- **Role:** Services §11.6 (cross-tenant operator view). Slide-7 architecture diagram embedded on `/admin/engage` in addition to `/`.
- **Servicing acceptance:** §11.6.
- **Specialist owner:** Frontend lead.

---

## 4. Technology choices justified

### Why FastAPI, not Express / Fastify / Hono
1. **Memory `reference_zhytomyr_forecast.md` proves we already ship FastAPI in production** at `zhytomyr.radai-1984.dev` on the same Hetzner VPS. Reusing the same stack means the same `psycopg3` patterns, the same Docker layout, the same Caddy snippet shape — strictly faster to deploy.
2. **Auto-generated OpenAPI** is first-class in FastAPI and feeds both SDKs (TS + Python) from a single source [§11.17, §11.18].
3. **Pydantic** is the cleanest way to express the rich Ukrainian-energy data shapes (ENTSO-E EIC validation, OBIS codes, signed `tenant_id`) at the API edge.
4. Python is also the language of the synthetic-data generator and (in a real future) the ML / forecasting code. One language across the backend reduces context-switching cost for the next phase.

### Why Postgres, not SQLite or DuckDB
1. **User explicitly asked for Postgres** in the task brief.
2. **Multi-tenant RLS** [§11.13 spirit + brief §13 risk] is a first-class Postgres feature; SQLite can't do it.
3. **Schema namespacing** (`market.`, `dispatch.`, `ems.`, `regulatory.`) gives the three-sub-system separation a real on-disk shape — SQLite would force it all into one namespace.
4. **Time-series performance** for the telemetry table (~5M rows in a worst-case generator pass) is fine on Postgres with monthly RANGE partitioning; SQLite would degrade.
5. Zhytomyr already runs Postgres on the same VPS; we run a separate logical DB on the same instance.

### Why Next.js 16 App Router, not Remix / SvelteKit / Astro
1. v1 was Next.js, and we want continuity for the team's mental model. The user's memory `project_vercel_analytics_next16_bug.md` is *negative* knowledge but it's *exact* knowledge — we know which trap to avoid (don't pin `@vercel/analytics@2.x` on Next 16 because `modifyConfig` breaks on Vercel).
2. App Router gives us co-located server components + client components + route handlers in one file tree — clean separation between *render server-side* (the producer dashboard) and *interact client-side* (palette, drawers, the slide-7 SVG).
3. Vercel deploy is one-command. We already have credentials and DNS for the parent domain.

### Why Caddy already-on-VPS, not new nginx
- Memory `reference_n8n_hetzner_server.md` and `reference_zhytomyr_forecast.md` confirm Caddy is the existing reverse proxy on `178.105.209.14`, terminating TLS for `n8n.radai-1984.dev`, `ses.radai-1984.dev`, `zhytomyr.radai-1984.dev`. Adding `api.gecko.radai-1984.dev` is **one new snippet** in the existing Caddyfile, automatic Let's Encrypt cert, zero extra moving parts.
- nginx would mean a parallel TLS config, a parallel cert-renewal cron, and a parallel mental model for the operator. No upside.

### Why deterministic classifier for AI agents, not real LLM
1. **PRODUCT_BRIEF §12 explicitly out-of-scopes** "Real LLM (analyst stays a keyword classifier over the DB; LLM-shaped UX, deterministic backing)".
2. **Prompt-injection surface goes to zero** [brief §13 risk] — the agent cannot be jailbroken because there is no model to jailbreak.
3. **No API spend** — the demo must be free to run.
4. **Determinism** — for an acceptance walk-through, the same question gives the same answer. With a real LLM that becomes a flaky-test problem.
5. **Latency** — < 100 ms responses look snappy, reinforcing "production-fidelity feel" [§11.25].

### Why design-token system (one component, two themes)
1. **PRODUCT_BRIEF §13 risk** flags "Both themes designed = 2× design work" and prescribes single-token system as the mitigation.
2. Tailwind 4 has first-class CSS-variable support; we declare tokens (`--surface-card`, `--text-body`, `--brand-primary`, `--status-warning`) in two `:root[data-theme=light]` and `:root[data-theme=dark]` blocks, and every component reads tokens rather than literal colors.
3. The token contract becomes one of the few things the Detailed Architect MUST spec exactly — see §9 hand-off list.

### Why Scalar over Swagger UI for the API explorer
- Scalar's light/dark theme parity is built in (matches our token system more cleanly than Swagger UI).
- Smaller bundle, faster first paint — relevant since `/developer/api/explorer` is part of the §11.25 "production-fidelity feel" promise.
- It's the trajectory the dev-portal space is moving toward (Stripe, Linear, Resend all moved off Swagger UI).

---

## 5. Data flow at high level

All flows below assume the user has already chosen a tenant via the chrome switcher (defaults to "Demo-Producer-1" on first visit).

### 5.1 Read flow — user opens `/producer/`

```
Browser GET /producer/
   |
   v
Vercel Edge SSR renders the page shell + first-fold data via:
   |
   v
Next.js route handler GET /api/kpi/portfolio-summary?tenant=<id>&from=2026-04-23&to=2026-05-23
   |  (injects X-Tenant-Id from session cookie)
   v
Caddy on Hetzner forwards to FastAPI: GET /api/v1/kpi/portfolio-summary
   |
   v
FastAPI ems.kpi.service.get_portfolio_summary(tenant_id, window)
   |
   v
psycopg3 reads from core.asset JOIN ems.asset_telemetry_hourly JOIN market.settlement_lines
   |
   v
Returns JSON {grn_saved, grn_earned, imbalances_avoided_mwh, co2_avoided_tn, availability_pct, opportunity_score}
   |
   v
Next.js renders KPI strip, then client-side hydrates the chart components which fetch detail via additional /api/* calls
```

**Note on caching:** the `portfolio-summary` endpoint is idempotent for a 30-day static dataset, so Cloudflare caches it for 60s. The browser sees < 50 ms response time on a cache hit.

### 5.2 Synthetic data generation flow — at deploy time only

```
docker compose run --rm synth python -m gecko_synth.seed --tenants 3 --days 30
   |
   v
Reads config/synth.yaml (asset mix, event injection list, RNG seed)
   |
   v
For each tenant in {Demo-Producer-1, Demo-CI-1, Demo-Storage-1}:
   |
   v
   1. Insert 8-12 rows in core.asset (with EIC codes, names "Поляна СЕС" etc.)
   |
   v
   2. For each of 30 days, for each of 24 hours:
      - generate РДН price (apply cap-pinning model)
      - generate БР prices (system-short, system-long)
      - for each asset: telemetry row (CF profile + cloud/wind noise)
      - for each RES asset: forecast row (primary + refined)
   |
   v
   3. Inject events (RES curtailment, planned outages, regulator notices)
   |
   v
   4. Generate market_bids, ancillary offers/activations
   |
   v
   5. Generate one monthly settlement_statement per (tenant, counterparty)
   |
   v
   6. Generate ~6 signed_documents stubs
   |
   v
COMMIT, exit.
```

**Idempotency contract:** the script `TRUNCATE`s every business table (preserving migrations) and reseeds. Re-running it produces identical data because RNG is seeded. This is what §11.10 means — the *running app* never re-seeds, but a fresh deploy can.

### 5.3 AI agent flow — user asks "коли наступний небаланс?"

```
Browser POST /api/agents/query
   body = { agent: "dispatcher_analyst", text: "коли наступний небаланс?" }
   |
   v
Next.js route handler proxies to FastAPI POST /api/v1/agents/query
   |
   v
FastAPI app.ems.agents.engine.classify(text)
   -> intent = "next_imbalance_window"
   |
   v
app.ems.agents.intents.next_imbalance.run(tenant_id, now)
   -> SELECT FROM market.br_settlements
      WHERE tenant_id = $1
        AND interval_start > $2
        AND ABS(our_imbalance_mwh) > 0.5
      ORDER BY interval_start LIMIT 3
   |
   v
Template "next_imbalance.j2" fills in numbers:
   "Найближче вікно небалансу: завтра 18:00–19:00. Очікуваний небаланс ≈ 1.2 МВт·год
    по об'єкту «Поляна СЕС». Ризик: ціна дефіциту 7,400 грн/МВт·год."
   |
   v
Returns { answer: "...", evidence: [{table, row_id}, ...], persona: "dispatcher_analyst" }
   |
   v
Browser renders bubble; "evidence" chips link to the source row on /producer/rynok/ or /producer/spovishchennya/
```

The `evidence` field is the differentiator from a generic LLM chatbot — every claim links back to a row in the live DB [§11.15: "≥3 question families with evidence drawn from the live DB, not hard-coded strings"].

### 5.4 Forecast submission stub flow

```
User on /producer/prognozy/ clicks "Подати прогноз" button
   |
   v
Browser POST /api/forecast/submit
   body = { date: "2026-05-24", resource_eic: "10W...", hourly_volumes_mwh: [0, 0, ..., 4.2, ...] }
   |
   v
Next.js proxy -> FastAPI POST /api/v1/forecast/submissions
   |
   v
FastAPI inserts row in regulatory.forecast_submissions
   status='DRAFT', then a setTimeout (or async task) flips to 'SUBMITTED' after 200ms,
   then 'ACK' after another 800ms
   |
   v
Returns submission_id + initial status
   |
   v
Browser shows "Прогноз подано, очікуємо підтвердження" → polls GET /api/forecast/submissions/{id}
   every 500ms until status=='ACK' → shows green tick + mRID
```

No real XML is sent anywhere. The `raw_xml` column in `forecast_submissions` is filled with a generated ENTSO-E `ScheduleDocument` stub for *visual realism* in a "View raw" drawer — but it goes nowhere.

### 5.5 КЕП signing stub flow

```
User on /producer/zvity/ clicks "Підписати через КЕП" on a settlement statement card
   |
   v
Browser POST /api/sign
   body = { document_ref_table: "settlement_statements", document_ref_id: 12 }
   |
   v
Next.js proxy -> FastAPI POST /api/v1/sign
   |
   v
FastAPI:
   1. Generate fake SHA-256 of the document JSON (real hash of fake content)
   2. Pick a random signer from a fixture list (Ukrainian names + ЄДРПОУ + АЦСК)
   3. Insert into regulatory.signed_documents
   4. Update settlement_statements.signed_doc_id and status='SIGNED'
   5. Generate 64 random bytes as a "p7s_blob" stub
   |
   v
Returns { signed_doc_id, badge_text: "Підписано КЕП · Іваненко І.І. · ..." }
   |
   v
Browser swaps the "Підписати" button for the КЕП badge component
```

No real crypto — exactly per NQ4-closed and PRODUCT_BRIEF §12.

---

## 6. Major design decisions

Each decision is **locked at this level**. The Detailed Architect inherits these and may refine but not reverse.

### D1. Time keying convention: `(date DATE, hour SMALLINT 1..24)` columns AND a derived `interval_start TIMESTAMPTZ` for sorting / range queries
- **Rationale:** UA dispatchers read in `Г1..Г24` columns (Zhytomyr CSV format, `forecast_zhytomyr_2026-04-14.csv` proves this). Operators reading the producer dashboard expect that vocabulary. But SQL ranges and partitioning need a `TIMESTAMPTZ`. We carry both.
- **Rejected alternatives:** (a) timestamp-only — fails the Ukrainian dispatcher's sniff test; (b) hour-0..23 — diverges from the UA convention (Zhytomyr uses 1..24, deck shows 1..24).
- **Source:** `research_asset_data_shape.md` §0 and §B.4.

### D2. Tenant isolation: `tenant_id UUID NOT NULL` column on every business table + RLS policy enforced on the DB role used by FastAPI
- **Rationale:** §11.13 demands no-code-change data swap; brief §13 risk demands credible isolation even with mock auth. RLS is the right place because it does not depend on every query author remembering to add `WHERE tenant_id = $1`.
- **Rejected:** schema-per-tenant — would explode migrations 3×; row-level filter at application layer only — too easy to leak.

### D3. ENTSO-E EIC codes embedded in every market and asset row
- **Rationale:** PRODUCT_BRIEF §4 invariant; `research_regulatory_data_shape.md` §6 enumerates the codes. Bidding zone defaults to `10Y1001C--00003F` (UA single BZN post-2022). Each producer asset carries a `resource_eic CHAR(16)` (W-prefix). Each metering point carries a V-prefix EIC. Each market participant carries an X-prefix EIC.
- **Rejected:** invented synthetic codes — fails any UA energy professional's sniff test in 30 seconds [§11.25].

### D4. РДН price generator must model cap-pinning behaviour
- **Rationale:** `research_market_data_shape.md` §1 documents "evening peak at 17:00 hit the price ceiling 100% of days in Nov 2025". Our 30-day window (Apr 23 – May 23 2026) sits *after* the Mar 31 2026 cap revert, so we use the hourly caps **5,600–6,900 UAH/MWh** (РДН/ВДР). Generator must pin evening peak (17:00–22:00) prices at the cap on a credible fraction of days (say 30–60% during this window — spring, not winter).
- **Rejected:** uncapped Gaussian random walk — would produce 12,000 UAH/MWh outliers and read as fake.

### D5. AI agents share ONE classifier engine with per-persona prompt templates
- **Rationale:** §11.15 explicit. Brief §13 risk "4 AI agents instead of 2 increases prompt-engineering surface" answered by "One shared engine + per-persona system prompts".
- **Rejected:** four separate codebases — duplicates intent vocabulary, drift over time.

### D6. SDK packages built from same generated OpenAPI schema (single source of truth)
- **Rationale:** §11.17 demands TS + Py SDKs cover the same surface. Generating both from `/openapi.json` makes drift impossible. Build pipeline: FastAPI starts → emits `openapi.json` → CI uploads to `/packages/openapi/openapi.json` → `openapi-typescript` and `openapi-python-client` both consume it → version-bumped npm + PyPI releases.
- **Rejected:** hand-written SDKs — guaranteed drift between TS and Py over time.

### D7. Design tokens via CSS variables; theme via `data-theme` attribute on `<html>`
- **Rationale:** brief §13 risk mitigation; only way to keep "one component, two themes" honest. Tailwind 4 supports `:root[data-theme=...] { --token: value }` natively.
- **Rejected:** two compiled stylesheets — doubles bundle; styled-components / runtime-CSS-in-JS — costs render perf, breaks SSR caching.

### D8. Voice agent UI button always visible; click invokes pluggable handler (stub or real depending on FastAPI env)
- **Rationale:** user hard constraint "Voice agent: stub default, real Realtime API only when explicit OPENAI_API_KEY provided". Frontend stays identical between modes; the swap is server-side only — this is the cleanest contract.
- **Rejected:** hide the button when no key — would break §11.16 "voice agent accessible from topbar" on the default deploy.

### D9. Dev portal `/developer/api/explorer` uses Scalar (not Swagger UI / Redoc)
- **Rationale:** see §4. Light/dark parity matters because both themes are first-class [§11.1].
- **Rejected:** Swagger UI — historical default but heavy and visually mismatched with our token system.

### D10. Synthetic data window = 30 days (2026-04-23 to 2026-05-23) — diverges from research recommendations
- **Rationale:** **explicit user hard constraint from PROGRESS.md and orchestrator brief.** `research_market_data_shape.md` recommended 13 months and `research_regulatory_data_shape.md` recommended 90 days, but the user override wins. Generator parameters are configurable; 30 days is the v2-demo default.
- **Implication:** some scenarios from research drop out — e.g., the Jan/Mar 2026 cap-regime change is *before* our window and cannot be a story arc. We document this gap rather than fake it.
- **Story arcs that fit in 30 days:** weekday/weekend baseload swing (~4 cycles), 1-2 RES-curtailment events, 1 planned-maintenance window, 5-10 daily settlement runs (one per business day for one tenant), monthly settlement boundary (Apr 30 → May 1 transition is in-window).

### D11. Sub-system separation = Python module boundaries (not separate services)
- **Rationale:** §11.8 says "folders, services, or both — Phase 3 decides". Three services means three deploys, three Docker containers, three sets of Caddy snippets, three log streams — overkill for a demo. Three Python modules with strict import rules (Disp. cannot import from Ринкова's internals, only from a public interface package `app/core/contracts/`) gives the *separation property* without the operational cost.
- §11.14 demands the optimiser run "not in the Next.js process" — satisfied because the whole FastAPI app is not the Next.js process. No additional split needed.
- **Detailed Architect must spec:** the import-rule contract (which module can import what from which). Stage 2 owns that.

### D12. Schema namespacing inside Postgres: `core.`, `market.`, `dispatch.`, `ems.`, `regulatory.`, `agents.`
- **Rationale:** mirrors the sub-system decomposition on disk. Migrations live in `db/migrations/<schema>/` folders. Avoids one giant `public` schema with 40 tables.
- **Rejected:** all in `public` — works but reads like a junk drawer; one schema per tenant — D2 supersedes.

### D13. Forecast model = "two-stage" (primary morning + refined intraday) following Zhytomyr precedent
- **Rationale:** `research_asset_data_shape.md` §B.5 lists this as the directly-reusable pattern. Surfaces as `forecast_runs` table with `forecast_type ∈ {primary, refined}` column. Demo shows MAPE per stage.
- **Rejected:** single-shot forecast — misses the §11.19 "Подача прогнозу" story arc where the user can resubmit a refined forecast intraday.

### D14. Telemetry granularity for v2 demo: **hourly** (not 15-min, not 1-min)
- **Rationale:** `research_asset_data_shape.md` §0 acknowledges 15-min is the real convention but hourly is what `(date, hour 1..24)` operates in, and it's what the operator dashboards display. We keep telemetry hourly to match the dispatch view; if a Stage-3 specialist wants 15-min for a specific chart, they can store a quarter-hourly fact for that asset class only.
- **Cost:** ~12 assets × 24 h × 30 days × 3 tenants = ~26,000 rows for `asset_telemetry_hourly` — trivial.
- **Rejected:** 1-min — 1.5M rows is fine but adds no demo value; 15-min — better fidelity but harder to render compactly in Г1..Г24 spreadsheet-style.

### D15. Slide-7 hub-and-spoke diagram on `/` is a React component (SVG), not an image
- **Rationale:** §11.3 demands interactive — animate connection lines on hover, click navigates. Plain `<img>` cannot satisfy that.
- **Rejected:** Mermaid diagram — animation control is limited; D3.js — overkill for ~15 nodes. Plain React + SVG paths + Framer Motion animations is the right fit.

---

## 7. Risks at architectural level + mitigations

### R1. Postgres on shared VPS gets noisy-neighbor'd by other services (n8n, ses, zhytomyr)
- **Blast radius:** GECKO queries slow or hang during demo; embarrassing on a live show.
- **Mitigation:** Postgres runs as **its own container with explicit CPU + memory limits** in docker-compose (e.g., 2 CPU, 2 GB RAM). Heavy queries (telemetry aggregates for KPI) get pre-aggregated into materialised views refreshed by the synth script at seed time (no runtime refresh = no contention). The Detailed Architect specifies the materialised-view list.

### R2. Vercel + Next 16 + `@vercel/analytics` regression (memory `project_vercel_analytics_next16_bug.md`)
- **Blast radius:** deploy passes locally, fails on Vercel; loss of half a day debugging.
- **Mitigation:** Pin `@vercel/analytics@~1.x` from day one (or omit the package entirely until v2.1 is verified). Add a CI step that builds against the Vercel-target environment, not just local Next dev.

### R3. Cloudflare proxy on `api.gecko.radai-1984.dev` strips a header the FastAPI app expects (e.g., `X-Tenant-Id`)
- **Blast radius:** tenant switcher silently breaks; every user sees Demo-Producer-1 data.
- **Mitigation:** integration test in CI that hits the public URL with an `X-Tenant-Id` and asserts the FastAPI received it (echoed in response). Cloudflare proxy rule explicitly whitelists `X-Tenant-Id`. Backup channel: tenant in URL query parameter as well as header (FastAPI tries header first, falls back to query).

### R4. Synthetic data "feels wrong" to a UA energy professional
- **Blast radius:** demo lands poorly with the actual buyer; product brief §13 first risk.
- **Mitigation:** The three research files exist specifically to anchor numbers (РДН caps, BESS arbitrage cycles, EIC codes, КЕП badge fields). Synth generator includes an **internal sniff-test script** that asserts: every РДН evening-peak hour ≤ cap; every battery SOC ∈ [10, 90]%; every EIC is 16 chars; every settlement amount = volume × tariff × (1 + VAT). Sniff-test must pass in CI before deploy.

### R5. AI agent classifier returns "I don't know" too often
- **Blast radius:** §11.15 says "≥3 question families with evidence" — if classifier misses all of them, criterion fails.
- **Mitigation:** Agents lead writes a fixed **gold-set** of 30 questions (per agent: ~7-8) that the classifier MUST correctly route. CI runs this set on every PR. Failure on the gold set blocks merge.

### R6. КЕП stub gets misread as real crypto by a security-conscious reviewer
- **Blast radius:** trust hit ("they claim КЕП but it's fake bytes").
- **Mitigation:** every КЕП badge in the UI carries a small "DEMO" watermark; the `/developer/` portal documents the КЕП mock explicitly; an `/about/credentials` page lists everything that is stubbed.

### R7. 30-day data window leaves some §11 acceptance criteria with too few rows
- **Blast radius:** acceptance walk-through finds an empty chart.
- **Mitigation:** synth generator pre-computes coverage: for each acceptance criterion, the generator records which row(s) satisfy it. A coverage report (`synth_coverage.md`) generated at seed time lists "§11.19 satisfied by 7 forecast submissions in window", etc. Empty coverage = block deploy.

### R8. Cross-tenant data leak in `/admin/*` because admin endpoints intentionally bypass tenant filter
- **Blast radius:** confusing — "tenant data isolation" claim weakens.
- **Mitigation:** admin endpoints live in a **separate FastAPI router** with explicit "this is cross-tenant" markers in code (decorator `@cross_tenant`). Logging always records cross-tenant access. The mock `X-Admin: true` header is checked at the router boundary, not inside individual endpoints.

### R9. SDK build pipeline drifts away from the live API
- **Blast radius:** developer copies an SDK example, gets 404 because endpoint was renamed.
- **Mitigation:** the SDK builds run as part of the same CI pipeline as FastAPI; if FastAPI emits an OpenAPI that the generators choke on, CI fails before deploy. SDK examples in `/developer/sdk-*/` are tested against the live API in CI (smoke test: import SDK, hit endpoint, assert non-empty result).

### R10. The slide-7 interactive diagram is heavier than expected (>200 KB JS) and slows `/` first-load below the §11.25 1.5s budget
- **Blast radius:** brand-defining landing page reads slow.
- **Mitigation:** the diagram is a Server Component skeleton (SVG paths static) + Client Component overlays for hover animations. Heavy interaction (Framer Motion) is dynamically imported. Performance budget checked in CI via Lighthouse on a representative cold cache.

---

## 8. Non-goals and out-of-scope (re-affirmed)

Mirrors PRODUCT_BRIEF §12. Stage 2 must NOT introduce any of these:

- ❌ Real SCADA / OPC-UA / Modbus / MQTT bridge
- ❌ Real market connector to СОП / Укренерго
- ❌ Real auth, SSO, RBAC (mock multi-tenancy only)
- ❌ Real LLM (deterministic classifier + templates only)
- ❌ Real MILP / convex solver
- ❌ Real КЕП / Дія.Підпис crypto
- ❌ Multi-language UI (Ukrainian only)
- ❌ Mobile-native build (PWA-only)
- ❌ Blockchain anything
- ❌ Billing / invoice generation
- ❌ Background workers / cron / queue (data static at runtime, "live ticker" is faked client-side)
- ❌ Production-grade observability (Sentry / RUM / tracing) — basic Hetzner logs only

---

## 9. Hand-off to Detailed Architect

### 9.1 DECISIONS LOCKED — do NOT relitigate

1. Frontend = Next.js 16 App Router on Vercel; persona-stratified URLs (`/producer/*`, `/c-i/*`, `/storage/*`, `/developer/*`, `/admin/*`) (D7 in §6, brief §10).
2. Backend = FastAPI on Hetzner VPS behind Caddy at `api.gecko.radai-1984.dev` (§2.1, §4).
3. DB = Postgres 16 in Docker on same VPS, schema-namespaced by sub-system (D12).
4. Tenant isolation = `tenant_id UUID NOT NULL` + RLS, mock auth (D2).
5. Time keying = `(date DATE, hour SMALLINT 1..24)` + derived `interval_start TIMESTAMPTZ` (D1).
6. EIC codes everywhere; BZN default `10Y1001C--00003F` (D3).
7. РДН price generator uses post-Mar-2026 hourly caps (5,600–6,900 UAH/MWh); cap-pinning behaviour modelled (D4).
8. 4 AI agents share one engine + per-persona prompt templates; deterministic classifier (D5, §3.10).
9. SDKs (TS + Py) generated from one OpenAPI source (D6).
10. Light theme primary + dark accessibility toggle via CSS-var token system, `data-theme` attribute swap (D7, brief §5).
11. Voice agent default = stub (free); upgrade path = OpenAI Realtime via env var (D8, §3.11).
12. Data window = **30 days, 2026-04-23 to 2026-05-23 inclusive** (D10, user hard constraint).
13. Sub-systems = Python module boundaries with cross-module import rules, not separate services (D11).
14. Slide-7 diagram = React+SVG component on `/` and `/admin/engage/` (D15).
15. КЕП = stub badge only, fake hash + timestamp (brief §12, §5.5 flow).

### 9.2 QUESTIONS DELEGATED to Stage-2 Detailed Architect

The Detailed Architect MUST answer these and either lock or escalate to the user:

1. **Exact Postgres schema DDL** for every table — start from sketches in `research_*_data_shape.md`, finalize types, constraints, indexes, RLS policies.
2. **Exact list of materialised views** for KPI pre-aggregation (asset_daily_summary, market_hourly_index, tenant_kpi_30d, etc.).
3. **Exact FastAPI route paths** under `/api/v1/*` — naming convention (kebab vs snake), versioning policy (v1 only for now).
4. **Exact RLS policy SQL** — per-tenant `USING (tenant_id = current_setting('app.tenant_id')::uuid)` style or another approach.
5. **Cross-module import rules** — what is the public interface of each sub-system module, and how is it enforced (ruff rule, import-linter, etc.).
6. **Design-token contract** — the full token list (typography, spacing, surface, brand, status, chart-palette) with light + dark values; how Manrope is loaded; how the palette is sampled from the client PDF (a one-off task before Stage 3 frontend specialist starts).
7. **Synth-generator config schema** — `synth.yaml` keys (tenant list, asset mix per tenant, RNG seed, event injection list).
8. **AI agent intent vocabulary** — the full list of question families per agent, the gold-set test fixtures (R5 mitigation).
9. **Exact OpenAPI version + linter rules** — OpenAPI 3.1; what spectral/vacuum rules to enforce; doc style (operationId convention).
10. **TS SDK + Py SDK package skeleton** — npm scope confirmed `@gecko-vpp/sdk`, PyPI name `gecko-vpp`; CI publish steps (manual approval gate? auto on tag?).
11. **Caddy snippet for `api.gecko.radai-1984.dev`** — exact directives, including header allowlist, rate limits, log format.
12. **Postgres backup strategy for the demo** — even a daily `pg_dump` to a Hetzner-local volume? Or accept ephemeral?
13. **Voice-agent canned-response set** — exact Ukrainian text per scenario, exact Web Speech API voice choice (uk-UA, fallback?).
14. **React component tree for the slide-7 hub-and-spoke diagram** — nodes list, connection list, hover animation spec, click-navigation map (which node → which URL).
15. **FMEA table** for the architecture (modes of failure × detection × recovery), to satisfy bible methodology Phase 3 deliverable.
16. **Tests strategy** — what is unit, what is integration, what is smoke; how the 30-question gold set is wired in.
17. **Deployment topology runbook** — order of operations for a fresh deploy (DNS first, then Docker, then synth, then verify, then Vercel).
18. **Coverage-report shape** — the `synth_coverage.md` artefact mentioned in R7; what fields it carries.
19. **Admin endpoint discrimination** — the cross-tenant `@cross_tenant` decorator design; logging policy.
20. **Webhook subscription stub** — `/developer/webhooks/` documents what; does FastAPI emit anything (fake heartbeat?) or is it purely doc?

---

## 10. Addendum: self-review notes

After writing the body above, I re-read it once. Findings:

### 10.1 Internal inconsistencies found

- **§5.5 КЕП flow inserts into `regulatory.signed_documents`** but §3.6 lists schemas as `core.*, market.*, dispatch.*, ems.*, regulatory.*, agents.*` — consistent. Good.
- **§3.10 says "~12 question families"** but §9.2 item 8 leaves the exact vocabulary open to Stage 2. The "12" is intentional ceiling-not-floor and should not be read as locked — adding a sentence in §3.10 to clarify.
- **§5.4 forecast-submission status flow** says `DRAFT → SUBMITTED → ACK` happens client-side via setTimeout. That contradicts §12 "no background workers". Strictly the server doesn't run a worker — the client polls and the server flips status on read based on `time_since_submission`. Flagging for Stage 2 to lock the mechanism.
- **D10 says "the Jan/Mar 2026 cap-regime change is *before* our window"** — Mar 31 2026 is just before Apr 23 2026, so yes, before. But our 30-day window starts 23 days after the revert; the cap regime in our window is the **post-revert** state. Reading D4 confirms this is what the generator uses. Consistent.

### 10.2 Misalignments with PRODUCT_BRIEF v0.4

- Brief §11.5 says `/c-i/*` and `/storage/*` need "at minimum: home, активи, прогнози, ринок, звіти" — five surfaces, not the full nine. My §3.1 just says they exist but doesn't enumerate the cut. Adding to §9.2 delegated question 14-ish region: "exact list of which 5 of 9 surfaces ship for `/c-i/` and `/storage/`" — actually that's a frontend-specialist call, leaving it.
- Brief §11.20 mentions "settlement statement, report, contract stub" carry sign buttons. My §5.5 only shows settlement_statements. Stage 2 should confirm sign workflow covers all three document types — adding as delegated question.
- Brief §11.27-31 are POLISH (defer-OK). I did not call out which acceptance criteria are POLISH vs MVP in §3 component table. Not load-bearing for topology, but Stage 2 should preserve the distinction in its FMEA.

### 10.3 Where I waved my hands

- **§3.7 synth generator** — I say "modelling cap-pinning" but don't specify the *mechanism*. Stage 2 must spec: distribution of evening-peak hours that hit cap (e.g., 40% with probability tied to a deterministic "demand stress" flag per day). Flagged in §9.2 item 7.
- **§3.10 AI classifier** — the regex + BoW choice is hand-wavy. Stage 2 must spec: do we use scikit-learn TF-IDF? sentence-transformers (no, that's an LLM-adjacent dependency)? or strict pattern table? The hard constraint "no LLM" rules out sentence-transformers; suggest **a pattern table + small handcrafted lexicon** is the right answer. Flagging for AI Agents specialist.
- **§3.11 voice agent** — Web Speech API support for Ukrainian voice varies by browser. Stage 2 must verify: Chrome on Windows yes, Safari iOS no. Fallback strategy needed.
- **§7 R1 noisy-neighbor mitigation** — "explicit CPU + memory limits" without numbers. Stage 2 must commit numbers (suggested 2 CPU / 2 GB RAM based on Zhytomyr's published needs).
- **§7 R3 Cloudflare header strip** — I assert Cloudflare strips some headers; need verification that `X-Tenant-Id` is not on a default deny list. Stage 2 must test.

### 10.4 Items the next stage MUST resolve (extracted as a checklist)

- [ ] Lock the synth-generator's exact distribution for РДН evening-peak cap-pinning probability per day.
- [ ] Lock the AI classifier implementation mechanism (pattern table + lexicon, no embeddings model).
- [ ] Lock Web Speech API fallback for unsupported browsers (canned recorded MP3? text-only response?).
- [ ] Lock Postgres CPU/RAM resource limits in docker-compose.
- [ ] Confirm Cloudflare proxy passes `X-Tenant-Id` header (and add transform rule if not).
- [ ] Decide forecast submission `DRAFT → SUBMITTED → ACK` mechanism (client poll + server status-computed-on-read is my recommendation).
- [ ] Confirm sign-stub workflow extends to settlement + report + contract document types (per brief §11.20).
- [ ] Decide which 5 of 9 surfaces ship for `/c-i/*` and `/storage/*` (frontend specialist's call once they exist).

### 10.5 Things I would add in a second pass (time permitting)

- A **dependency graph** between the synth-generator output tables (asset → telemetry → market → settlement) showing causal ordering for seed.
- A **timing diagram** for the deploy sequence (DNS propagation vs first synth run vs Vercel cutover) — this is a Stage-2 runbook anyway.
- An explicit **performance budget per surface** (`/producer/` < 1.5s; `/developer/api/explorer` < 2s; `/admin/*` < 2s) — brief §11.25 says "loading under 1.5s on a fresh tab" but I'd refine per surface.
- A **diff against v1** — explicitly what is reused (chart components, portal pattern, type structure per brief §13 assumptions) and what is rewritten. This belongs in Stage 2's implementation plan but is worth noting here.

### 10.6 Self-assessment

This document services PROGRESS.md Stage 1's deliverable spec (system topology + component boundaries + tech choices + data flow + risks + hand-off). Density is around 11 pages markdown — within the 6-12 page target. Every section earns its space; no English fluff. Each major component is tagged to at least one acceptance criterion. The hand-off list is concrete enough that the Detailed Architect can sit down and start working without re-deriving any topology decision.

**Confidence in topology lock: high.** **Confidence in data-shape sketches: medium (Stage 2 finalizes).** **Confidence in synth-generator parameterisation: needs Stage-2 work.**

---

*End of HIGH_LEVEL_ARCHITECTURE v0.1.*
