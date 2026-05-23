# SECURITY_INSTRUCTIONS — GECKO VPP v2

**Owner:** Security lead (Operations Specialist Lead bundle).
**Authoritative source:** `ARCHITECTURE.md` §9 (Security model), §3.9 (RLS policies), §3.10 (Grants and roles), §11 FMEA rows F06, F13, F14, F18.
**Brief reference:** `PRODUCT_BRIEF.md` §11.13 (sub-1 hour data swap), §13 risk row "tenant data isolation in the demo is a security fiction".
**Status:** v0.1 — 2026-05-23. Frozen for Phase 4 execution.

---

## 0. Goal

Establish a credible security posture for a mock-tenant demo. Two non-negotiables:

1. **Real tenant isolation in Postgres** — even though authentication is mock (knowledge of one of three UUIDs), the database must physically refuse to return tenant B's rows when `app.tenant_id` is set to tenant A. This is enforced by Row-Level Security (RLS) on `gecko_api NOBYPASSRLS`. The "sub-1 hour data swap" acceptance criterion (PRODUCT_BRIEF §11.13) cashes only if RLS is real.
2. **No XSS or SQL-injection surface** exposed by the public dev portal. The portal exposes OpenAPI schema for read; mutation endpoints are not exploitable without one of three demo tenant UUIDs (stable, not advertised).

Everything else (rate limit, HSTS, CORS, gitleaks) is supporting infrastructure. The two above must hold.

---

## 1. Success criteria (verifiable)

| # | Criterion | How to verify |
|---|---|---|
| S1 | RLS cross-tenant test passes: two psycopg connections with different `app.tenant_id` see disjoint row sets on every domain table | `pytest apps/api/tests/integration/test_rls_isolation.py -v` |
| S2 | `gecko_api` role has `NOBYPASSRLS` after migrations applied | `psql -c "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname='gecko_api'"` → `f` |
| S3 | All SQL goes through asyncpg `$1`/`$2` parameter placeholders; no f-string SQL anywhere | `ruff check --select=S608 apps/api/` returns clean |
| S4 | CORS allow-list locked to `https://gecko.radai-1984.dev` + `http://localhost:3000` + `http://localhost:3001`; no wildcard | `curl -i -H "Origin: https://evil.example" https://api.gecko.radai-1984.dev/api/v1/assets` returns no `Access-Control-Allow-Origin` header |
| S5 | gitleaks scan clean against the entire repo on every CI run | `gitleaks detect --source . --no-banner` exit 0 |
| S6 | `<KEPSignBadge>` always renders the DEMO watermark; component throws if `demo={true}` prop is omitted | Playwright smoke test `kep-watermark-required.spec.ts` |
| S7 | Caddy rate-limit of 100 req/min/IP enforced on `/api/*` | `for i in $(seq 1 120); do curl -o /dev/null -s -w "%{http_code}\n" https://api.gecko.radai-1984.dev/healthz; done | sort | uniq -c` shows 429s after 100 |
| S8 | Dev portal at `/developer/api/explorer` exposes OpenAPI but no working tenant token is shipped client-side | View page source; no `X-Tenant-Id` value rendered |
| S9 | HSTS header present on every prod response | `curl -I https://gecko.radai-1984.dev/ | grep -i strict-transport-security` |
| S10 | No `dangerouslySetInnerHTML` outside the audited Scalar wrapper | ESLint rule `react/no-danger` set to `error` with single override in `components/dev/OpenAPIExplorer.tsx` |

All ten green → done.

---

## 2. Tools (locked)

| Tool | Purpose | Where it runs |
|---|---|---|
| `gitleaks` | Secret-scanning | Pre-commit hook + CI job `lint.secrets` |
| `ruff` (`S` ruleset) | Detects f-string SQL anti-pattern + bandit-equivalent checks | CI job `lint.python` |
| `bandit` | Python security linter (supplementary to ruff `S`) | CI job `lint.python`, advisory |
| `pytest` + `pytest-asyncio` + `testcontainers` | RLS integration tests | CI job `test.integration` |
| `eslint-plugin-react` (`no-danger` = error) | XSS prevention at component level | CI job `lint.frontend` |
| Caddy native `rate_limit` directive | Per-IP rate-limit on `/api/*` | Hetzner host |
| `psql` | Manual RLS audit | Hetzner VPS during deploy verification |

No paid third-party security tooling. No Snyk, no Sonar — gitleaks + ruff + bandit + the RLS pytest is sufficient for a demo.

---

## 3. Architecture details (cross-referenced to ARCHITECTURE.md)

### 3.1 Mock authentication

Per ARCHITECTURE.md §9.1:

- The only "credential" is knowledge of one of the three demo tenant UUIDs (seeded in migration `002_core_tables.py`, listed in `docs/demo-tenants.md`). Codes: `producer-1`, `ci-1`, `storage-1`.
- Next.js layer stores `gecko_tenant_id` cookie: **HttpOnly, Secure, SameSite=Lax, Path=/**. Set on `/api/v1/auth/switch-tenant` Next.js route handler response.
- Next.js route handlers (`apps/web/app/api/[...path]/route.ts`) read the cookie and forward as `X-Tenant-Id` header to FastAPI. Browser **never sees** the FastAPI endpoint directly — same-origin via Next.js avoids preflight CORS and avoids exposing the header mechanism client-side.
- No password, no OAuth, no JWT. PRODUCT_BRIEF §12 explicitly out-of-scopes real auth.

### 3.2 Per-request tenant injection in FastAPI

`apps/api/app/db.py` defines the dependency every router uses (ARCHITECTURE.md §9.2 + §6 implication):

```python
from fastapi import Depends, Header, HTTPException
import asyncpg
from uuid import UUID

async def get_db_conn(
    x_tenant_id: str = Header(...),
    x_admin: str | None = Header(default=None),
) -> asyncpg.Connection:
    try:
        tenant_uuid = UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(400, "Invalid X-Tenant-Id")
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "SET LOCAL app.tenant_id = $1",
                str(tenant_uuid),
            )
            if x_admin == "true":
                await conn.execute("SET LOCAL app.is_admin = 'true'")
            yield conn
```

**Critical:** `SET LOCAL` is transaction-scoped. The connection returns to the pool with no residual state. **Do not use plain `SET`** — that leaks tenant context across requests and is the single most likely way to leak data.

### 3.3 RLS policy posture

Per ARCHITECTURE.md §3.9:

- Every domain table has RLS enabled in migration `009_rls_policies.py`.
- Standard policy:
  ```sql
  CREATE POLICY tenant_isolation_select ON <table> FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
  CREATE POLICY tenant_isolation_modify ON <table> FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
  ```
- Cross-tenant table `regulatory.regulator_events` uses separate policies:
  - `regevent_read_all` — `USING (TRUE)` for SELECT
  - `regevent_write_admin` — requires `app.is_admin='true'` for ALL
- Admin bypass for `/api/v1/admin/*` endpoints: separate policy `tenant_isolation_admin_bypass` activated only when `app.is_admin='true'` is set. The `@cross_tenant` Python decorator (see §6.5 of architecture) sets that flag and writes `audit.events` with `event_type='admin.cross_tenant_read'`.

### 3.4 Role posture (ARCHITECTURE.md §3.10)

```sql
CREATE ROLE gecko_api LOGIN PASSWORD '<env>';
CREATE ROLE gecko_migrate LOGIN PASSWORD '<env>' BYPASSRLS;
CREATE ROLE gecko_readonly LOGIN PASSWORD '<env>';
ALTER ROLE gecko_api NOBYPASSRLS;
```

- `gecko_api` — what the FastAPI process connects as. **MUST** have `NOBYPASSRLS`. If a coder forgets `WHERE tenant_id = ...` in a query, the DB returns 0 rows, not a leak.
- `gecko_migrate` — used only by `alembic upgrade head`. Has BYPASSRLS so schema migrations can run. **Never used by FastAPI runtime.**
- `gecko_readonly` — reserved, not used in v2 demo. Will be used if/when "read-only customer key" SDK auth ships.

### 3.5 Three demo tenant UUIDs

Seeded in migration `002_core_tables.py`, fixed forever (referenced in tests, in `docs/demo-tenants.md`, in the synth generator):

```
producer-1 → 00000000-0000-4000-8000-000000000001
ci-1       → 00000000-0000-4000-8000-000000000002
storage-1  → 00000000-0000-4000-8000-000000000003
```

These are well-known but not advertised on the dev portal. To switch tenants in the browser, a user must already know a UUID or use the topbar `<TenantSwitcher>` (which reads them from `/api/v1/auth/list-tenants`, a non-secret endpoint that returns the three).

### 3.6 CORS posture (ARCHITECTURE.md §9.6)

CORS set at **two layers** for defence in depth:

1. **Caddy** (`infra/caddy/gecko-api.caddy`) — adds headers at edge.
2. **FastAPI** (`apps/api/app/main.py`) — `CORSMiddleware` with explicit allow-list. Picks up the same value from `settings.cors_origins` (env var, comma-separated).

```python
# apps/api/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gecko.radai-1984.dev",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=False,  # no cookies cross-origin; Next.js proxy handles auth
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Tenant-Id", "X-Admin"],
    max_age=3600,
)
```

**Rule:** never set `allow_origins=["*"]`. CI grep for `allow_origins=["*"]` blocks merge.

### 3.7 Caddy snippet (ARCHITECTURE.md §9.4)

`infra/caddy/gecko-api.caddy`:

```caddy
api.gecko.radai-1984.dev {
    encode gzip zstd

    rate_limit {
        zone gecko_api {
            key {remote_host}
            events 100
            window 1m
        }
    }

    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    header {
        # HSTS — 6 months, includes subdomains
        Strict-Transport-Security "max-age=15768000; includeSubDomains"
        # CORS — restricts who can call from a browser (FastAPI also enforces)
        Access-Control-Allow-Origin "https://gecko.radai-1984.dev"
        Access-Control-Allow-Headers "Content-Type, X-Tenant-Id, X-Admin"
        Access-Control-Allow-Methods "GET, POST, PATCH, DELETE, OPTIONS"
        Access-Control-Max-Age "3600"
        # Hardening
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        # Prevent caching of authenticated responses
        Cache-Control "no-store" {
            path /api/v1/agents/*
            path /api/v1/auth/*
        }
    }

    log {
        format json
        output file /var/log/caddy/gecko-api.log
    }
}
```

**Note** the Caddy `rate_limit` directive requires the `caddy-ratelimit` plugin built into the binary. The existing Caddy on `178.105.209.14` already serves zhytomyr / n8n / ses — DevOps must confirm rate-limit plugin is built in (`caddy list-modules | grep ratelimit`). If not present → swap to `mholt/caddy-ratelimit` build or implement at FastAPI layer with `slowapi`. See DEVOPS_INSTRUCTIONS §5.

### 3.8 Secret handling (ARCHITECTURE.md §9.7, §13.5)

- `.env.example` lives in repo. Real `.env` lives at `/opt/gecko-vpp/.env` on Hetzner, mode `0640`, owner `root:gecko`.
- Cloudflare token at `~/.cloudflare/api-token` — **NOT** in this repo. Referenced via the user's existing memory (`reference_cloudflare_api_token.md`); DevOps scripts read from filesystem.
- OPENAI_API_KEY — present in `.env.example` as empty value. Only filled if `VOICE_PROVIDER=openai-realtime` is set. Default deploy is `VOICE_PROVIDER=stub` — no key needed.
- Postgres passwords generated at deploy time on the VPS with `openssl rand -base64 24`. Never typed, never copy-pasted into chat.
- `gitleaks` runs as a pre-commit hook (config in `.gitleaks.toml` at repo root) and as a CI job. Both block on detection.

`.gitleaks.toml`:

```toml
[allowlist]
# .env.example values are placeholder/safe; never block on them
paths = [
    '''.env.example''',
    '''README.md''',
]

[[rules]]
id = "openai-key"
description = "OpenAI API key"
regex = '''sk-[A-Za-z0-9]{32,}'''

[[rules]]
id = "cf-token"
description = "Cloudflare API token"
regex = '''[A-Za-z0-9_-]{40,}\.eyJ[A-Za-z0-9._-]+'''  # heuristic; tweak as needed

[[rules]]
id = "private-key"
description = "Private key block"
regex = '''-----BEGIN ((RSA|EC|OPENSSH|PGP) )?PRIVATE KEY-----'''
```

### 3.9 SQL injection (ARCHITECTURE.md §9.8)

Mandatory pattern — repository layer uses asyncpg positional params only:

```python
# apps/api/app/market/repositories/rdn.py
async def list_rdn(conn, date_from, date_to):
    return await conn.fetch(
        "SELECT * FROM market.rdn_prices "
        "WHERE date BETWEEN $1 AND $2 ORDER BY date, hour",
        date_from, date_to,
    )
```

**Forbidden patterns** (CI `ruff check --select=S608`):

```python
# NEVER
await conn.fetch(f"SELECT * FROM market.rdn_prices WHERE date = '{date}'")
await conn.fetch("SELECT * FROM " + table_name)
await conn.fetch("SELECT * FROM market.rdn_prices WHERE date = " + str(date))
```

If a table name truly needs to be dynamic (the optimiser does this for one query), it must be looked up in a hardcoded allow-list:

```python
ALLOWED_TABLES = {"rdn_prices", "vdr_trades", "br_settlements"}
if table not in ALLOWED_TABLES:
    raise ValueError("table not allowed")
sql = f"SELECT * FROM market.{table}"  # safe: table in allow-list
```

### 3.10 XSS posture (ARCHITECTURE.md §9.9)

- React auto-escapes by default — sufficient for all rendered DB strings.
- ESLint rule `react/no-danger` set to `error` repo-wide.
- Single allowed override: `apps/web/components/dev/OpenAPIExplorer.tsx` (Scalar wrapper) — Scalar escapes internally. Override marked with `// eslint-disable-next-line react/no-danger -- audited 2026-05-23, Scalar v1.x escapes input`.
- No untrusted markdown rendering anywhere. Agent responses are plain text + structured evidence chips — no inline HTML.

### 3.11 No file uploads (ARCHITECTURE.md §9.10)

Per ARCHITECTURE.md §9.10 — `<input type="file" disabled>` everywhere. Eliminates one whole risk class (file-upload-as-execution, path-traversal, MIME confusion).

---

## 4. Threat model (lightweight, 6 rows)

| # | Threat | Mitigation | Verification |
|---|---|---|---|
| T1 | Cross-tenant data leak via missing `WHERE tenant_id` | RLS on every domain table + `gecko_api NOBYPASSRLS` (ARCHITECTURE.md §3.9, §3.10). If app forgets the filter, DB returns 0 rows, not a leak. | `test_rls_isolation.py` runs in CI; FMEA F06 covers RLS-missing-on-new-table |
| T2 | SQL injection via user input in agent query, dates, IDs | All SQL parameterised through asyncpg `$1`/`$2` (ARCHITECTURE.md §9.8). Ruff `S608` blocks f-string SQL in CI. | `ruff check --select=S608` clean; manual review of `apps/api/app/agents/intents/*.py` |
| T3 | XSS via dashboard rendering DB content (asset names, agent text) | React auto-escape; ESLint `react/no-danger=error`; no untrusted HTML rendered (ARCHITECTURE.md §9.9). | `pnpm lint` clean; Playwright smoke renders Ukrainian asset names with `<script>` payload seeded by RLS test and asserts no eval |
| T4 | КЕП-stub badge mistaken for real signature | DEMO watermark **required** prop on `<KEPSignBadge>`; component throws if missing. Disclaimer popover on hover. `/about/credentials` lists every stub. (ARCHITECTURE.md FMEA F13) | Playwright smoke `kep-watermark-required.spec.ts` asserts DEMO text on every badge |
| T5 | Dev portal probed for exploitable mutation endpoint | Rate-limit 100r/m at Caddy; FastAPI checks RLS on every write; UUIDs not advertised. Public read of OpenAPI schema only; no working mutation token issued. | Manual: curl with bogus `X-Tenant-Id` returns 400; curl without header returns 400; curl 200 times within minute returns 429 from request ~101 |
| T6 | Secret committed to public GitHub repo | gitleaks pre-commit hook + CI job (ARCHITECTURE.md FMEA F18). `.env` in `.gitignore`. `.env.example` is the only env-shaped file allowed. | `gitleaks detect --source .` runs in CI; merge blocked on hit. Rotate procedure documented in §6 below. |
| T7 | Cloudflare strips `X-Tenant-Id` header in transit (FMEA F14) | Cloudflare Transform Rule explicitly preserves `X-Tenant-Id`. Smoke test from CI runner curls `https://api.gecko.radai-1984.dev/api/v1/auth/me` with `X-Tenant-Id` header and asserts FastAPI sees the value (logged in `request_id` envelope). | DevOps adds the Transform Rule; Security verifies via curl + Caddy logs. |
| T8 | RLS bypass via Postgres function ownership | All functions created by `gecko_migrate` are explicit `SECURITY INVOKER` (default); never `SECURITY DEFINER` on tables under RLS. CI grep blocks `SECURITY DEFINER` in `apps/api/alembic/versions/*.py`. | `grep -r SECURITY DEFINER apps/api/alembic/` returns empty |

---

## 5. Pre-flight + Branching protocol

### 5.1 Pre-flight (the user's 4 questions)

Before starting any security work, the agent must answer in writing in the PR description or commit body:

1. **What does success look like?** — All 10 success criteria in §1 above are green. RLS test passes; gitleaks clean; KEP watermark required; rate-limit enforced; HSTS present. Failure = any of 10 red.

2. **What inputs do I have?** — `ARCHITECTURE.md` §9, §3.9, §3.10, §11; `PRODUCT_BRIEF.md` §11.13, §13; `infra/caddy/gecko-api.caddy` snippet (already drafted in architecture); existing memory `reference_cloudflare_api_token.md` for CF token path; existing Caddy host config at `/etc/caddy/Caddyfile` on Hetzner (read-only — DO NOT touch existing vhosts for n8n/vodokanal/zhytomyr).

3. **What is the smallest, safest first move?** — Write the RLS isolation pytest (`apps/api/tests/integration/test_rls_isolation.py`) against the testcontainers Postgres **before** writing any RLS policy. Confirm it fails on a fresh schema without policies. THEN apply migration `009_rls_policies.py` and confirm the same test passes. This is the security regression net for everyone downstream.

4. **What could go wrong, and what's my rollback?** — RLS misconfigured can mean either (a) tenant A sees tenant B (catastrophic — caught by `test_rls_isolation.py`) or (b) tenant A sees nothing because policy is too strict (annoying — caught by smoke tests). Rollback = `alembic downgrade -1` to drop the RLS migration; FastAPI then runs without RLS but **still filters by tenant in WHERE clauses** at repository layer (defence in depth). Postgres dump taken before every policy migration: `pg_dump -Fc gecko > /opt/gecko-vpp/backup/$(date +%Y%m%d-%H%M).pgdump`.

### 5.2 Branching protocol

- Branch name: `security/<task>` — e.g. `security/rls-policies`, `security/gitleaks-config`, `security/caddy-snippet`.
- One branch per logical unit. Don't pile gitleaks + RLS + CORS into one branch.
- Commit messages follow the user's global git rules (`fix(security):`, `feat(security):`, etc.) and end with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- Branch must not be merged to main until all relevant CI gates listed in §1 pass.
- The Security lead writes the final RLS audit report as part of `audit/RLS_AUDIT.md` (one-page check off of every table → policy applied → test row).

---

## 6. Operations runbook

### 6.1 If a secret is committed accidentally

1. **Do not push** if not yet pushed. `git reset --soft HEAD~1`, remove secret from staging, recommit.
2. If already pushed:
   - **Rotate the secret first** (CF token, OPENAI key, DB password — whatever leaked).
   - Then `git filter-repo --invert-paths --path <file>` and `git push --force` — only with explicit user override per the user's global rules.
   - File an entry in `difficulties_log.md`.
   - Update `.gitleaks.toml` rule if the leak slipped past existing rules.

### 6.2 If the RLS test starts failing on main

1. **Block deploy immediately** — this is a Sev-1 for the demo.
2. Find the offending migration (`alembic history`).
3. Revert via `alembic downgrade <prev>`.
4. Write the missing `ENABLE ROW LEVEL SECURITY` and policy in a new migration.
5. Re-run the test; confirm green; redeploy.

### 6.3 If a new table is added without RLS

This is **FMEA F06**. The test `test_rls_no_orphan_tables.py` should iterate `information_schema.tables` for our schemas and assert `pg_class.relrowsecurity = TRUE` for every table. Add this iteration test in Phase 4.13 (Security audit phase). If a future PR adds a new table without RLS, this test fails before merge.

```python
# apps/api/tests/integration/test_rls_no_orphan_tables.py
async def test_every_domain_table_has_rls(pg_conn):
    rows = await pg_conn.fetch("""
        SELECT n.nspname, c.relname, c.relrowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('core','market','dispatch','ems','regulatory','agents','audit')
          AND c.relkind = 'r'
    """)
    no_rls = [(r["nspname"], r["relname"]) for r in rows if not r["relrowsecurity"]]
    assert no_rls == [], f"Tables missing RLS: {no_rls}"
```

### 6.4 If Cloudflare strips `X-Tenant-Id` (FMEA F14)

1. CI smoke step issues `curl -H "X-Tenant-Id: 00000000-0000-4000-8000-000000000001" https://api.gecko.radai-1984.dev/api/v1/auth/me`; FastAPI logs the value seen. If CF strips it, FastAPI returns 400.
2. Fix: Cloudflare dashboard → Rules → Transform Rules → "Modify Request Header" → action: "Set static" → name `X-Tenant-Id` from `http.request.headers["x-tenant-id"]`. Persist.
3. Fallback: temporary `?tenant=<uuid>` query param read in FastAPI (`X-Tenant-Id` header takes precedence if both present). Behind a feature flag, removed after Transform Rule confirmed.

### 6.5 If rate-limit is hitting legitimate traffic

100 r/m per IP is generous for a demo but a noisy Cloudflare IP could trigger it. Diagnose with `tail -f /var/log/caddy/gecko-api.log | jq 'select(.status==429)'`. If a legitimate IP is being throttled (e.g., CF edge IP shared by many users), the fix is `key {http.request.header.cf-connecting-ip}` instead of `{remote_host}`. Default stays `{remote_host}` because CF preserves the visitor IP via `CF-Connecting-IP`.

---

## 7. Self-review checklist

Before declaring Security phase done, the agent checks every box:

- [ ] Migration `009_rls_policies.py` enables RLS on all 27 domain tables listed in ARCHITECTURE.md §3.9
- [ ] `core.users` and `regulatory.regulator_events` use the cross-tenant policy variant, not the standard one
- [ ] `gecko_api` role is `NOBYPASSRLS` (verified via `pg_roles`)
- [ ] `gecko_migrate` role is `BYPASSRLS` (verified) and only used by alembic
- [ ] `test_rls_isolation.py` passes (two-connection isolation test)
- [ ] `test_rls_no_orphan_tables.py` passes (every table in our schemas has `relrowsecurity=TRUE`)
- [ ] `ruff check --select=S608` clean on `apps/api/`
- [ ] ESLint `react/no-danger=error` enforced; only Scalar wrapper has the audited override
- [ ] `gitleaks detect --source .` clean on main
- [ ] Pre-commit hook installed in repo (`.pre-commit-config.yaml`) with gitleaks + ruff
- [ ] Caddy snippet `infra/caddy/gecko-api.caddy` matches the version in §3.7 above
- [ ] Cloudflare Transform Rule preserving `X-Tenant-Id` configured and verified via curl
- [ ] HSTS header observed on `gecko.radai-1984.dev/` and `api.gecko.radai-1984.dev/healthz`
- [ ] Three demo tenant UUIDs documented in `docs/demo-tenants.md`
- [ ] `<KEPSignBadge>` requires `demo={true}` prop; component throws otherwise; smoke test asserts watermark visible
- [ ] CORS allow-list enforced at both Caddy and FastAPI layers; no `*`
- [ ] `.env.example` committed; `.env` in `.gitignore`; no real secrets in repo

If every box is checked → Security phase DONE. Append entry to `PROGRESS.md` and (if anything went wrong) to `difficulties_log.md`.

---

## 8. Done definition

Security phase is **DONE** when:

1. All 10 success criteria in §1 are green (and stay green in CI).
2. All 17 self-review items in §7 are checked.
3. RLS audit report `audit/RLS_AUDIT.md` is written (one row per table, policy applied, test passing).
4. No items in §1 or §7 have known workarounds that defer back-pressure to a later phase. If something is genuinely deferred (e.g., production-grade secret manager), it must be entered in `difficulties_log.md` with a clear "v3" tag.

Then PROGRESS.md gets an entry like:

```
- 2026-05-23 — Stage 4.13 (Security audit) DONE. Output: audit/RLS_AUDIT.md, .gitleaks.toml, test_rls_isolation.py, test_rls_no_orphan_tables.py.
  All 10 success criteria green. Notable: Caddy ratelimit plugin verified present on Hetzner; Cloudflare Transform Rule for X-Tenant-Id configured.
```
