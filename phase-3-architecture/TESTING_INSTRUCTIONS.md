# TESTING_INSTRUCTIONS — GECKO VPP v2

**Owner:** Testing lead (Operations Specialist Lead bundle).
**Authoritative source:** `ARCHITECTURE.md` §10 (Testing strategy), §10.7 (CI gate summary), §11 FMEA where detection = "smoke" or "CI".
**Brief reference:** `PRODUCT_BRIEF.md` §11.24 (Smoke pass), §11.25 (Production-fidelity feel — load < 1.5s, no fake moments).
**Status:** v0.1 — 2026-05-23. Frozen for Phase 4 execution.

---

## 0. Goal

Four-layer testing pyramid covering the four kinds of mistake the demo can suffer:

1. **Smoke** (Playwright) — does the user see anything? Does it render in both themes without console errors?
2. **Unit** (vitest + pytest) — do the small pieces behave (classifier intent picking, design-token resolution, synth determinism, currency formatting)?
3. **Contract** (Spectral + SDK build) — does the OpenAPI spec stay consistent with the implementation, and do both SDKs still build from it?
4. **Data coverage** (`sniff_test.py`) — does the seeded synthetic dataset actually contain a row for each acceptance criterion that needs one (§11.4, §11.11, §11.12, §11.19, §11.20, §11.21, §11.22, §11.27 if polish ships)?

If any of the four layers is red, deploy is blocked.

---

## 1. Success criteria (verifiable)

| # | Criterion | Evidence |
|---|---|---|
| T1 | Playwright smoke suite passes against deploy preview on every PR — all persona surfaces return 200, both themes render, no console errors | `pnpm -F web test:smoke` exit 0; GitHub Actions check green |
| T2 | Unit-test coverage ≥ 60% on `apps/api/app/agents/classifier.py`, `apps/web/lib/theme.ts`, `apps/web/lib/format-uah.ts`, `apps/synth/synth/` | `pytest --cov=app.agents --cov-report=term`; `vitest run --coverage` |
| T3 | OpenAPI lint clean via Spectral; both SDKs build from spec without manual edits | `spectral lint packages/openapi/openapi.json`; `pnpm -F sdk-ts build`; `uv run --package gecko-vpp build` |
| T4 | Example scripts in `packages/sdk-ts/src/examples/` and `packages/sdk-py/gecko_vpp/examples/` execute end-to-end against local FastAPI | `make sdk-examples-test` |
| T5 | Data coverage report `synth_coverage.md` has ✅ on every applicable §11 row; CI blocks on ❌ | `apps/synth/synth/sniff_test.py` exit 0; report committed and reviewed by Testing lead |
| T6 | Integration test `test_rls_isolation.py` passes (two-connection RLS check) | shared with Security; runs in same CI job |
| T7 | Optimiser determinism test: same `inputs_hash` → same `recommendations` | `pytest apps/api/tests/unit/test_optimiser_determinism.py` |
| T8 | КЕП-stub watermark mandatory test: `<KEPSignBadge>` without `demo={true}` throws | `pnpm -F web test:smoke -- --grep "kep-watermark"` |
| T9 | Cmd+K command palette: typing "акти" + Enter navigates to `/producer/aktyvy/` | smoke step 4 (ARCHITECTURE.md §10.1) |
| T10 | Theme toggle: server-side `data-theme` swap with no FOUC on first paint | smoke step 2 (ARCHITECTURE.md §10.1); visual-diff against golden screenshot |

All 10 green → testing harness DONE.

---

## 2. Tools (locked)

| Tool | Layer | Purpose |
|---|---|---|
| `@playwright/test` | Smoke | E2E browser tests against deploy preview + local stack |
| `vitest` + `jsdom` | Unit (frontend) | Vite-native unit tests for React utils, hooks, formatters |
| `pytest` + `pytest-asyncio` | Unit (backend) | Async FastAPI/asyncpg unit tests |
| `pytest` + `testcontainers` | Integration | Spins up real Postgres in Docker; runs migrations; asserts RLS, FKs, partition behaviour |
| `Spectral` (`@stoplight/spectral-cli`) | Contract | OpenAPI lint with our ruleset |
| `openapi-typescript` | Contract | TS SDK type generation from spec — build-step regenerates and asserts no diff |
| `openapi-python-client` | Contract | Python SDK type generation |
| Custom `sniff_test.py` | Data coverage | Asserts each §11 criterion has supporting rows |
| `Lighthouse CI` | Performance (warn-only) | LCP / TBT budget tracking per §11.25 |
| `axe-core` | Accessibility (warn-only) | Color-contrast violations on both themes |

No paid services. No BrowserStack — Playwright runs Chromium / Firefox / WebKit in Docker on GitHub Actions runners.

---

## 3. Test suites — detailed

### 3.1 Smoke (Playwright) — `apps/web/tests/smoke.spec.ts`

Per ARCHITECTURE.md §10.1.

**Scenarios:**

1. **Every persona surface URL returns 200 and renders without console errors.** Iterates over the 29-route list and asserts: status 200, page has visible `<h1>` or `data-testid="page-loaded"` sentinel, `console.error` count = 0 during render, no React hydration warnings.
   - Routes: `/`, `/producer/*` (9), `/c-i/*` (5), `/storage/*` (5), `/developer/*` (6), `/admin/*` (3), `/about/credentials`.
2. **Both themes render on `/producer/`, `/c-i/`, `/storage/`, `/admin/engage/`.** Toggle via topbar, assert `data-theme` swap on `<html>`, take screenshot, run `axe-core.run()` and assert no contrast violations.
3. **Tenant switcher works.** Open switcher on `/producer/`; click `ci-1`; assert URL still `/producer/` and KPI tile values changed (compare innerText before/after).
4. **Command palette.** Press `Ctrl+K` on `/producer/`; type `акти`; press Enter; assert URL `/producer/aktyvy/`.
5. **КЕП signing.** Visit `/producer/zvity/`; click first report card's sign button; assert `<KEPSignBadge>` appears with `data-testid="kep-demo-watermark"` containing the literal text "DEMO".

```typescript
// apps/web/tests/smoke.spec.ts (excerpt)
import { test, expect } from "@playwright/test";

const ROUTES = [
  "/",
  "/producer/", "/producer/aktyvy/", "/producer/prognozy/",
  "/producer/dyspetcheryzatsiya/", "/producer/rynok/", "/producer/uze/",
  "/producer/spovishchennya/", "/producer/zvity/", "/producer/nalashtuvannya/",
  "/c-i/", "/c-i/aktyvy/", "/c-i/prognozy/", "/c-i/rynok/", "/c-i/zvity/",
  "/storage/", "/storage/aktyvy/", "/storage/uze/", "/storage/rynok/", "/storage/zvity/",
  "/developer/", "/developer/api/explorer", "/developer/sdk-ts/",
  "/developer/sdk-py/", "/developer/webhooks/", "/developer/auth/",
  "/admin/engage/", "/admin/operate/", "/admin/analyze/",
  "/about/credentials",
];

for (const path of ROUTES) {
  test(`route ${path} returns 200 and renders without errors`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", msg => { if (msg.type() === "error") errors.push(msg.text()); });
    const resp = await page.goto(path);
    expect(resp?.status()).toBe(200);
    await page.waitForSelector("[data-testid='page-loaded'],h1");
    expect(errors, `console errors on ${path}: ${errors.join(" | ")}`).toEqual([]);
  });
}
```

Smoke target URL is parametrised via env:
- Local dev: `BASE_URL=http://localhost:3000`
- CI on PR: deploy-preview URL from Vercel
- Production verification: `BASE_URL=https://gecko.radai-1984.dev`

### 3.2 Unit tests — backend (`apps/api/tests/unit/`)

Per ARCHITECTURE.md §10.2 + FMEA F07, F11, F20.

**Coverage targets:**

| File under test | Test file | Asserts |
|---|---|---|
| `app/agents/classifier.py` | `test_classifier_gold_set.py` | 30-question gold-set fixture; each question routes to expected intent code |
| `app/agents/intents/*.py` | `test_intent_sql_shape.py` | Each intent SQL template runs against fixture DB and returns expected shape (column names, row count > 0) |
| `app/ems/optimiser/engine.py` | `test_optimiser_determinism.py` | Same `inputs_hash` → identical `recommendations` array (byte-equal JSON) |
| `app/regulatory/services/kep_stub.py` | `test_kep_stub.py` | SHA-256 of document content is real (re-computable); other fields (signer, timestamp) are stubbed; `is_demo_stub=True` |
| `app/regulatory/services/forecast_status.py` | `test_forecast_auto_advance.py` | Status auto-flips from `PENDING` → `ACK` on read after threshold time (no worker needed; on-read state machine) |
| `app/core/db.py` | `test_set_local_tenant.py` | `get_db_conn` dependency successfully sets `app.tenant_id` per request and releases connection clean |

**Determinism contract.** Optimiser test:

```python
# apps/api/tests/unit/test_optimiser_determinism.py
async def test_optimiser_deterministic_on_fixed_inputs(client_with_seeded_db):
    inputs = {"horizon_hours": 24, "battery_id": "<fixture-uuid>"}
    r1 = await client_with_seeded_db.post("/api/v1/ems/optimise", json=inputs)
    r2 = await client_with_seeded_db.post("/api/v1/ems/optimise", json=inputs)
    assert r1.json()["data"]["inputs_hash"] == r2.json()["data"]["inputs_hash"]
    assert r1.json()["data"]["recommendations"] == r2.json()["data"]["recommendations"]
```

### 3.3 Unit tests — frontend (`apps/web/tests/unit/`)

Per ARCHITECTURE.md §10.2.

| File under test | Test file | Asserts |
|---|---|---|
| `lib/theme.ts` | `theme.test.ts` | `resolveToken("color.bg.primary", "light")` returns `var(--gecko-bg-primary-light)`; same for dark |
| `lib/format-uah.ts` | `format-uah.test.ts` | `formatUah(123456.78)` → `"123 456,78 грн"` (uk-UA locale) |
| `lib/tenant.ts` | `tenant.test.ts` | `getTenantFromCookie` returns valid UUID; defaults to producer-1 on missing cookie |
| `components/charts/HourlyChart.tsx` | `hourly-chart.test.tsx` | Cap-pinning detection: when `prices[h] === cap[h]`, the cap-pinning indicator is rendered |
| `components/palette/CommandPalette.tsx` | `palette.test.tsx` | Fuzzy search: typing "акти" matches "Активи" before "Налаштування" |

Coverage threshold: ≥ 60% lines on the files above. CI fails below.

### 3.4 Integration tests (`apps/api/tests/integration/`)

Per ARCHITECTURE.md §10.3.

- `conftest.py` spins up Postgres 16 via `testcontainers`, applies all alembic migrations via `gecko_migrate` role, then connects FastAPI test client via `gecko_api`.
- `test_rls_isolation.py` — open two psycopg connections with different `app.tenant_id`; assert tenant A SELECT returns 0 rows for tenant B's data on each of the 27 RLS-enabled tables (shared with Security; see SECURITY_INSTRUCTIONS §1 S1).
- `test_admin_bypass.py` — with `app.is_admin='true'`, SELECT from `core.assets` returns 24–36 rows (cross-tenant); without it returns only one tenant's slice.
- `test_endpoint_envelope.py` — every endpoint listed in ARCHITECTURE.md §4 returns canonical `{data, meta}` envelope on success and `{error}` on documented failures.
- `test_partitioned_telemetry.py` — INSERT into `dispatch.telemetry` for 2026-04 and 2026-05 dates lands in the right partition (FMEA F16).

### 3.5 Contract tests

Per ARCHITECTURE.md §10.4.

1. **OpenAPI dump.** CI job runs `python -m apps.api.app.main --dump-openapi > packages/openapi/openapi.json` and `git diff --exit-code packages/openapi/openapi.json`. If a router renamed an operation, the diff is non-empty → CI fails → auto-PR opens with the regenerated spec.
2. **Spectral lint.** `spectral lint packages/openapi/openapi.json --ruleset packages/openapi/.spectral.yaml`. Ruleset extends `spectral:oas` and adds:
   - Every operation has `operationId` matching `^(core|market|dispatch|ems|regulatory|agents|audit)\.[a-z_]+\.(list|get|create|update|delete|sign|submit|optimise)$`.
   - Every response has a documented schema (no `application/json` without `$ref`).
   - Every endpoint documents the `X-Tenant-Id` header parameter.
3. **SDK build.** `pnpm -F sdk-ts build` runs `openapi-typescript packages/openapi/openapi.json -o packages/sdk-ts/src/generated/api.d.ts` then `tsup`. Build failure → CI fails (FMEA F12).
4. **SDK example execution.** Both `examples/sdk-ts/list-assets.ts` and `examples/sdk-py/list_assets.py` run against `http://localhost:8000` in CI after backend boot. Assertions:
   - Response has `data` array of assets
   - Each asset has `id`, `name`, `eic_code`, `capacity_mw`
   - `eic_code` matches the regex from ARCHITECTURE.md §3.11.5

### 3.6 Data coverage tests (`apps/synth/synth/sniff_test.py`)

Per ARCHITECTURE.md §10.5 + §3.11.5.

Runs after `docker compose run --rm synth`. Emits `phase-3-architecture/synth_coverage.md`. Asserts:

| Acceptance § | Assertion |
|---|---|
| §11.4 | At least 8 rows in `core.assets` with valid EIC + capacity ∈ (1, 20] МВт |
| §11.11 | `core.eic_codes` has ≥ 1 row each of EIC types Y, X, W, V; all `CHAR(16)` matching regex |
| §11.12 | Asset names are Cyrillic; prices in `market.*` are denominated `UAH`; all timestamps EET (`+02:00`/`+03:00` DST handled by `interval_start TIMESTAMPTZ`) |
| §11.19 | `regulatory.forecast_submissions` has ≥ 60 rows, ≥ 1 with status `ACK` |
| §11.20 | `regulatory.signed_documents` has ≥ 12 rows of `document_type='SETTLEMENT_ACT'` with `is_demo_stub=TRUE` |
| §11.21 | `market.rdn_prices` ≥ 2160 (30d × 24h × 3 tenants); `market.vdr_trades` ≥ 2700; `market.br_settlements` ≥ 2160; `market.dd_contracts` ≥ 15 |
| §11.22 | `ems.kpi_daily` rows have `co2_avoided_tn > 0` for each producer/storage tenant-day |
| §11.27 (polish) | ≥ 1 curtailment event row; ≥ 1 imbalance settlement above mean threshold |

**Sniff invariants** (architectural, not §11):

- Every РДН hour 17:00–21:00 on a "capped" day: `is_capped=TRUE` AND `price_uah_mwh = cap_uah_mwh`.
- Every battery SOC reading: 10 ≤ `soc_pct` ≤ 90.
- Every EIC matches `^10[YXWVTZ][A-Z0-9-]{12}[A-Z0-9]$`.
- Every settlement line: `amount_gross_uah ≈ amount_net_uah × (1 + vat_rate)` within ±0.01.
- Negative РДН price day exists (around 2026-05-04 per §3.11.3.8).
- Planned maintenance event injected (producer-1 ВЕС, 2026-05-08 to 2026-05-12).
- At least 1 ancillary activation row.

```python
# apps/synth/synth/sniff_test.py (shape)
def run_all(conn):
    failures = []
    coverage = {}
    failures += check_eic_format(conn, coverage)
    failures += check_capped_hours_consistency(conn, coverage)
    failures += check_acceptance_criteria(conn, coverage)
    write_coverage_md(coverage, path="phase-3-architecture/synth_coverage.md")
    if failures:
        for f in failures: print(f"FAIL: {f}", file=sys.stderr)
        sys.exit(1)
```

### 3.7 What NOT to test (per ARCHITECTURE.md §10.6)

- Real LLM accuracy — no real LLM in default config.
- Real KEP crypto — stub only.
- Real market connectors — never connect to UEEX, СОП, Укренерго.
- Safari iOS Web Speech API quirks — Voice agent stub falls back to text-only on unsupported browsers; we accept the fallback.
- Lighthouse > budget — warn only, not blocking (per §10.7).

### 3.8 Performance (`apps/web/tests/perf/`)

Per PRODUCT_BRIEF §11.25 — "production-fidelity feel; loading under 1.5s on a fresh tab".

- Lighthouse CI runs against deploy preview on every PR.
- Budgets (warn-only):
  - LCP < 1.5s on `/`
  - LCP < 2.0s on `/producer/`, `/c-i/`, `/storage/`
  - LCP < 2.0s on `/developer/api/explorer` (Scalar bundle is heavy — FMEA F19; lazy-load below the fold)
  - TBT < 200ms on `/`
- Warn-only because: a one-off Vercel cold start can blow the budget; we don't want CI to be flaky over this. But we **track** it and if main regresses by > 30% from baseline, the lead is paged.

---

## 4. CI pipeline

Per ARCHITECTURE.md §10.7. Single GitHub Actions workflow at `.github/workflows/ci.yml`. Triggers: PR + push to `main`.

### 4.1 Job graph

```
lint
├── lint.python   (ruff, mypy, bandit, import-linter)
├── lint.frontend (tsc, eslint with no-hex + no-danger, prettier --check)
├── lint.secrets  (gitleaks)
└── lint.openapi  (spectral)
        │
        ▼
build
├── build.api     (docker build apps/api)
├── build.synth   (docker build apps/synth)
├── build.web     (pnpm -F web build)
├── build.sdk-ts  (pnpm -F sdk-ts build; openapi-typescript)
└── build.sdk-py  (uv build packages/sdk-py)
        │
        ▼
test
├── test.unit.backend  (pytest apps/api/tests/unit)
├── test.unit.frontend (vitest)
├── test.integration   (pytest apps/api/tests/integration with testcontainers Postgres)
└── test.data-coverage (synth → sniff_test.py)
        │
        ▼
test.smoke (Playwright against deploy preview)
        │
        ▼
contract.sdk-examples (run sdk-ts and sdk-py example scripts against local API)
        │
        ▼
deploy-ready ✓
```

### 4.2 Branch protection (GitHub)

`main` is protected:
- Required checks: `lint.*`, `build.*`, `test.unit.*`, `test.integration`, `test.data-coverage`, `test.smoke`, `contract.sdk-examples`.
- No direct push to `main`. PR only.
- Linear history (squash merge).
- Up-to-date branch required before merge.

### 4.3 Concurrency control

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

A new push to a PR cancels the previous run — saves runner minutes.

### 4.4 Secret handling in CI

- No secrets needed for unit/integration/smoke (testcontainers Postgres uses ephemeral password).
- Deploy job (separate workflow `deploy.yml` triggered on push to `main`) uses GitHub Actions secrets:
  - `VERCEL_TOKEN` — set by user via gh CLI; not committed.
  - `HETZNER_SSH_KEY` — used to ssh and `docker compose pull && up -d` on the VPS.
  - `CLOUDFLARE_API_TOKEN` — same value as `~/.cloudflare/api-token` on user's machine.
- All secrets accessed only via `${{ secrets.X }}` in workflow YAML. Never echoed to logs.

---

## 5. Pre-flight + Branching protocol

### 5.1 Pre-flight (the user's 4 questions)

Before starting any testing work, write in the PR description:

1. **What does success look like?** All 10 T-criteria in §1 green. Smoke covers the 29 routes in both themes; unit ≥ 60% coverage; OpenAPI lint clean; SDKs build; data coverage report all ✅.

2. **What inputs do I have?** ARCHITECTURE.md §10 (full testing spec), §11 FMEA (which detections live in tests), §3.11.5 (sniff-test invariants), §4 (endpoints whose envelopes must be tested), `docs/agents-gold-set.md` (30-question fixture — written by AI agents lead in Phase 4.8). PRODUCT_BRIEF §11.24, §11.25.

3. **What is the smallest, safest first move?** Write the route-200 smoke test (scenario 1 above) **first** — that single test reveals every routing/hydration regression cheaply. Even before all routes are implemented, this test runs as `test.skip` for missing routes and as `test()` for ones the Frontend lead has shipped. Frontend lead removes `skip` as they land each route.

4. **What could go wrong, and what's my rollback?** Flaky Playwright tests waste CI minutes. Mitigation: deterministic test data via the synth generator's fixed RNG seed; explicit `waitFor` selectors not arbitrary timeouts; per-test `console.error` capture (don't rely on aggregate); retries `retries: 2` on CI only, never local. If a test becomes flaky, **mark it `test.fixme` not `test.skip`** so it shows in the report; open an issue same day; fix within 24h or remove the test.

### 5.2 Branching protocol

- Branch name: `test/<area>` — e.g. `test/playwright-smoke`, `test/openapi-spectral`, `test/sniff-test`.
- Each test PR is also an audit of the implementation it tests — if the test reveals a bug, the test PR includes the fix.
- Commits: `test(<area>): <what>` per global git rules; ends with the co-author line.

---

## 6. Operations runbook

### 6.1 Test is failing on CI but passes locally

Likely culprits in order of probability:
1. **Different Postgres version.** testcontainers pins `postgres:16-alpine`. Local dev compose pins the same. If different → fix.
2. **Time-of-day dependency.** A test that uses `datetime.now()` may pass before midnight, fail after. Replace with `freezegun` to pin to `2026-05-23T12:00:00+02:00`.
3. **RNG not seeded.** Some test path uses Python's `random.random()` directly instead of the synth's seeded RNG. Trace via `pytest --tb=short -p no:randomly`.
4. **Race condition on testcontainers boot.** Add `wait_for_logs(container, "database system is ready to accept connections")` before any test runs.

### 6.2 Playwright is flaky on `test.smoke`

1. First run `pnpm test:smoke --headed` locally to watch. If you see a navigation race or a button-not-yet-attached error, that's the bug.
2. Replace `page.click("button")` with `page.getByRole("button", { name: /Підписати/ }).click()`.
3. Use `page.waitForLoadState("networkidle")` only as last resort — prefer explicit selectors.
4. If a test stays flaky for 24h: `test.fixme(...)`, file issue, fix or delete the same week.

### 6.3 sniff_test.py reports ❌ on a §11 criterion

This is a **deploy block**, per FMEA F15.

1. Read `synth_coverage.md` to see which criterion has no rows.
2. Open `apps/synth/synth/<area>.py` (e.g. `regulatory.py` for §11.20) — likely event injection logic is mis-keyed.
3. Fix the synth generator; rerun `docker compose run --rm synth`.
4. Re-check `synth_coverage.md`; commit fix.

Don't relax the assertion to make the test green. The assertion exists to catch this exact bug.

### 6.4 OpenAPI spec drift (FMEA F12)

CI dumps the spec; if it differs from committed `packages/openapi/openapi.json`, an auto-PR opens with the regeneration. The Backend lead reviews and merges. If the diff is unexpected (endpoint accidentally renamed), revert the offending source change.

### 6.5 Coverage drops below 60%

CI fails. The PR author either:
- Adds tests to reach 60% on the new code paths.
- Justifies the exclusion in PR description and adds the file to `coverage.exclude`. Only accepted for: generated code, vendor, test-only helpers.

---

## 7. Self-review checklist

Before declaring Testing phase done:

- [ ] `apps/web/tests/smoke.spec.ts` exists and asserts all 5 scenarios in §3.1
- [ ] `apps/web/tests/unit/` has the 5 frontend unit tests in §3.3
- [ ] `apps/api/tests/unit/` has the 6 backend unit tests in §3.2
- [ ] `apps/api/tests/integration/conftest.py` boots Postgres via testcontainers
- [ ] `test_rls_isolation.py` and `test_admin_bypass.py` exist and pass
- [ ] `apps/synth/synth/sniff_test.py` written; emits `synth_coverage.md`; covers every row in the table in §3.6
- [ ] `packages/openapi/.spectral.yaml` ruleset committed; CI runs `spectral lint`
- [ ] OpenAPI dump-and-diff CI step works (auto-PR on drift)
- [ ] Both SDK builds succeed in CI; example scripts execute against local API
- [ ] `.github/workflows/ci.yml` matches the job graph in §4.1
- [ ] `main` branch protection requires all green checks
- [ ] Lighthouse CI runs warn-only with budgets per §3.8
- [ ] Coverage threshold ≥ 60% enforced for the files in §3.2 and §3.3
- [ ] `test.fixme` policy documented; no `test.skip` on the main branch except for known v3 features

If every box is checked → Testing phase DONE.

---

## 8. Done definition

Testing phase is **DONE** when:

1. All 10 success criteria in §1 are green and stay green on `main` for ≥ 2 consecutive merges.
2. All 13 self-review items in §7 are checked.
3. CI badges in `README.md`: `[![CI](https://github.com/basisabp1984/gecko-vpp-rebuild/actions/workflows/ci.yml/badge.svg)](...)`.
4. Test failures over the previous 7 days have a root-cause analysis in `difficulties_log.md` (so we learn from flakes, not paper over them).

Append to PROGRESS.md:

```
- 2026-05-23 — Stage 4.12 (Testing harness) DONE. Output: smoke.spec.ts, unit tests (backend + frontend), sniff_test.py, .spectral.yaml, ci.yml workflow.
  All 10 success criteria green. CI badges in README. Coverage 67% on classifier + 71% on theme resolver.
```
