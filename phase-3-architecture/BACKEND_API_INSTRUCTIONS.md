# BACKEND_API_INSTRUCTIONS — GECKO VPP v2

**Owner:** Backend API sub-lead (Stage-3 specialist; executes Phase 4.3 + 4.7 of `ARCHITECTURE.md §12`).
**Parent contracts:** `ARCHITECTURE.md` §4 (all 30+ endpoints), §6 (backend architecture, module boundaries, import-linter), §11 FMEA rows F01/F02/F12/F20, §14.2 (this lead's checklist), §13 (deploy seams that backend exposes).
**Prerequisite:** `BACKEND_DB_INSTRUCTIONS.md` is green — schemas + RLS + synth data exist before the first endpoint is wired.
**Length:** ~7 pages.

---

## 1. Goal

Build the FastAPI process that sits behind Caddy at `api.gecko.radai-1984.dev`. **One Python process, six sub-system modules** (`core`, `market`, `dispatch`, `ems`, `regulatory`, `agents`, plus `audit` cross-cutting + `admin` router-only), every endpoint in `ARCHITECTURE.md §4` implemented and conformant to the canonical JSON envelope. The OpenAPI 3.1 spec emitted at `/openapi.json` is the single source of truth for both SDKs (per `SDK_INSTRUCTIONS.md`); it must lint clean under Spectral. Sub-system module isolation enforced by `import-linter` in CI.

The process serves three audiences:
1. The Next.js route handlers (the only production caller). Adds `X-Tenant-Id` header server-side from the cookie.
2. The TS + Py SDKs (consume `packages/openapi/openapi.json`).
3. The dev portal's Scalar embed (reads the same committed JSON).

---

## 2. Success criteria (binary checklist)

- [ ] `uvicorn app.main:app` boots without warnings; `GET /openapi.json` returns a valid OpenAPI 3.1 document.
- [ ] **Every endpoint** listed in `ARCHITECTURE.md §4.2 through §4.10` is reachable with the expected method + path. Count target: ≥30 (30+ per architect).
- [ ] Every successful response wraps payload in `{"data": ..., "meta": {request_id, tenant_id, generated_at}}` (per §4.1).
- [ ] Every error response is `{"error": {"code": ..., "message": ..., "details": ...}}` and `code` ∈ the canonical 7 (§4.1).
- [ ] Monetary fields are **numeric strings** in JSON; timestamps **ISO 8601 with Europe/Kyiv offset** (`+03:00`); pagination defaults `page=1&per_page=50` (max 200).
- [ ] `X-Tenant-Id` injection: missing header → 400 `MISSING_TENANT_HEADER`; unknown UUID → 400 `INVALID_TENANT`.
- [ ] RLS works through the API: same endpoint with two different `X-Tenant-Id` headers returns disjoint data (integration test).
- [ ] `import-linter` (`uv run lint-imports`) passes against the contract in `apps/api/importlinter.cfg`; CI blocks merge on violation.
- [ ] `spectral lint packages/openapi/openapi.json` passes against `.spectral.yaml` (every operation has `operationId` + tags; every 4xx response references canonical error codes; monetary fields carry unit suffix).
- [ ] OpenAPI dump step (`scripts/dump_openapi.py`) writes `packages/openapi/openapi.json` deterministically; CI auto-PRs on diff.
- [ ] `@cross_tenant` decorator only appears on routes whose path matches `^/api/v1/admin/` (CI grep test).
- [ ] Optimiser endpoint returns within 2 s on synthetic data; same inputs → same `inputs_hash` → same `recommendations` (determinism test).
- [ ] Forecast-submission status flips **on read** (server-computed; no background worker) per `ARCHITECTURE.md §3.6.1` and §6 lock.
- [ ] КЕП stub endpoint always sets `is_demo_stub=TRUE` and returns a badge object exactly per §4.7 shape.
- [ ] Caddy snippet `infra/caddy/gecko-api.caddy` is reviewable and matches §9.4.
- [ ] Pre-flight check (§9 below) all YES before code begins.

---

## 3. Tools (verify available before starting)

| Tool | Purpose | Pin / version |
|---|---|---|
| Python 3.12 | runtime | matches DB phase |
| FastAPI | web framework | `>=0.110,<1.0` (OpenAPI 3.1 support stable since 0.99) |
| Pydantic v2 | request/response schemas | `>=2.7,<3` |
| SQLAlchemy 2.0 async | ORM/core (the architect chose this over raw psycopg; we follow) | `>=2.0,<2.1` |
| `asyncpg` | async DB driver | `>=0.29` |
| `uvicorn[standard]` | ASGI server | latest stable |
| `import-linter` | cross-module import contract enforcement | `>=2.0` |
| `ruff` + `mypy` | lint + type | latest |
| `pytest` + `pytest-asyncio` + `httpx` + `testcontainers[postgres]` | tests | latest |
| `@stoplight/spectral-cli` | OpenAPI linter (CI gate) | latest |
| `jinja2` | agent response templates (this file references them; AI agents lead owns content) | `>=3` |

**Why not aiohttp / starlette directly?** `ARCHITECTURE.md §6` locked FastAPI (Zhytomyr-proven path; auto-OpenAPI; tight Pydantic v2 integration). Do not re-litigate.

---

## 4. Step-by-step plan

### Phase A — App skeleton

**Step 1. FastAPI app structure** per `ARCHITECTURE.md §6.1`.

Create `apps/api/app/main.py`:
- Instantiate `FastAPI(title="GECKO VPP API", version="1.0.0", openapi_version="3.1.0", docs_url=None, redoc_url=None)`. Disable built-in `/docs` and `/redoc` — the dev portal serves Scalar instead (HLA D9).
- Lifespan context manager creates the asyncpg pool (`min_size=2`, `max_size=20`; cite F01 mitigation) and tears it down on shutdown.
- Register exception handlers for `GeckoError` subclasses (see Step 6).
- Register the canonical envelope middleware (see Step 5).
- Include 8 routers (one per sub-system + auth + assets aggregate + admin):
  - `core.routers.auth.router` at `/api/v1/auth`
  - `core.routers.assets.router` at `/api/v1/assets`
  - `market.routers.aggregate.router` at `/api/v1/market`
  - `dispatch.routers.aggregate.router` at `/api/v1/dispatch`
  - `ems.routers.aggregate.router` at `/api/v1/ems`
  - `regulatory.routers.aggregate.router` at `/api/v1/regulatory`
  - `agents.routers.aggregate.router` at `/api/v1/agents`
  - `admin.routers.aggregate.router` at `/api/v1/admin`

**Step 2. Pydantic v2 schemas** under each module's `schemas/` folder. Folder is **internal** — only `<module>/public.py` re-exports what other modules may consume (the import-linter contract in §6.4 of `ARCHITECTURE.md`). One file per logical group:

```
apps/api/app/<module>/schemas/
├── __init__.py        # exports nothing (forces explicit imports)
├── requests.py        # *Request models
└── responses.py       # *Response models
```

Naming convention:
- `RDNPriceResponse`, `BidSubmitRequest`, `OptimisationRunRequest`, `KEPSignBadgeResponse`.
- All monetary fields → `condecimal(max_digits=14, decimal_places=2)` rendered as JSON **string** via `model_config = {"json_encoders": {Decimal: str}}` and `Field(..., serialization_alias=...)` where needed.
- All timestamps → `datetime` annotated with custom serializer producing `2026-05-23T14:32:11+03:00` (Europe/Kyiv offset).

**Step 3. DB session + RLS injection** — `apps/api/app/db.py`.

The dependency is the load-bearing security control (§9.2 + §11 F06). Sketch:

```python
async def get_db_conn(
    tenant_id: UUID = Depends(tenant_dep),
    is_admin: bool = Depends(admin_dep),
) -> AsyncIterator[AsyncConnection]:
    async with engine.begin() as conn:               # opens transaction (REQUIRED for SET LOCAL)
        await conn.execute(text("SET LOCAL app.tenant_id = :t"), {"t": str(tenant_id)})
        if is_admin:
            await conn.execute(text("SET LOCAL app.is_admin = 'true'"))
        yield conn
        # on success, exit commits; on exception, exit rolls back
```

Two FastAPI dependencies feed in:
- `tenant_dep` reads `request.headers["X-Tenant-Id"]`. Missing → `MissingTenantHeader` (400). Not a valid UUID → `InvalidTenant` (400). UUID not in `core.tenants` → `InvalidTenant` (404).
- `admin_dep` returns `True` iff `X-Admin: true` AND `request.url.path.startswith("/api/v1/admin/")`. Anywhere else → ignored.

**Critical:** `SET LOCAL` is transaction-scoped. **Every request must run inside a transaction.** Read-only endpoints still open a transaction (cheap) and commit at the end.

**Step 4. Module pattern + import-linter** (`ARCHITECTURE.md §6.3` + §6.4).

Each module's folder layout is fixed:
```
apps/api/app/<module>/
├── __init__.py        # exports nothing
├── public.py          # the ONLY surface other modules may import
├── routers/           # FastAPI APIRouters (one file per resource group)
├── services/          # business logic
├── repositories/      # SQL (async, parameterised — NO string concat)
└── schemas/           # pydantic v2 models
```

Write `apps/api/importlinter.cfg` exactly as `ARCHITECTURE.md §6.4`. Then `uv run lint-imports` must pass. Add the CI gate to `.github/workflows/ci.yml`.

### Phase B — Cross-cutting infrastructure

**Step 5. Envelope middleware.**

`apps/api/app/core/middleware.py` implements a response wrapper that:
1. Generates a UUIDv4 `request_id` per request, sets it on `request.state`.
2. After the endpoint runs, if the response is a dict/model and not already enveloped, wraps it as `{"data": <body>, "meta": {"request_id": ..., "tenant_id": ..., "generated_at": <ISO>}}`.
3. On exception, lets the `GeckoError` handler format `{"error": {...}}` instead.

**Implementation note:** FastAPI's auto response model unwrapping makes "envelope everything" tricky. Two options:
- (A) Endpoints return raw Pydantic models; middleware re-serializes — fragile, breaks `response_model`.
- (B) Each endpoint returns `Success[T]` typed wrapper via a `response_model=Success[T]` declaration; middleware only handles error envelope. **Pick (B)** — cleaner OpenAPI, no double-serialization. Define generic `Success[T]` in `core.schemas.envelope`.

**Step 6. Exception handlers** per `ARCHITECTURE.md §6.8`. `apps/api/app/core/exceptions.py` defines:
- `class GeckoError(Exception)` with class attrs `code: str`, `http_status: int`, `message: str`.
- Subclasses: `InvalidTenant (400)`, `MissingTenantHeader (400)`, `NotFound (404)`, `ValidationFailed (422)`, `RateLimited (429)`, `InternalError (500)`, `StubNotImplemented (501)`.
- FastAPI handler `@app.exception_handler(GeckoError)` returns the canonical error envelope with `details` optional.
- Also handle `pydantic.ValidationError` → wrap as `ValidationFailed` with `details=err.errors()`.

**Step 7. Tenant injection dependencies** (`core/security.py`).
- `tenant_dep(request: Request) -> UUID`: parse header, fetch `core.tenants` row via a small in-process LRU cache (3 tenants total — cache size 16 is plenty; invalidate on `POST /auth/switch-tenant` is not needed since tenants are static for the demo).
- `admin_dep(request: Request) -> bool`: as in Step 3.
- `@cross_tenant` decorator: emits an `audit.events` row with `event_type='admin.cross_tenant_read'` before yielding control. The decorator wraps the route handler; the dependency-injection system sees an inner function with the same signature.
- CI grep test: every `@cross_tenant` use must live under `apps/api/app/admin/`.

### Phase C — Routers in priority order

Per `ARCHITECTURE.md §12 Phase 4.3` the first 5 endpoints unblock the frontend. Implement in this order:

**Step 8. Read-only endpoints first (unblock Phase 4.4 frontend chrome).**

| Order | Endpoint | Module | Spec ref |
|---|---|---|---|
| 1 | `GET /api/v1/auth/me` | core | §4.2 |
| 2 | `POST /api/v1/auth/switch-tenant` | core | §4.2 |
| 3 | `GET /api/v1/assets` | core | §4.6 |
| 4 | `GET /api/v1/assets/{id}` | core | §4.6 |
| 5 | `GET /api/v1/market/rdn` | market | §4.3 |
| 6 | `GET /api/v1/ems/kpi/portfolio?range=30d` | ems | §4.5 |
| 7 | `GET /api/v1/ems/kpi/daily?date=...` | ems | §4.5 |
| 8 | `GET /api/v1/market/vdr` | market | §4.3 |
| 9 | `GET /api/v1/market/br` | market | §4.3 |
| 10 | `GET /api/v1/market/dd` | market | §4.3 |
| 11 | `GET /api/v1/market/bids` | market | §4.3 |
| 12 | `GET /api/v1/market/revenue?range=30d` | market | §4.3 |
| 13 | `GET /api/v1/dispatch/setpoints` | dispatch | §4.4 |
| 14 | `GET /api/v1/dispatch/telemetry` | dispatch | §4.4 |
| 15 | `GET /api/v1/dispatch/instructions` | dispatch | §4.4 |
| 16 | `GET /api/v1/ems/forecasts` | ems | §4.5 |
| 17 | `GET /api/v1/regulatory/settlements` | regulatory | §4.7 |
| 18 | `GET /api/v1/regulatory/settlements/{id}` | regulatory | §4.7 |
| 19 | `GET /api/v1/regulatory/events` | regulatory | §4.7 |
| 20 | `GET /api/v1/admin/portfolio` | admin | §4.9 |
| 21 | `GET /api/v1/admin/operations` | admin | §4.9 |
| 22 | `GET /api/v1/admin/analytics` | admin | §4.9 |
| 23 | `GET /api/v1/agents/voice/session` | agents | §4.8 |
| 24 | `GET /api/v1/webhooks/event-types` | core (dev-portal helper) | §4.10 |
| 25 | `GET /api/v1/webhooks/sample/{type}` | core | §4.10 |

**Step 9. Then write endpoints (stubs that mutate but with realistic state-flip semantics):**

| Order | Endpoint | Notes |
|---|---|---|
| 26 | `POST /api/v1/market/bids` | INSERT into `market.bids` with `state='ACTIVE'`. State auto-flips to `'ACCEPTED'` on next read after 500 ms — implementation: on every read of a bid row, check `(now() - submitted_at) > interval '500 ms'` AND `state='ACTIVE'` → UPDATE in same connection. Pattern reused for forecast-submission status (#28). |
| 27 | `POST /api/v1/dispatch/setpoints` | Same flip pattern: `pending → acknowledged` after 300 ms on read. |
| 28 | `POST /api/v1/ems/forecasts/submit` | Writes to `regulatory.forecast_submissions` with `status='DRAFT'`. Flips `DRAFT → SUBMITTED` after 200 ms, `SUBMITTED → ACK` after 1000 ms on read (server-computed). |
| 29 | `POST /api/v1/ems/optimise` | See Step 10 (optimiser runner). |
| 30 | `POST /api/v1/regulatory/documents/{ref_table}/{ref_id}/sign` | Generates real SHA-256 of `(ref_table, ref_id, current_doc_json)`, picks signer from fixture pool, writes `regulatory.signed_documents` with `is_demo_stub=TRUE`. Returns badge object per §4.7 (5 fields). |

**Status-flip-on-read pattern** is the key trick. Encapsulate it in `apps/api/app/core/status_flip.py`:
```python
async def flip_if_due(conn, table, id_col, id_val, status_col, transitions: list[tuple[str, str, timedelta]]):
    """Idempotent: if status matches `from`, age > delta, UPDATE to `to`."""
```
Used by bids, setpoints, forecast_submissions. Removes drift between handlers.

**Step 10. Optimiser runner** (`ARCHITECTURE.md §6.6`).

`apps/api/app/ems/optimiser/runner.py`:
- Single pure function `run_optimisation(scenario, horizon_hours, asset_ids, tenant_id, conn) -> OptimisationResult`.
- Determinism: `inputs_hash = sha256(canonical_json({scenario, sorted(asset_ids), horizon_hours, current_day})).hexdigest()`. Seed `random.Random(inputs_hash[:16])` and use only that RNG for any perturbation.
- Read inputs from `core.assets`, `market.rdn_prices` (next `horizon_hours`), `dispatch.telemetry` (last hour per asset).
- Apply scenario-specific perturbation (e.g., `arbitrage` → for each УЗЕ, recommend discharge in top-decile-price hours, charge in bottom-decile).
- Insert one row in `ems.optimisation_runs` with `inputs_hash`, `inputs` (JSONB), `recommendations` (JSONB), `expected_uplift_uah`, `risk_flags`, `confidence_pct`, `duration_ms`.
- Hard timeout 2 s (architect §6.6). If exceeds (shouldn't on synth data) → return partial with `risk_flags=['timeout']` (F20 mitigation).
- Pure Python, no Celery, no asyncio.create_task — synchronous within the request transaction.

**Step 11. Agents endpoint surface (Phase 4.8 owner = AI Agents lead, but the routers + Pydantic skeleton live here).**

Implement only the *routing + envelope* for:
- `POST /api/v1/agents/{persona}/query` — validates `{persona}` against the 4 allowed values; delegates body to `agents.services.classifier_service.classify_and_answer(...)`. The AI Agents lead owns `classifier_service`; this lead provides the router contract + tests for the envelope.
- `GET /api/v1/agents/voice/session` — already in Step 8. Reads `settings.voice_provider`; if `stub` or `OPENAI_API_KEY` absent → returns the stub payload exactly per §4.8 (5 canned scenarios). If `openai-realtime` → calls OpenAI's ephemeral session endpoint, returns the ephemeral token + websocket URL.

**Defensive switch** (HLA §3.11): if `VOICE_PROVIDER=openai-realtime` AND `OPENAI_API_KEY` is empty/missing → force-downgrade to `stub` (log a WARN). User's hard constraint: "no paid API spend without explicit key".

**Step 12. Admin endpoints + `@cross_tenant`.** Per `ARCHITECTURE.md §4.9` + §6.5. Three admin endpoints; each wrapped with `@cross_tenant`. The decorator:
1. Pre-call: emits `audit.events` row.
2. Sets `app.is_admin='true'` on the connection (already handled by `admin_dep` if path matches; decorator is a *redundant guard* that fails closed if `admin_dep` was forgotten).
3. Post-call: nothing (transaction commit clears `SET LOCAL`).

Grep test (`scripts/check_cross_tenant_scope.sh`): `grep -rn "@cross_tenant" apps/api/app/ | grep -v "apps/api/app/admin/"` must be empty.

### Phase D — OpenAPI, lint, CI

**Step 13. OpenAPI dump script.** `apps/api/scripts/dump_openapi.py`:
```python
from app.main import app
import json, pathlib
spec = app.openapi()
pathlib.Path("packages/openapi/openapi.json").write_text(
    json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False)
)
```
Run on every CI build. If diff vs committed → auto-PR (DevOps lead implements the PR-bot wiring; Backend lead just ensures the script is deterministic by sorting keys).

**Step 14. Spectral ruleset** (`.spectral.yaml`) per `ARCHITECTURE.md §6.7`:
- Every operation has `operationId` (auto from FastAPI: `{module}.{resource}.{verb}` — set via `operation_id` on each route or via a globally-installed `generate_unique_id_function`).
- Every operation has ≥1 tag (use the FastAPI `tags=[...]` argument on `include_router`).
- 4xx responses reference one of the 7 canonical error codes.
- Monetary field names end in `_uah`, `_uah_mwh`, `_eur_mwh` or `_eur_mwh_h` (regex enforced).

**Step 15. Caddy snippet** (`infra/caddy/gecko-api.caddy`). Copy verbatim from `ARCHITECTURE.md §9.4`. Includes:
- `reverse_proxy localhost:8000 { header_up X-Real-IP ... X-Forwarded-* }`.
- `rate_limit` block (100 req/min/IP) — F01/F02 + §9.5 mitigation.
- CORS headers allowing `https://gecko.radai-1984.dev`, localhost dev origins, and the headers `Content-Type, X-Tenant-Id, X-Admin`.
- JSON access logs to `/var/log/caddy/gecko-api.log`.

This snippet is imported into the existing Caddyfile by DevOps; this lead's only deliverable is the file content + smoke instruction `curl https://api.gecko.radai-1984.dev/openapi.json` returning 200.

### Phase E — Tests

**Step 16. Unit tests** (`apps/api/tests/unit/`):
- Each Pydantic schema round-trips JSON (validate then dump then re-validate → equal).
- `flip_if_due` is idempotent (running twice with same now → one update).
- Optimiser determinism: 2 runs with identical input → identical `recommendations` and `inputs_hash`.
- КЕП stub: SHA-256 of canonical content matches what's stored in `document_hash_sha256`.
- Envelope middleware: handler returning `{"foo": 1}` becomes `{"data": {"foo":1}, "meta":{...}}`.
- Error envelope: raising `NotFound("asset x")` → `{"error":{"code":"NOT_FOUND",...}}` + HTTP 404.

**Step 17. Integration tests** (`apps/api/tests/integration/`):
- `test_rls_isolation_via_api`: same endpoint, two different `X-Tenant-Id` headers, response sets disjoint.
- `test_missing_tenant_header_returns_400`.
- `test_admin_cross_tenant_sees_all_three`: `GET /api/v1/admin/portfolio` with `X-Admin: true` returns 3 tenants.
- `test_admin_bypass_does_not_work_outside_admin_prefix`: `X-Admin: true` on `/api/v1/assets` does NOT broaden visibility.
- `test_forecast_submission_status_flip_on_read`: POST, immediately GET → `DRAFT`; wait 250 ms, GET → `SUBMITTED`; wait 1.1 s, GET → `ACK`.
- `test_optimiser_under_2_seconds`.
- `test_kep_sign_returns_badge_with_demo_stub_true`.

---

## 5. Convention reminders (cite ARCHITECTURE.md, do NOT relitigate)

- **Envelope:** `{ data, meta }` success; `{ error: { code, message, details } }` error (§4.1).
- **Monetary as strings.** Decimal → str in serializer. Never `float` in the JSON output.
- **Timestamps ISO 8601 with Europe/Kyiv offset** (`+03:00` since our window is post-DST). Use `arrow` or write a custom serializer — pick the lighter option.
- **Pagination:** `?page=1&per_page=50`, max `per_page=200`. `meta.pagination = {page, per_page, total, total_pages}` when applicable.
- **Cache headers** (§4.11): GET = `public, max-age=60, stale-while-revalidate=300`; POST/PATCH/DELETE = `no-store`; `/voice/session` = `no-store`.
- **operationId convention:** `{module}.{resource}.{verb}` (e.g., `market.rdn.list`, `market.bids.submit`). Spectral enforces.
- **SQL parameterisation:** asyncpg `$1/$2/...`. **NEVER** `f"SELECT ... {var}"`. CI grep test for `f"SELECT"` and `f"INSERT"` blocks merge (§9.8).

---

## 6. FMEA rows this file mitigates (cite `ARCHITECTURE.md §11`)

- **F01 (Pool exhausted).** Pool `min_size=2, max_size=20`; health check endpoint `GET /health` returns 503 if pool > 90% used.
- **F02 (OOM on telemetry query).** Hard `LIMIT 1000` on every telemetry GET; `?per_page=200` is the absolute cap.
- **F12 (OpenAPI drift).** CI dump + diff + auto-PR.
- **F20 (Optimiser > 2 s).** Hard timeout 5 s in code; if hit, return partial result with `risk_flags=['timeout']`.

---

## 7. §11 acceptance criteria this file's domain services

- **§11.2** — `/auth/switch-tenant` endpoint.
- **§11.4** — every endpoint backing 9 producer surfaces.
- **§11.6** — `/admin/*` endpoints.
- **§11.8** — sub-system Python module separation enforced by `import-linter`.
- **§11.9** — every frontend page calls only HTTP, never the DB.
- **§11.13** — RLS + tenant_id injection makes data-swap trivial (no code change needed).
- **§11.14** — `/ems/optimise` runs in this FastAPI process, NOT in Next.js.
- **§11.15** — `/agents/{persona}/query` endpoint (AI Agents lead fills the body; this lead provides the surface).
- **§11.16** — `/agents/voice/session` endpoint with stub+real branches.
- **§11.17** — OpenAPI spec is the source for SDK generation.
- **§11.18** — `/openapi.json` served (consumed by dev portal Scalar embed).
- **§11.19** — `/ems/forecasts/submit` with auto-flipping status.
- **§11.20** — `/regulatory/documents/.../sign` returns badge with `is_demo_stub=TRUE`.
- **§11.21** — `/market/rdn|vdr|br|dd` endpoints expose single-pane data.
- **§11.22** — `/ems/kpi/portfolio` and `/ems/kpi/daily` expose CO₂ KPI.
- **§11.24** — every endpoint returns well-formed JSON (smoke test gate).
- **§11.25** — response time budgets (read endpoints < 200 ms p95 on synth data).

---

## 8. Pre-flight check (NON-NEGOTIABLE — answer YES before starting)

- [ ] **(a) Goal clear?** "Build all FastAPI endpoints from §4; emit OpenAPI; enforce RLS + import-linter."
- [ ] **(b) Success criteria measurable?** "Every line in §2 is binary checkable."
- [ ] **(c) Tools available?** "FastAPI, Pydantic v2, SQLAlchemy 2.0 async, asyncpg, import-linter, spectral-cli all resolvable in `apps/api/pyproject.toml`."
- [ ] **(d) Plan complete?** "I can produce every endpoint by following Phase A→E mechanically with no architectural decisions left to make."
- [ ] **(e) Upstream green?** "DB phase done (per `BACKEND_DB_INSTRUCTIONS §11`); synth_coverage.md is ✅."

If any NO → STOP. Write `BACKEND_API_CHECKLIST.md` addendum, ping orchestrator.

---

## 9. Branching protocol

| Branch point | Fallback |
|---|---|
| `SET LOCAL` outside transaction fails | Wrap every dependency in `engine.begin()` (already specced); if a specific route needs to run outside a transaction, raise it as an exception — there should be no such route. |
| Pydantic v2 numeric-string serializer is awkward | Use `field_serializer` decorator on the response model fields rather than global encoders. |
| Spectral fails on a rule we can't satisfy (e.g., FastAPI emits something the linter dislikes) | Either fix at the FastAPI level (preferred) or add a targeted `overrides` to `.spectral.yaml` documenting why. **Do not disable global rules.** |
| `import-linter` flags a false positive (e.g., `app.core.public` imported via a re-export) | Add the specific edge to `ignore_imports` in `importlinter.cfg`. Document in a comment. |
| OpenAPI dump is non-deterministic across runs (FastAPI sometimes emits different `$ref` ordering) | Add `sort_keys=True` (already in Step 13) AND post-process the JSON to canonicalise component order. |
| Voice provider `openai-realtime` selected but key missing | Force-downgrade to `stub`, log WARN, continue. Already specced in Step 11. |
| Optimiser non-deterministic (test fails) | Audit every randomness source; the `inputs_hash`-seeded `random.Random` is the only allowed RNG. No `numpy.random` without seeding. |
| RLS test fails because `app.tenant_id` not set (e.g., during health check) | Health check endpoint MUST NOT touch tables with RLS; use `SELECT 1` or `pg_isready`. |
| Caddy `rate_limit` directive errors (plugin not installed) | Document in `difficulties_log.md`; ask DevOps to install `caddy-ratelimit`. Until installed, rely on Cloudflare rate-limit (already in DNS layer per §9). |

Log every branch to `difficulties_log.md`; return to main path as soon as possible.

---

## 10. Done definition

Backend API phase DONE iff:

1. All boxes in §2 checked.
2. CI gates green: `pytest unit`, `pytest integration`, `uv run lint-imports`, `uv run ruff check`, `uv run mypy`, `spectral lint`, `pytest --sdk-examples` (run by SDK lead but depends on this surface).
3. `packages/openapi/openapi.json` committed and up-to-date with implementation.
4. PR opened titled `feat(api): full endpoint coverage + OpenAPI + RLS injection (Phase 4.3 + 4.7)`.
5. Append to `PROGRESS.md`:
   ```
   - YYYY-MM-DD — Phase 4.3 + 4.7 (Backend API lead) DONE. 30+ endpoints; OpenAPI green; import-linter green; RLS verified via API. [one-line gotcha note]
   ```
6. Any branch taken logged in `difficulties_log.md`.

When done, hand off:
- to SDK lead (`SDK_INSTRUCTIONS.md`) — they unblock on OpenAPI spec.
- to AI Agents lead — they unblock on `/agents/{persona}/query` router skeleton.
- to Frontend lead (Phase 4.5+) — full endpoint set unblocks the surfaces.

---

*End of BACKEND_API_INSTRUCTIONS v0.1.*
