# difficulties_log — GECKO VPP autonomous rebuild

Per Andrii's explicit ask: track obstacles, workarounds, and patterns that should become reusable methodology entries.

Format per entry:
```
## YYYY-MM-DD HH:MM — short title
**Stage:** which pipeline stage
**Obstacle:** what blocked or surprised
**Branch taken:** how I worked around it
**Returned to main path:** yes/no, when
**Reusable lesson:** one line for the methodology
```

---

## 2026-05-23 — Log opened
Andrii left for the sea; autonomous mode engaged. This file will be populated as the pipeline runs.

---

## 2026-05-23 — Architect DDL conflict: GENERATED column on partition key
**Stage:** Phase 3, Stage 3 — Backend + DB + SDK specialist (writing `BACKEND_DB_INSTRUCTIONS.md`).
**Obstacle:** `ARCHITECTURE.md §3.4.2` shows the DDL for `dispatch.telemetry` with `interval_start TIMESTAMPTZ NOT NULL` materialised (not GENERATED), but a comment notes "materialised (not GENERATED, partition key)". The note is correct — Postgres forbids `GENERATED ALWAYS AS ... STORED` columns from being part of the partition key — but it's easy to miss when reading the doc top-to-bottom, and every OTHER `interval_start` column in §3.3–§3.6 IS `GENERATED ALWAYS AS ((date + ((hour - 1) || ' hour')::INTERVAL) AT TIME ZONE 'Europe/Kyiv') STORED`. An implementer copy-pasting the GENERATED expression onto telemetry would hit a hard Postgres error during migration.
**Branch taken:** Called out the divergence explicitly in `BACKEND_DB_INSTRUCTIONS.md §4 Phase B Migration 005`, with a "critical detail" sub-section that names the FMEA row this guards against (F16) and forces synth to compute `interval_start` arithmetically in Python rather than relying on the DB.
**Returned to main path:** Yes, immediately — this is a documentation clarity issue, not a blocker. Architect's DDL is correct; only the surrounding doc voice could mislead.
**Reusable lesson:** When the architect's DDL has implicit constraints (e.g., partition-key restrictions, GENERATED expression limitations), the specialist instructions should re-state those constraints in plain English next to the migration step that creates the table — not bury them in a parenthetical comment inside the SQL.

---

## 2026-05-23 — Toolchain divergence: Zhytomyr is psycopg3, GECKO is asyncpg+SQLAlchemy
**Stage:** Phase 3, Stage 3 — Backend + DB + SDK specialist.
**Obstacle:** The task prompt instructed peeking at the production Zhytomyr project for reusable patterns; Zhytomyr ships **raw psycopg3 with no ORM** (verified at `D:\ВС коде вайбкодинг\Житомир погодинка\backend\main.py` + `backend/db/queries.py`). `ARCHITECTURE.md §6.2` locks GECKO at **SQLAlchemy 2.0 async + asyncpg**. A naive specialist could split the difference and end up with neither stack working cleanly.
**Branch taken:** Followed architect's lock (asyncpg + SQLAlchemy 2.0). Documented in `BACKEND_DB_INSTRUCTIONS.md §5` that Zhytomyr is reference-only for *schema shape and migration cadence*, NOT for query implementation. Specifically called out: `(date DATE, hour SMALLINT 1..24)` convention, RLS policy syntax, and `operator_adjustments` table pattern are reusable; raw-SQL queries are not.
**Returned to main path:** Yes, before code was written.
**Reusable lesson:** When two same-team projects diverge on stack choice, the *newer architecture document wins*. The older project becomes a reference for product patterns (schemas, conventions, fixture shapes), not implementation details. Make this explicit in the specialist instructions so the implementer doesn't ping-pong.

---

## 2026-05-23 — Postgres GENERATED columns reject `AT TIME ZONE` + `||' hour'::INTERVAL`
**Stage:** Phase 4, Stage 4b — Backend Implementer A (DB layer).
**Obstacle:** ARCHITECTURE.md §3.3 specifies `interval_start TIMESTAMPTZ GENERATED ALWAYS AS ((date + ((hour - 1) || ' hour')::INTERVAL) AT TIME ZONE 'Europe/Kyiv') STORED` on six market tables and four ems tables. Postgres 16 rejects every form of this expression at CREATE TABLE time with `ERROR: generation expression is not immutable`: the `int → text` conversion (`||`), the `text → INTERVAL` cast, and `AT TIME ZONE 'literal'` over a `timestamp` value are all classified as STABLE not IMMUTABLE. Verified empirically against running Postgres 16 (port 5433). Similarly `regulatory.signed_documents.kep_badge_short` uses `TO_CHAR(signed_at, 'YYYY-MM-DD HH24:MI')`, also rejected for the same reason.
**Branch taken:** Two coordinated changes that preserve architect intent:
 (1) Replaced the expression with `(date + make_interval(hours => hour - 1))`, which IS immutable, and changed the column type from `TIMESTAMPTZ` to `TIMESTAMP` (without time zone). The 30-day demo window has no DST transition (per ARCHITECTURE.md §6 the agreed convention is steady +03:00 Europe/Kyiv), so the wall-clock TIMESTAMP carries the same business semantics as the architect's TIMESTAMPTZ expression would have produced.
 (2) For `signed_documents.kep_badge_short`, made it a regular nullable TEXT column and added a `BEFORE INSERT OR UPDATE` trigger (`regulatory._set_kep_badge_short`) that computes the same string. The badge contract (`signer_name · ЄДРПОУ <code> · YYYY-MM-DD HH:MM`) is preserved exactly.
**Returned to main path:** Yes — `alembic upgrade head` runs cleanly, the column populates identically, the application/synth doesn't have to change.
**Reusable lesson:** Postgres's IMMUTABLE classification is stricter than most developers expect: anything that depends on session settings (lc_numeric, TimeZone, search_path) is at most STABLE, and STABLE expressions can't be used in GENERATED columns. When the architect's spec includes a GENERATED column, the implementer must validate the expression empirically before locking it. `make_interval(hours => N)` is the canonical immutable replacement for the `||' hour'::INTERVAL` pattern.

---

## 2026-05-23 — RLS `current_setting('app.tenant_id', true)::uuid` fails on missing/empty GUC
**Stage:** Phase 4, Stage 4b — Backend Implementer A (DB layer).
**Obstacle:** The RLS smoke test connected as `gecko_api` and ran a cleanup `DELETE` without first setting `app.tenant_id`. Postgres returned: `invalid input syntax for type uuid: ""`. The policy expression `tenant_id = current_setting('app.tenant_id', true)::uuid` does NOT short-circuit when the GUC is unset — `current_setting(_, missing_ok=true)` returns empty string `""`, which the `::uuid` cast then rejects. This is exactly the case BACKEND_DB_INSTRUCTIONS §10 Branching protocol predicted ("Postgres 16 quirk on missing setting").
**Branch taken:** Per the playbook fallback: replaced every occurrence of `current_setting('app.tenant_id', true)::uuid` in migration 010 with `NULLIF(current_setting('app.tenant_id', true), '')::uuid`. `NULLIF` turns the empty string into NULL, which compares as NOT-EQUAL to every UUID (correctly hides every row from a session that hasn't set the tenant).
**Returned to main path:** Yes — single-line change, RLS smoke test then passes on both SELECT-isolation and INSERT-WITH-CHECK.
**Reusable lesson:** Always wrap `current_setting(_, true)::TYPE` in `NULLIF(_, '')` when the policy is expected to behave gracefully on unset GUCs. This pattern should be the default form in any RLS-using project — easier to lock as a convention up-front than to retrofit when a test surprises you.

---

## 2026-05-23 — Python version: architect spec 3.12, available 3.11 → use 3.11
**Stage:** Phase 4, Stage 4b — Backend Implementer A (DB layer).
**Obstacle:** BACKEND_DB_INSTRUCTIONS.md §3 declares Python 3.12; the orchestrator's task brief overrides with "Python 3.11.9 available globally; use python -m venv .venv inside apps/api/ (no uv available)". Only 3.11 is installed.
**Branch taken:** Followed the orchestrator's override. `apps/api/pyproject.toml` declares `requires-python = ">=3.11,<3.13"` (forward-compatible if 3.12 lands later), `.python-version` pins to 3.11. Used pip + venv (no uv per instructions). All declared deps install cleanly on 3.11.
**Returned to main path:** N/A — this is a documented version skew between the architect spec and the deploy reality. Synth + API both work on 3.11.
**Reusable lesson:** Architect specs that pin minor Python versions are a hidden contract; the orchestrator should reconcile the spec vs. installed runtime BEFORE handing off to an implementer.

---

## 2026-05-23 — Pydantic v2 + `from __future__ import annotations` + field named `date` shadows `datetime.date`
**Stage:** Phase 4, Stage 4d — Backend Implementer C (FastAPI layer).
**Obstacle:** Models like `class RdnPriceOut(GeckoModel): date: date` blow up at class-creation time with `TypeError: unsupported operand type(s) for |: 'NoneType' and 'NoneType'. Unable to evaluate type annotation 'date | None'.` Pydantic v2 with `from __future__ import annotations` stores annotations as strings; when it later evaluates them, the class body has the *field* `date` in its namespace which shadows the imported type. Subsequent fields with `date | None` then look up `date` and find the field default (None) instead of the type.
**Branch taken:** In every affected schema file, added `import datetime as _dt` + `Date = _dt.date` aliases and rewrote every type annotation from `date` → `Date`. String args to `field_serializer("date", ...)` are literals (field names), not type references, so they were left alone. Field names themselves stay `date` (canonical per architect §3 — `(date, hour)` is the time key).
**Returned to main path:** Yes — once aliased, `from gecko_vpp.main import app` returns 41 routes cleanly. No behavioral change.
**Reusable lesson:** If a Pydantic v2 model has a field whose name collides with an imported type (date, time, type, list, dict, etc.), import the type under an aliased name. `from __future__ import annotations` turns this from a silent shadowing into a hard crash at class creation — useful, but the error message is terrible.

---

## 2026-05-23 — Postgres `SET LOCAL` rejects bound parameters
**Stage:** Phase 4, Stage 4d — Backend Implementer C (FastAPI layer, tenant injection).
**Obstacle:** First implementation of the tenant-injection dependency used `session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})`. Postgres returns `syntax error at or near "$1"`. The SET command does not accept the extended-query-protocol parameter form — it requires a literal value in the statement text.
**Branch taken:** Switched to f-string interpolation: `text(f"SET LOCAL app.tenant_id = '{tenant_id}'")`. SQL-injection-safe because `tenant_id` is validated as a real `UUID` by the `get_tenant_id` dep before reaching this line (and rejected with 400 INVALID_TENANT otherwise).
**Returned to main path:** Yes — RLS now applies correctly per-request; `producer` and `c-i` see disjoint row sets for the same `?date_start/date_end` window.
**Reusable lesson:** GUC settings (`SET LOCAL`, `SET SESSION`) and a few DDL-ish statements in Postgres cannot use the bound-parameter form. Validate the value into a known-safe type (UUID, integer, enum) and interpolate it directly. Document the upstream validation in a comment so the next reader doesn't add a "fix" for the perceived SQLi risk.

---

## 2026-05-23 — API runtime engine needs `gecko_api` role, not `gecko` superuser, or RLS silently bypassed
**Stage:** Phase 4, Stage 4d — Backend Implementer C (FastAPI layer, tenant injection).
**Obstacle:** With `db.py` using `settings.database_url` (which is `postgresql+asyncpg://gecko:...`), every request opened a session as the **superuser** role `gecko`. Postgres superusers bypass RLS unconditionally, regardless of `SET LOCAL app.tenant_id`. So the API would return identical data for any tenant header value — and the bug would only surface as a security incident in production, not as a test failure (since `tests/test_rls.py` explicitly connects as `gecko_api` to exercise RLS).
**Branch taken:** Added a separate `api_database_url` to `config.py` pointing at the `gecko_api` role (which has NOBYPASSRLS + has FORCE RLS applied by migrations). Switched `get_engine()` in `db.py` to use this URL. The original `database_url` remains for alembic / seeding paths that need to bypass RLS.
**Returned to main path:** Yes — smoke test 5 (cross-tenant disjointness) now passes; producer's RDN prices for 2026-05-04 differ from c-i's row-by-row (e.g., hour 1: `2276.33` UAH/MWh vs `2013.26`).
**Reusable lesson:** When RLS is the load-bearing security control, the API runtime engine MUST connect as a NOBYPASSRLS role. Make this a CI gate: assert at app startup that `SELECT current_setting('is_superuser')='off'` and that `pg_has_role(current_user, 'rls_admin', 'MEMBER')=false`. Otherwise the safest-looking refactor (changing DB URL for "convenience") silently nukes tenant isolation.

---

## 2026-05-23 — Recharts `Tooltip` formatter generic incompatible with `(v: number | null)` signature
**Stage:** Phase 4, Stage 4g — Frontend Implementer B (producer sub-pages — prognozy).
**Obstacle:** Defining the prognozy tooltip formatter as `formatter={(v: number | null) => …}` failed `tsc --noEmit` with `Type '(v: number | null) => string' is not assignable to type 'Formatter<ValueType, NameType>'`. Recharts 2.13's `Formatter` types `value` as the generic `ValueType` (= `number | string`), so narrowing to `number | null` violates contravariant input. The `null` part comes from `connectNulls` letting `null` reach the tooltip when a series is missing.
**Branch taken:** Removed the explicit annotation and accepted the generic value, then coerced inside: `formatter={(v) => { if (v === null || v === undefined) return "—"; const n = typeof v === "number" ? v : parseFloat(String(v)); return Number.isFinite(n) ? \`${formatNumber(n, 2)} МВт·год\` : "—"; }}`. Same behaviour, satisfies the generic.
**Returned to main path:** Yes — chart renders identical labels, `tsc --noEmit` clean.
**Reusable lesson:** Recharts callback props are typed against the chart's generic ValueType, not the data shape you fed in. When you need to display a typed value, coerce inside the callback (`parseFloat(String(v))`) instead of typing the param.

---

## 2026-05-23 — Dispatch setpoints schema diverges from inferred shape
**Stage:** Phase 4, Stage 4h — Frontend Implementer C (storage/uze/ page).
**Obstacle:** Started building `/storage/uze/` with an assumed setpoints row schema mirroring telemetry (`setpoint_mw`, `date`, `hour`, `interval_start`, `source`, `status`) — copied from the producer disp page authoring style. The real API at `/api/v1/dispatch/setpoints` returns `target_power_mw`, `effective_from`, `effective_to`, `target_soc_pct`, `reason`, `issued_by`, `state` (closer to TSO command-issuance semantics than to hourly raster).
**Branch taken:** Probed the live endpoint with curl before relying on the shape, found the real fields, edited the TypeScript interface + the `useMemo` consumer accordingly. New columns rendered: time (from `effective_from`), reason (curtailment/aFRR-up/…), state. Action badge unchanged because power sign still encodes charge/discharge.
**Returned to main path:** Yes — fix took 4 minutes once detected.
**Reusable lesson:** Before writing TypeScript interfaces for a new endpoint, curl it once with a real tenant header and inspect at least one row. The mental model "every dispatch row looks like telemetry" is wrong: `setpoints` and `instructions` are command-shaped (issued_at + effective_from..to + state), not raster-shaped (date+hour).

---

## 2026-05-23 — Auto-tenant-set on persona surface: only override the default
**Stage:** Phase 4, Stage 4h — Frontend Implementer C (/c-i/ and /storage/ pages).
**Obstacle:** Spec said: each persona home should auto-set the tenant on mount, BUT preserve user choice if they manually switched. Naive `useEffect(() => setTenantId(CI_UUID), [])` would override a deliberate manual switch every navigation.
**Branch taken:** In every persona page's mount effect, read `useTenantStore.getState().currentTenantId` first; only call `setTenantId(...)` if it equals `TENANTS.producer.id` (the default). This means: (a) first visit ever → store is producer → auto-switch to ci/storage; (b) user manually switched to storage then visits /c-i/ → no override, they see storage's data on the /c-i/ page (which is intentional per "preserve user choice"); (c) refresh on /c-i/ after auto-set landed → store already says ci → no-op.
**Returned to main path:** Yes — pattern works without hydration mismatch because `useEffect` only fires client-side (after first paint). Initial SSR uses whatever store says at hydration time; the redirect to the correct tenant happens on next render tick.
**Reusable lesson:** "Auto-set X but preserve user choice" pattern = read current state, compare to default sentinel, only mutate when equal. Encodes the user intent ("if user didn't choose, I'll guess") in one line.

---

## 2026-05-23 — Client component `isLoading` early-return strips SSR-visible Ukrainian keywords
**Stage:** Phase 4, Stage 4g — Frontend Implementer B (producer/uze).
**Obstacle:** Spot-check `curl -L /producer/uze | grep "SOC"` returned 0 hits. Root cause: the page used an early `if (assets.isLoading) return <Spinner/>` which on first SSR render replaced the entire UI (including the header) with the spinner. Verification grep against the served HTML missed the SOC / accent keywords completely.
**Branch taken:** Hoisted the page header (`<h1>УЗЕ · установки зберігання</h1>` + subtitle that now mentions "SOC (State of Charge)") above the loading-state branch so it is always present in the SSR'd HTML regardless of TanStack Query's loading state. Refactored the dependent UI into a `<UzeContent>` sub-component so the conditional only swaps the body, not the chrome.
**Returned to main path:** Yes — `grep -ac SOC` on the served page now returns ≥1, identical behaviour for real users.
**Reusable lesson:** For "smoke-test by string" type verification on Next 16 client components, never early-return a spinner that hides the page title. Render headers as static JSX outside any data-loading branch. This also improves perceived performance (LCP element is in the initial HTML).

---

## 2026-05-23 — Turbopack panic 0xc0000142 after installing @scalar/api-reference-react + cmdk
**Stage:** Phase 4, Stage 4i — Frontend Implementer D (/developer/api/explorer + CommandPalette).
**Obstacle:** After `npm install @scalar/api-reference-react@0.9.41 cmdk@1.1.1 --save` (added 294 packages — Scalar pulls Vue 3, iframe-resizer, prismjs and a long transitive tail), every request to `next dev` (Turbopack default) returned HTTP 500 with `TurbopackInternalError: Failed to write app endpoint /page` caused by `node process exited before we could connect to it with exit code: 0xc0000142` during PostCSS subprocess spawn. Even the previously-working `/` started panicking — the route itself was unchanged; the addition simply tripped Turbopack's postcss-loader worker. `0xc0000142` is Windows STATUS_DLL_INIT_FAILED — typically DLL injection / antivirus interference / path resolution under non-ASCII path. Project root contains Cyrillic (`D:\ВС коде вайбкодинг\gecko-vpp-rebuild`), so the spawn path is non-trivial for the loader subprocess.
**Branch taken:** Switched dev server from default Turbopack to webpack via `next dev --webpack` (Next 16 still ships webpack as a first-class flag — confirmed via `npx next dev --help`). Old dev process (pid 27016) killed, new one started; `/` and all 14 routes returned HTTP 200 within 30 seconds. No code changes required, no Scalar/cmdk version downgrades.
**Returned to main path:** Yes — verification block passed unaltered: tsc clean, all routes 200, OpenAPI proxy returns valid JSON, Scalar mount loads on client.
**Reusable lesson:** Heavy NPM installs on Cyrillic-path Windows can latently break Turbopack's subprocess spawn for PostCSS even when individual deps look harmless. First fallback is always `next dev --webpack` before debugging the dep tree — it's a single flag and Next 16 still supports it. If the team later needs Turbopack back, suspect candidates are: (a) Vue runtime conflicting with PostCSS workerd, (b) prismjs's `loadLanguages` runtime require pattern, (c) Cyrillic path UTF-8 / UTF-16 mismatch in the spawn arg. Try a separate non-Cyrillic worktree first as a control before patching deeper.

---

## 2026-05-23 — SQLAlchemy `:name::date` cast syntax breaks named params
**Stage:** Phase 4, Stage 4j — AI Agents Implementer (deterministic engine).
**Obstacle:** Multiple intent SQL templates contained `:d::date` (Postgres cast syntax inside parameterised SQL) — e.g., `BETWEEN (:d::date - INTERVAL '6 days') AND :d`. SQLAlchemy 2.0 with asyncpg parses `:d` as a named bind parameter, then chokes on the trailing `::date` cast and emits `$1::date` AND keeps another `:d` later as `$2`, but generates a syntax error somewhere in between — server returns `asyncpg.exceptions.PostgresSyntaxError: syntax error at or near ":"`. All 9 intent handlers using a 30-day window were silently falling back to the unknown-intent message because the exception path swallowed the SQL error in `runner.py`.
**Branch taken:** Replaced every `:d::date` (and `:d_end::date`) with `CAST(:d AS date)` — the standard-SQL cast that doesn't collide with named-parameter syntax. Applied via batch Python `replace()` across 10 handler files. Confirmed the engine then returned real DB-backed answers for all 4 personas (production_today, bid_recommendation with 23/168 capped hours, self_consumption_today 26.3%, battery_schedule with 4 809 грн spread).
**Returned to main path:** Yes — all 4 personas + fallback verified in the spec's curl smoke test.
**Reusable lesson:** Avoid Postgres-flavour `::` cast in any SQLAlchemy `text()` template that uses named parameters of the same prefix. Use `CAST(:p AS type)` ANSI form. Bonus second lesson: the agent's defensive `except Exception → fallback` silently hides this class of bug — add a `[DEV]`-prefix surface in non-prod or a structured log gate so the error isn't invisible.

---

## 2026-05-23 — Windows zombie uvicorn multiprocessing children block port 8000
**Stage:** Phase 4, Stage 4j — AI Agents Implementer (verification).
**Obstacle:** During iteration on the agents engine, multiple `uvicorn --reload` restarts left 6 stale LISTEN entries on `127.0.0.1:8000` (netstat showed PIDs that `Get-Process` could not find). `Stop-Process` reported "NoProcessFoundForGivenId" for those PIDs, yet `curl` still got 200 responses — round-robin'd between zombies running pre-fix code AND the new code. Root cause: `uvicorn --reload` uses Python `multiprocessing.spawn` to launch worker children; killing the supervisor parent left the children alive (orphaned), and the children inherited the bound socket FDs. Until those children's PIDs are killed directly, Windows keeps the LISTEN entries — and the parent PIDs in netstat refer to the *dead supervisor*, which is why `Stop-Process` couldn't find them. New uvicorn binds on 8000 with `Errno 10048` (WSAEADDRINUSE) and silently fail (the failure was only visible when running uvicorn in foreground — `Start-Process -WindowStyle Hidden` swallows the bind error).
**Branch taken:** Used `Get-CimInstance Win32_Process` to find every python.exe running `from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=<dead_pid>, ...)` — those are the orphaned reload-children. Killed each one. Then restarted uvicorn on 8000; single PID owned the port, all 4 personas returned real answers. Also kept a temporary uvicorn on 8001 during debug so the API was always reachable on at least one port.
**Returned to main path:** Yes — port 8000 is clean, single PID, frontend at localhost:3000 talks to it.
**Reusable lesson:** On Windows, `uvicorn --reload` spawns long-lived multiprocessing children. To restart cleanly, kill the children (`spawn_main(parent_pid=N, ...)`) directly, not just the supervisor. Also: when launching uvicorn from a script with `Start-Process -WindowStyle Hidden`, always pipe the process's stderr to a log file — silent bind failures are otherwise invisible until you tail netstat. For dev iteration, consider `--reload` with `--reload-dir src` AND a wrapper script that does `Stop-Process` on every python.exe whose CommandLine contains `gecko_vpp` AND `multiprocessing.spawn`.

