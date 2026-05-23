# DEVOPS_INSTRUCTIONS — GECKO VPP v2

**Owner:** DevOps lead (Operations Specialist Lead bundle).
**Authoritative source:** `ARCHITECTURE.md` §13 (Deployment topology), §13.6 (Deploy sequence), §11 FMEA F03–F05, F14, F17, F18.
**Brief reference:** `PRODUCT_BRIEF.md` §11.24 (Smoke pass), §11.25 (production-fidelity feel), §13 risks (Vercel + Next 16 hidden bugs).
**HLA reference:** `HIGH_LEVEL_ARCHITECTURE.md` §2.3 (DNS/CDN), §2.4 (v1 coexistence).
**Status:** v0.1 — 2026-05-23. Frozen for Phase 4.14 execution.

---

## 0. Goal

Deploy GECKO VPP v2 with these traits, atomically and reversibly:

- **Frontend on Vercel** at `https://gecko.radai-1984.dev/` (Next.js 16 App Router from monorepo subpath `apps/web/`).
- **Backend on Hetzner VPS** (`178.105.209.14`) at `https://api.gecko.radai-1984.dev/` (FastAPI + Postgres 16 in Docker, fronted by existing Caddy at `/etc/caddy/Caddyfile`).
- **DNS via Cloudflare** (zone `radai-1984.dev`, zone id `f12805dc...`, token at `~/.cloudflare/api-token`).
- **Public GitHub repo** `basisabp1984/gecko-vpp-rebuild` (MIT).
- **v1 stays live untouched** at `vpp.radai-1984.dev` (its own Vercel project; not modified by this work).
- **No new secrets in repo**; `.env.example` only.
- **No paid third-party tools** (Sentry, Datadog, etc. — not used).

---

## 1. Success criteria (verifiable)

| # | Criterion | Verification command |
|---|---|---|
| D1 | `https://gecko.radai-1984.dev/` returns 200, persona picker `<PersonaPicker>` visible | `curl -I https://gecko.radai-1984.dev/` → `HTTP/2 200`; Playwright smoke on `/` passes |
| D2 | `https://api.gecko.radai-1984.dev/openapi.json` returns valid OpenAPI 3.1 JSON | `curl -s https://api.gecko.radai-1984.dev/openapi.json \| jq .openapi` → `"3.1.0"` |
| D3 | `https://api.gecko.radai-1984.dev/healthz` returns 200 with `{"ok": true, "db": "up"}` | `curl -s https://api.gecko.radai-1984.dev/healthz` |
| D4 | Postgres reachable from the `api` container, 30 days of seeded data present | `docker compose exec api python -c "import asyncpg, asyncio; asyncio.run(asyncpg.connect(...).fetchval('SELECT count(*) FROM market.rdn_prices'))"` → ≥ 2160 |
| D5 | GitHub repo `basisabp1984/gecko-vpp-rebuild` is public, CI green on `main` | `gh repo view basisabp1984/gecko-vpp-rebuild --json visibility,defaultBranchRef` |
| D6 | v1 at `vpp.radai-1984.dev` still serves (HTTP 200 + visible content unchanged) | `curl -I https://vpp.radai-1984.dev/` |
| D7 | TLS cert valid on both gecko.* and api.gecko.* | `openssl s_client -connect gecko.radai-1984.dev:443 -servername gecko.radai-1984.dev </dev/null 2>/dev/null \| openssl x509 -noout -dates` |
| D8 | Smoke test passes against production URLs (`BASE_URL=https://gecko.radai-1984.dev pnpm -F web test:smoke`) | CI smoke job green |
| D9 | Caddy `/etc/caddy/Caddyfile` validates cleanly after adding gecko vhost | `caddy validate --config /etc/caddy/Caddyfile` exit 0 |
| D10 | `synth_coverage.md` on the VPS shows all ✅ after seed | `cat /opt/gecko-vpp/phase-3-architecture/synth_coverage.md \| grep ❌` returns empty |

All 10 green → deploy DONE.

---

## 2. Tools

| Tool | Purpose | Notes |
|---|---|---|
| `gh` CLI | GitHub repo create, branch protect, secret upload | Pre-authenticated on user's machine (`gh auth status`) |
| `vercel` CLI | Project link, env vars, custom domain attach | Login: `vercel login` (browser flow) |
| Cloudflare API (curl with token) | DNS records | Token at `~/.cloudflare/api-token`; zone id `f12805dc...` |
| `ssh` to `root@178.105.209.14` | Hetzner host operations | Existing user key; no new credentials |
| `docker` + `docker compose` v2 | Backend stack on Hetzner | Existing engine on host |
| Existing `caddy` on host | Reverse proxy + TLS + rate-limit | `/etc/caddy/Caddyfile` — **APPEND ONLY, never replace** |
| `psql` / `pg_dump` | DB ops on the VPS | Used for backup before destructive migrations |

**Out of scope.** No nginx (Caddy already on host). No Kubernetes (single-VPS demo). No managed Postgres (Docker'd Postgres on the same VPS). No Sentry / Datadog.

---

## 3. Topology recap

```
                  ┌────────────────────────────┐
  user-browser ───►   Cloudflare CDN (proxied) │
                  └──┬─────────────────────────┘
                     │
   ┌─────────────────┴─────┬──────────────────────────┐
   │                       │                          │
   ▼                       ▼                          ▼
gecko.radai-           api.gecko.radai-           vpp.radai-1984.dev
 1984.dev               1984.dev                  (V1 — UNTOUCHED)
   │                       │
   │ CNAME                 │ A 178.105.209.14
   ▼                       ▼
Vercel project          Hetzner VPS (178.105.209.14)
  gecko-vpp-rebuild       │
  Next.js 16              │  Caddy :443  (existing — APPEND vhost)
  apps/web/               │     │
                          │     ├─► localhost:8000 (api)
                          │     ├─► n8n           (existing)
                          │     ├─► vodokanal     (existing)
                          │     └─► zhytomyr      (existing)
                          │
                          │  Docker compose at /opt/gecko-vpp/
                          │     ├─ api (FastAPI :8000)
                          │     ├─ postgres :5432 bind 127.0.0.1
                          │     └─ synth (one-shot, restart: no)
                          │
                          │  Postgres volume: gecko_pg_data
                          │  Logs: /var/log/caddy/gecko-api.log
```

---

## 4. Step-by-step deploy plan

### Phase A — GitHub repo

**Goal:** Public repo `basisabp1984/gecko-vpp-rebuild`, MIT licensed, with code from `d:\ВС коде вайбкодинг\gecko-vpp-rebuild\`.

**Pre-check:**
```bash
cd "/d/ВС коде вайбкодинг/gecko-vpp-rebuild"
ls -la .git || echo "not a git repo yet"
gh auth status
```

**Steps:**

1. Initialise git in the project root.
   ```bash
   git init -b main
   ```

2. Write `.gitignore` covering all sensitive and generated paths (see §6.1 below for full content).

3. Write `LICENSE` (MIT, copyright `2026 Andrii Liubarskyi`).

4. Write `README.md` (see §6.2 for content).

5. Stage and commit, **named files only — never `git add -A` on this repo**:
   ```bash
   git add .gitignore LICENSE README.md PRODUCT_BRIEF.md PROGRESS.md difficulties_log.md
   git add phase-1-understanding/ phase-2-solution/ phase-3-architecture/
   git add apps/ packages/ infra/ pnpm-workspace.yaml pyproject.toml package.json
   git add tsconfig.base.json .nvmrc .python-version .env.example .gitleaks.toml
   git add .github/workflows/ci.yml .github/workflows/deploy.yml
   git add .pre-commit-config.yaml
   git status   # eyeball before commit; abort if anything sus is staged
   git commit -m "feat: initial commit of gecko-vpp-rebuild v2 monorepo

   Public repo for the GECKO VPP v2 demo. Includes architecture documents
   (Phase 1-3), apps/web (Next.js 16), apps/api (FastAPI), apps/synth
   (Python data generator), SDKs, infra, CI.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
   ```

6. Create the GitHub repo and push:
   ```bash
   gh repo create basisabp1984/gecko-vpp-rebuild \
     --public \
     --description "VPP demo: Next.js 16 + FastAPI + Postgres on Hetzner. Ukrainian energy market." \
     --source=. \
     --remote=origin \
     --push
   ```

7. Enable branch protection on `main`:
   ```bash
   gh api repos/basisabp1984/gecko-vpp-rebuild/branches/main/protection \
     --method PUT \
     --field required_status_checks[strict]=true \
     --field required_status_checks[contexts][]=lint.python \
     --field required_status_checks[contexts][]=lint.frontend \
     --field required_status_checks[contexts][]=test.unit.backend \
     --field required_status_checks[contexts][]=test.unit.frontend \
     --field required_status_checks[contexts][]=test.integration \
     --field required_status_checks[contexts][]=test.smoke \
     --field enforce_admins=false \
     --field required_pull_request_reviews=null \
     --field restrictions=null
   ```

   Note: solo dev → `required_pull_request_reviews=null` is intentional. Andrii can self-merge.

8. Verify CI runs (Phase A first push triggers it).
   ```bash
   gh run watch
   ```

   If CI fails at this stage with green-field code (lints fail because code isn't shipped yet) — that's expected; specialist leads' first commits will green it. The DevOps lead's job here is the workflow file exists and triggers.

### Phase B — Vercel frontend

**Goal:** `apps/web/` deployed at `https://gecko.radai-1984.dev/` via a new Vercel project, separate from v1.

**Pre-check:**
```bash
vercel whoami    # should show the same user account as v1
vercel ls        # confirm v1 project name; new project will NOT collide
```

**Steps:**

1. Link from monorepo subpath:
   ```bash
   cd apps/web
   vercel link --project gecko-vpp-rebuild
   ```
   When prompted:
   - Set up new project → yes
   - Scope → user's account (NOT a v1 team if separate)
   - Link to existing? → no
   - Root directory: leave as `./` (we're already in `apps/web`)
   - Build command: `pnpm -F web build` (or default `pnpm build` — depending on workspace setup)
   - Output dir: `.next`
   - Framework: Next.js (auto-detected)

2. Set env vars on Vercel project:
   ```bash
   vercel env add NEXT_PUBLIC_API_BASE_URL production
   # paste: https://api.gecko.radai-1984.dev
   vercel env add NEXT_PUBLIC_DEMO_MODE production
   # paste: true
   ```

3. Trigger first deploy:
   ```bash
   vercel --prod
   ```
   Vercel returns a deploy URL like `https://gecko-vpp-rebuild-xxx.vercel.app`. **Verify the deploy succeeded** before adding the custom domain.

4. **Pin `@vercel/analytics` away from the broken version.** Per memory `project_vercel_analytics_next16_bug.md` and FMEA F04:
   ```bash
   # in apps/web/package.json — if @vercel/analytics is present at all, pin:
   #   "@vercel/analytics": "~1.5.0"
   # Prefer: don't install it. Next 16 + @vercel/analytics@2.x breaks Vercel modifyConfig.
   ```

5. Attach custom domain:
   ```bash
   vercel domains add gecko.radai-1984.dev
   # Vercel returns a CNAME target like `cname.vercel-dns.com` — note it down for Phase C
   ```

6. Vercel automatically connects to GitHub if `vercel link` saw a `github.com` remote — confirm via dashboard. Otherwise:
   ```bash
   vercel git connect
   ```
   Production branch: `main`. PRs auto-deploy preview URLs.

### Phase C — DNS (Cloudflare)

**Goal:** Two records added to `radai-1984.dev` zone.

**Pre-check:**
```bash
# token file exists per memory reference_cloudflare_api_token.md
ls -la ~/.cloudflare/api-token
CF_TOKEN=$(cat ~/.cloudflare/api-token)
CF_ZONE="f12805dc..."  # full zone id from memory
# verify access
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$CF_ZONE" | jq .result.name
# expect: "radai-1984.dev"
```

**Steps:**

1. Create CNAME for frontend (proxied=false; Vercel manages its own TLS for this CNAME):
   ```bash
   curl -s -X POST \
     -H "Authorization: Bearer $CF_TOKEN" \
     -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$CF_ZONE/dns_records" \
     -d '{
       "type": "CNAME",
       "name": "gecko",
       "content": "cname.vercel-dns.com",
       "proxied": false,
       "ttl": 1
     }' | jq .success
   ```

2. Create A record for backend (proxied=true; Cloudflare TLS + rate-limit + DDoS):
   ```bash
   curl -s -X POST \
     -H "Authorization: Bearer $CF_TOKEN" \
     -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$CF_ZONE/dns_records" \
     -d '{
       "type": "A",
       "name": "api.gecko",
       "content": "178.105.209.14",
       "proxied": true,
       "ttl": 1
     }' | jq .success
   ```

3. Add the **Cloudflare Transform Rule preserving `X-Tenant-Id`** (FMEA F14 mitigation). Cloudflare strips non-standard headers by default if the proxied domain is "Pro plan"; on the free plan, headers pass through, but we add the rule defensively.
   - Cloudflare dashboard → Rules → Transform Rules → "Modify Request Header"
   - Action: "Set static" → name `X-Tenant-Id` → value `http.request.headers["x-tenant-id"][0]`
   - Scope: hostname equals `api.gecko.radai-1984.dev`

   Verification from any machine:
   ```bash
   curl -I -H "X-Tenant-Id: 00000000-0000-4000-8000-000000000001" \
     https://api.gecko.radai-1984.dev/healthz
   # FastAPI logs should show the X-Tenant-Id value received
   ssh root@178.105.209.14 'docker compose -f /opt/gecko-vpp/docker-compose.yml logs api | grep tenant_id | tail -3'
   ```

4. Propagation: usually < 60s for Cloudflare records. If `dig gecko.radai-1984.dev @1.1.1.1` doesn't return the new record after 2 min, abort and check the API response from step 1/2.

### Phase D — Hetzner backend

**Goal:** Docker stack at `/opt/gecko-vpp/` running `api` + `postgres`, with synth seed completed.

**Pre-check:**
```bash
ssh root@178.105.209.14 'docker --version; docker compose version; ls /opt/'
# expect: docker engine present, compose v2, /opt contains n8n vodokanal zhytomyr
```

**Steps:**

1. Pick a free local port for FastAPI. Default is 8000; if taken (zhytomyr might use it — check first):
   ```bash
   ssh root@178.105.209.14 'ss -tlnp | grep -E "(8000|8001|8002)"'
   ```
   Use the first free; update `docker-compose.yml` and the Caddy snippet. **Document the chosen port in `difficulties_log.md` if not 8000.**

2. Provision directory:
   ```bash
   ssh root@178.105.209.14 'mkdir -p /opt/gecko-vpp && chown root:root /opt/gecko-vpp'
   ```

3. Deploy code. Two options:
   - **Option A (preferred):** clone the public GitHub repo on the VPS:
     ```bash
     ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
       git clone https://github.com/basisabp1984/gecko-vpp-rebuild.git .'
     ```
   - **Option B (fallback if repo not yet pushed or network issue):** `rsync` from local:
     ```bash
     rsync -avz --exclude=node_modules --exclude=__pycache__ --exclude=.next --exclude=dist --exclude=.env \
       "/d/ВС коде вайбкодинг/gecko-vpp-rebuild/" \
       root@178.105.209.14:/opt/gecko-vpp/
     ```

4. Create `/opt/gecko-vpp/.env` from `.env.example`. Generate real passwords on the VPS — never via clipboard:
   ```bash
   ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
     cp .env.example .env && \
     PW=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24) && \
     sed -i "s|change_me|$PW|g" .env && \
     chmod 0640 .env && chown root:root .env'
   ```

5. Pull / build images and start Postgres first:
   ```bash
   ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
     docker compose -f infra/docker/docker-compose.yml pull && \
     docker compose -f infra/docker/docker-compose.yml up -d postgres'
   ```

6. Wait for Postgres readiness:
   ```bash
   ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
     for i in $(seq 1 30); do \
       docker compose -f infra/docker/docker-compose.yml exec -T postgres pg_isready -U gecko_api && break; \
       sleep 2; \
     done'
   ```

7. Run migrations as `gecko_migrate` role (BYPASSRLS so schema creation succeeds):
   ```bash
   ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
     docker compose -f infra/docker/docker-compose.yml run --rm api \
       alembic upgrade head'
   ```

8. Run synth seed (one-shot container):
   ```bash
   ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
     docker compose -f infra/docker/docker-compose.yml run --rm synth \
       python -m synth'
   ```

9. Check synth coverage:
   ```bash
   ssh root@178.105.209.14 'cat /opt/gecko-vpp/phase-3-architecture/synth_coverage.md | head -30'
   # Verify zero ❌
   ssh root@178.105.209.14 'grep "❌" /opt/gecko-vpp/phase-3-architecture/synth_coverage.md && echo FAIL || echo OK'
   ```
   If any ❌ → **STOP**. Do not proceed to next step. Open an issue with the synth output; fix the synth code; reseed (synth truncates and reseeds, per HLA §5.2).

10. Start the API:
    ```bash
    ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
      docker compose -f infra/docker/docker-compose.yml up -d api'
    ```

11. Verify API responds locally on VPS:
    ```bash
    ssh root@178.105.209.14 'curl -s http://localhost:8000/healthz | jq .'
    # expect: {"ok": true, "db": "up"}
    ```

### Phase E — Caddy on host

**Goal:** Append the gecko-api vhost to `/etc/caddy/Caddyfile`. **Never edit existing blocks for n8n, vodokanal, zhytomyr, ses.**

**Pre-check:**
```bash
ssh root@178.105.209.14 'caddy version'
ssh root@178.105.209.14 'cat /etc/caddy/Caddyfile | head -50'
ssh root@178.105.209.14 'caddy list-modules 2>/dev/null | grep -i ratelimit'
# If ratelimit module is NOT in the binary, see §5.3 below for the workaround.
```

**Steps:**

1. **Backup** the existing Caddyfile:
   ```bash
   ssh root@178.105.209.14 'cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak.$(date +%Y%m%d-%H%M)'
   ```

2. Two ways to add the gecko snippet:
   - **Option A (preferred):** Caddyfile uses `import` directive somewhere. Add a line `import /opt/gecko-vpp/infra/caddy/gecko-api.caddy` to the global block. Cleaner — gecko's snippet stays in the repo.
   - **Option B:** Append the snippet contents directly to `/etc/caddy/Caddyfile`. Use this if there's no top-level `import`.

   ```bash
   # Option A
   ssh root@178.105.209.14 'grep -q "gecko-vpp" /etc/caddy/Caddyfile || \
     echo "import /opt/gecko-vpp/infra/caddy/gecko-api.caddy" >> /etc/caddy/Caddyfile'

   # Option B (only if no `import` directive — adapt to context)
   ssh root@178.105.209.14 'cat /opt/gecko-vpp/infra/caddy/gecko-api.caddy >> /etc/caddy/Caddyfile'
   ```

3. **Validate** before reload (FMEA F03 mitigation):
   ```bash
   ssh root@178.105.209.14 'caddy validate --config /etc/caddy/Caddyfile'
   ```
   If exit ≠ 0 → restore from backup; investigate; do NOT reload.

4. Reload Caddy:
   ```bash
   ssh root@178.105.209.14 'systemctl reload caddy'
   # check status
   ssh root@178.105.209.14 'systemctl status caddy --no-pager | head -10'
   ```

5. Caddy auto-provisions Let's Encrypt cert for `api.gecko.radai-1984.dev`. First request takes 2–10 seconds extra. Verify TLS:
   ```bash
   curl -I https://api.gecko.radai-1984.dev/healthz
   # expect: HTTP/2 200, server: Caddy
   ```

### Phase F — Verification

Run from a clean machine (not the VPS).

```bash
# D1: frontend renders
curl -s -o /dev/null -w "%{http_code}\n" https://gecko.radai-1984.dev/
# expect: 200

# D2: openapi served
curl -s https://api.gecko.radai-1984.dev/openapi.json | jq '.openapi'
# expect: "3.1.0"

# D3: health up
curl -s https://api.gecko.radai-1984.dev/healthz | jq .
# expect: {"ok": true, "db": "up"}

# D4: row counts (via API)
curl -s -H "X-Tenant-Id: 00000000-0000-4000-8000-000000000001" \
  https://api.gecko.radai-1984.dev/api/v1/market/rdn?date_from=2026-04-23&date_to=2026-05-23 | jq '.data | length'
# expect: ≥ 720 (1 tenant × 30 days × 24 hours)

# D5: repo public
gh repo view basisabp1984/gecko-vpp-rebuild --json visibility,defaultBranchRef -q '.visibility'
# expect: "PUBLIC"

# D6: v1 still serves
curl -I https://vpp.radai-1984.dev/
# expect: HTTP/2 200

# D7: TLS valid
echo | openssl s_client -connect gecko.radai-1984.dev:443 -servername gecko.radai-1984.dev 2>/dev/null | openssl x509 -noout -dates
echo | openssl s_client -connect api.gecko.radai-1984.dev:443 -servername api.gecko.radai-1984.dev 2>/dev/null | openssl x509 -noout -dates

# D8: smoke against prod
cd "/d/ВС коде вайбкодинг/gecko-vpp-rebuild"
BASE_URL=https://gecko.radai-1984.dev pnpm -F web test:smoke
```

If any of D1–D10 fails → rollback per §5 below; do not declare done.

### Phase G — Cleanup and documentation

1. Update `PROGRESS.md`:
   ```
   - 2026-05-23 — Stage 4.14 (Deploy) DONE. Frontend at https://gecko.radai-1984.dev/, backend at https://api.gecko.radai-1984.dev/. v1 at vpp.radai-1984.dev verified still live.
   ```

2. Update `README.md` with the live URLs and at least one screenshot (use Playwright to capture):
   ```bash
   BASE_URL=https://gecko.radai-1984.dev pnpm -F web playwright test --update-snapshots tests/screenshots.spec.ts
   git add apps/web/tests/screenshots/
   git commit -m "docs: add prod screenshots to README"
   git push
   ```

3. Set repo description and topics:
   ```bash
   gh repo edit basisabp1984/gecko-vpp-rebuild \
     --description "VPP demo: Next.js 16 + FastAPI + Postgres on Hetzner. Ukrainian energy market. Light + dark themes, persona-aware AI agents (deterministic classifier), public dev portal, both SDKs." \
     --add-topic vpp \
     --add-topic energy \
     --add-topic nextjs \
     --add-topic fastapi \
     --add-topic ukraine
   ```

4. Final secret scan on the pushed repo:
   ```bash
   gitleaks detect --source . --no-banner
   # exit 0 required
   ```

5. Append to `difficulties_log.md` any obstacles hit during deploy.

---

## 5. Rollback plan

### 5.1 Frontend rollback (Vercel)

Vercel keeps every previous deployment. To revert:
```bash
vercel ls gecko-vpp-rebuild   # list recent deployments
vercel promote <previous-deploy-url> --prod
```
Or via dashboard: Deployments → previous green one → "..." → "Promote to Production".

**No downtime.** Vercel atomic swap.

### 5.2 Backend rollback (Hetzner)

Two scenarios:

**A. Bad image / bad code.**
```bash
ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
  git fetch origin && \
  git checkout <previous-good-sha> && \
  docker compose -f infra/docker/docker-compose.yml build api && \
  docker compose -f infra/docker/docker-compose.yml up -d api'
```

**B. Bad migration.**
```bash
# Restore from backup taken pre-migration
ssh root@178.105.209.14 'cd /opt/gecko-vpp && \
  docker compose -f infra/docker/docker-compose.yml exec -T postgres \
    pg_restore -U gecko_migrate -d gecko --clean --if-exists < backup/<timestamp>.pgdump'
```

Backup is taken automatically before every alembic upgrade — script `infra/scripts/pre-migrate-backup.sh` runs in CI / deploy.

### 5.3 Caddy rollback

```bash
ssh root@178.105.209.14 'cp /etc/caddy/Caddyfile.bak.<timestamp> /etc/caddy/Caddyfile && \
  caddy validate --config /etc/caddy/Caddyfile && \
  systemctl reload caddy'
```

### 5.4 DNS rollback

Cloudflare records can be deleted via API:
```bash
RECORD_ID=$(curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$CF_ZONE/dns_records?name=gecko.radai-1984.dev" \
  | jq -r '.result[0].id')
curl -s -X DELETE -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$CF_ZONE/dns_records/$RECORD_ID"
```
Propagation: 1–5 min. v1 at `vpp.radai-1984.dev` unaffected because it uses a separate record.

---

## 6. Reference content

### 6.1 `.gitignore` (root)

```gitignore
# OS
.DS_Store
Thumbs.db

# Node
node_modules/
.next/
dist/
build/
*.tsbuildinfo

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage

# Env / secrets — NEVER commit these
.env
.env.local
.env.*.local
*.pem
*.key

# Generated reports
synth_coverage.md
phase-3-architecture/synth_coverage.md

# IDE
.vscode/
.idea/

# Logs
*.log
logs/

# OS / editor leftovers
*.swp
.bak.*
```

### 6.2 `README.md` skeleton

```markdown
# GECKO VPP v2

A demo of a Virtual Power Plant (VPP) platform for the Ukrainian energy market.

**Live demo:** https://gecko.radai-1984.dev
**API:** https://api.gecko.radai-1984.dev
**Dev portal:** https://gecko.radai-1984.dev/developer/
**API explorer:** https://gecko.radai-1984.dev/developer/api/explorer

## What's in this repo

- `apps/web` — Next.js 16 frontend (Vercel)
- `apps/api` — FastAPI backend (Hetzner VPS, Docker)
- `apps/synth` — Python synthetic data generator
- `packages/sdk-ts`, `packages/sdk-py` — public SDKs
- `infra/` — Docker compose + Caddy snippet
- `phase-1-understanding/`, `phase-2-solution/`, `phase-3-architecture/` — full design trail

## Important caveats (read before judging)

- **The data is synthetic.** A Python generator seeds 30 days of Ukrainian-market-shaped data.
- **The КЕП (digital signature) is a stub.** Every signed-document badge shows DEMO; no real crypto.
- **The AI agents are deterministic, not LLM-based.** Keyword classifier + per-persona Jinja templates.
- **Tenancy is mocked.** Three demo tenants (producer-1, ci-1, storage-1); RLS enforces real isolation in Postgres.
- **The voice agent runs in stub mode by default.** OpenAI Realtime path is wired but disabled.

## License

MIT
```

### 6.3 GitHub Actions deploy workflow (sketch)

`.github/workflows/deploy.yml` — triggers on push to `main` after CI is green:

```yaml
name: deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: deploy
  cancel-in-progress: false

jobs:
  vercel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: apps/web

  hetzner:
    runs-on: ubuntu-latest
    needs: vercel
    steps:
      - name: deploy via ssh
        uses: appleboy/ssh-action@v1
        with:
          host: 178.105.209.14
          username: root
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: |
            set -euo pipefail
            cd /opt/gecko-vpp
            ./infra/scripts/pre-migrate-backup.sh
            git fetch origin
            git checkout ${{ github.sha }}
            docker compose -f infra/docker/docker-compose.yml pull
            docker compose -f infra/docker/docker-compose.yml run --rm api alembic upgrade head
            docker compose -f infra/docker/docker-compose.yml up -d api

  smoke:
    runs-on: ubuntu-latest
    needs: hetzner
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: pnpm install
      - run: BASE_URL=https://gecko.radai-1984.dev pnpm -F web test:smoke
```

---

## 7. Pre-flight + Branching protocol

### 7.1 Pre-flight (the user's 4 questions)

1. **What does success look like?** All 10 D-criteria in §1 green. Frontend and backend live, v1 still serves, CI green, README has the live URL, no secrets in repo. Failure = any 1 of 10 red.

2. **What inputs do I have?** ARCHITECTURE.md §13 (deploy topology + sequence), §9 (security model), §11 FMEA F03–F05 + F14 + F17. HIGH_LEVEL_ARCHITECTURE.md §2.3, §2.4. Existing infra on Hetzner (`/opt/n8n`, `/opt/vodokanal`, `/opt/zhytomyr`, `/opt/ses`). Cloudflare token at `~/.cloudflare/api-token`. Memories: `reference_cloudflare_api_token.md`, `project_vercel_analytics_next16_bug.md`, `reference_zhytomyr_forecast.md` (template for Caddy + Compose layout).

3. **What is the smallest, safest first move?** **Phase A (GitHub repo init + push)** — completely reversible (just don't add the remote yet), tests CI workflow file, doesn't touch any live system. **Do NOT touch Cloudflare or Caddy first.** Phases B, C, D, E follow only after Phase A is green.

4. **What could go wrong, and what's my rollback?**
   - **Vercel deploy fails on Next 16 due to `@vercel/analytics`** (memory `project_vercel_analytics_next16_bug.md` + FMEA F04) → pin or omit the package; remediation is in the memory.
   - **Caddy reload fails** (existing config has syntax error from another project, or new snippet has a typo) → `caddy validate` BEFORE reload, restore `.bak.<timestamp>` on failure.
   - **Port 8000 collision** with existing service → check `ss -tlnp`; pick next free; update compose + Caddy snippet + `difficulties_log.md`.
   - **Cloudflare strips `X-Tenant-Id`** (FMEA F14) → Transform Rule in Phase C step 3.
   - **DNS propagation slow** → propagation max 5–10 min on Cloudflare; if longer, abort and check API response on record creation step.
   - **Docker image pull slow on Hetzner** → patience; do not kill. If genuinely hung > 10 min, check `docker pull` directly with verbose logs.
   - **Postgres noisy-neighbor** with n8n / zhytomyr (FMEA F17) → resource limits `cpus: '2.0'`, `mem_limit: 2g` in compose (already specified in ARCHITECTURE.md §13.2).
   - **Migration breaks** → pg_dump backup taken pre-migration via `infra/scripts/pre-migrate-backup.sh`; restore via `pg_restore` per §5.2B.

### 7.2 Branching protocol

- Branch name: `deploy/<phase>` (e.g. `deploy/phase-a-github`, `deploy/phase-d-hetzner`).
- One PR per phase A–G. Each PR must demonstrate its phase's success criteria in the description (curl outputs, screenshots).
- Final merge to `main` triggers `.github/workflows/deploy.yml` which runs Vercel deploy + Hetzner SSH + post-deploy smoke.

---

## 8. Operations runbook (post-launch)

### 8.1 Daily

- Caddy logs rotate weekly (existing logrotate config covers).
- Postgres backup runs nightly via cron on the VPS:
  ```bash
  # /opt/gecko-vpp/infra/scripts/nightly-backup.sh
  set -e
  cd /opt/gecko-vpp
  mkdir -p backup
  docker compose -f infra/docker/docker-compose.yml exec -T postgres \
    pg_dump -Fc -U gecko_migrate gecko > backup/$(date +%Y%m%d).pgdump
  find backup/ -name '*.pgdump' -mtime +7 -delete
  ```
  Add to root's crontab on the VPS:
  ```
  15 3 * * * /opt/gecko-vpp/infra/scripts/nightly-backup.sh >> /var/log/gecko-backup.log 2>&1
  ```

### 8.2 Common operations

| Operation | Command |
|---|---|
| Tail API logs | `ssh root@178.105.209.14 'docker compose -f /opt/gecko-vpp/infra/docker/docker-compose.yml logs -f --tail=50 api'` |
| Restart API | `ssh root@178.105.209.14 'cd /opt/gecko-vpp && docker compose -f infra/docker/docker-compose.yml restart api'` |
| Reseed DB | `ssh root@178.105.209.14 'cd /opt/gecko-vpp && docker compose -f infra/docker/docker-compose.yml run --rm synth python -m synth'` |
| psql shell | `ssh root@178.105.209.14 'cd /opt/gecko-vpp && docker compose -f infra/docker/docker-compose.yml exec postgres psql -U gecko_migrate gecko'` |
| Check resource usage | `ssh root@178.105.209.14 'docker stats --no-stream'` |

### 8.3 Promotion to v1 retirement (future)

When user accepts v2, retire v1:
1. Confirm 24h of green smoke on v2 prod URLs.
2. Edit v1 Vercel project: redirect `vpp.radai-1984.dev` → `gecko.radai-1984.dev` (301 via vercel.json `redirects`).
3. Keep v1 Vercel project around for 30 days; then delete after no incoming traffic.

Not required for v2 acceptance. v1 stays until Andrii says otherwise.

---

## 9. Self-review checklist

- [ ] Phase A done: repo public, `main` protected, CI workflow file present
- [ ] Phase B done: Vercel project `gecko-vpp-rebuild` linked to repo, custom domain attached, env vars set
- [ ] Phase C done: two DNS records present (CNAME + A) verified via `dig`, Transform Rule for `X-Tenant-Id` configured
- [ ] Phase D done: `/opt/gecko-vpp/` directory exists, `.env` mode 0640, compose stack running, alembic applied, synth seeded, `synth_coverage.md` all ✅
- [ ] Phase E done: Caddyfile.bak.* exists, validate passed, reload succeeded, TLS provisioned
- [ ] Phase F done: all 10 D-criteria verified via curl from a clean machine
- [ ] Phase G done: README has live URL + screenshot, repo description and topics set, gitleaks scan clean
- [ ] No secrets in repo (`gitleaks detect` clean)
- [ ] v1 site `vpp.radai-1984.dev` confirmed still live (D6)
- [ ] Existing services on Hetzner (n8n, vodokanal, zhytomyr, ses) confirmed still live — `curl -I` each
- [ ] Nightly Postgres backup cron added on VPS
- [ ] Deploy workflow `.github/workflows/deploy.yml` runs successfully on `main` push
- [ ] PROGRESS.md updated with deploy timestamp
- [ ] `difficulties_log.md` has entry for any obstacle encountered

If every box is checked → Deploy phase DONE.

---

## 10. Done definition

Deploy phase is **DONE** when:

1. All 10 D-criteria in §1 are green.
2. All 14 self-review items in §9 are checked.
3. A 24-hour soak passes — re-run smoke from a CI runner the next day and assert all green.
4. Andrii can hit `https://gecko.radai-1984.dev/` and see the persona picker with the slide-7 architecture diagram.
5. v1 (`vpp.radai-1984.dev`) is confirmed still functional and untouched.

The deploy report goes into `PROGRESS.md`:

```
- 2026-05-23 — Stage 4.14 (Deploy) DONE.
  Frontend: https://gecko.radai-1984.dev/ (Vercel project gecko-vpp-rebuild, custom domain, CI auto-deploy).
  Backend: https://api.gecko.radai-1984.dev/ (Hetzner 178.105.209.14, port 8000, Caddy-fronted).
  GitHub: basisabp1984/gecko-vpp-rebuild (public, MIT, CI green).
  v1 at vpp.radai-1984.dev verified still live.
  10/10 success criteria green. 14/14 self-review items checked.
```
