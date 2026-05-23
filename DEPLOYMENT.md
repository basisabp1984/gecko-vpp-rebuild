# DEPLOYMENT — self-hosting Krytsia from scratch

This guide takes a fresh Linux server + a fresh Vercel account and walks
you to a working Krytsia deployment. The reference deployment uses
`radai-1984.dev` on Hetzner + Cloudflare — substitute your own domain
and host wherever you see those values.

---

## 1. Prerequisites

| What | Why |
|---|---|
| **Linux server with Docker** (Hetzner CX22+, DigitalOcean droplet, your own VPS — anything that can run Docker Compose v2) | hosts `gecko-postgres` + `gecko-api` |
| **A shared Caddy container** on the same host, exposing a network named `caddy_web` | reverse proxy + Let's Encrypt for the API subdomain |
| **Cloudflare account** with an API token (`Zone:DNS:Edit` on your zone) | DNS for the API + frontend hostnames |
| **Vercel account** + Vercel CLI (`npm i -g vercel`) | frontend deploy |
| **Domain name** you control, with DNS hosted on Cloudflare | the reference repo uses `radai-1984.dev` — replace with yours |
| **GitHub repo** (your fork of this repo) | source of truth for Vercel auto-deploy + `git clone` on the server |

Server packages assumed: `docker.io` (or `docker-ce`),
`docker-compose-plugin`, `git`, `curl`, `jq`.

---

## 2. Backend on Hetzner (or any Linux + Docker host)

### 2.1 Prepare the server

```bash
# As root on the VPS
apt update
apt install -y docker.io docker-compose-plugin git

mkdir -p /opt/gecko-vpp
cd /opt/gecko-vpp
git clone https://github.com/<your-fork>/gecko-vpp-rebuild.git .
```

> If you are reusing the existing Hetzner host (`/opt/n8n`, `/opt/zhytomyr`,
> `/opt/vodokanal` already there), the shared Caddy container and the
> `caddy_web` Docker network already exist. Skip to §2.3.

### 2.2 Set up the shared Caddy network (only if you do not have one yet)

Krytsia expects an external Docker network named `caddy_web` and a
Caddy container attached to it. The minimal setup:

```bash
docker network create caddy_web
docker run -d \
  --name caddy \
  --restart unless-stopped \
  --network caddy_web \
  -p 80:80 -p 443:443 \
  -v /opt/caddy/Caddyfile:/etc/caddy/Caddyfile:ro \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:2-alpine
```

### 2.3 Environment file

Copy and edit `.env`:

```bash
cd /opt/gecko-vpp
cp .env.example .env
$EDITOR .env
```

Minimum values to set for a production deploy:

```env
# Database
POSTGRES_DB=gecko_vpp
POSTGRES_USER=gecko
POSTGRES_PASSWORD=<a strong random string — pwgen -s 32 1>

# Backend
APP_ENV=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://krytsia.your-domain.tld

# Demo tenants — keep these fixed UUIDs if you want the seeded data
# generator to populate matching rows. Change them only if you are
# building a fresh dataset.
TENANT_PRODUCER_UUID=11111111-1111-1111-1111-111111111111
TENANT_CI_UUID=22222222-2222-2222-2222-222222222222
TENANT_STORAGE_UUID=33333333-3333-3333-3333-333333333333

# Voice agent
VOICE_PROVIDER=stub
# OPENAI_API_KEY=sk-...  # only if VOICE_PROVIDER=openai-realtime

# Synth window + RNG seed (lock these to keep the demo reproducible)
SYNTH_DATE_START=2026-04-23
SYNTH_DATE_END=2026-05-23
SYNTH_RNG_SEED=42
```

`.env` is gitignored. Never commit it.

### 2.4 Bring the stack up

**Production requires BOTH compose files.** This is the most common
foot-gun on this project:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

What the overlay does:

- Drops the host port mappings (so Postgres + the API are not reachable
  from the public internet).
- Attaches `gecko-api` to the external `caddy_web` network so the
  shared Caddy container can reach `gecko-api:8000` via Docker DNS.

If you run only the base file in production, Caddy returns
`502 Bad Gateway` with `dial tcp: lookup gecko-api on 127.0.0.11:53: server
misbehaving` in the logs — that means `caddy_web` is not attached.

Verify both containers are healthy:

```bash
docker compose ps
docker compose logs --tail=50 api
```

### 2.5 Migrations and seed

Migrations run inside the `api` container (alembic 1.13 with sync
psycopg driver — async + alembic is more pain than worth):

```bash
docker compose exec api alembic upgrade head
```

Expected output ends with `Running upgrade ... -> 012, seed core lookups`.

Seed the synthetic data. The generator is **not** baked into the API
image; install it in its own venv on the host (or run it from your
laptop pointed at the prod DB through the bastion of your choice):

```bash
cd /opt/gecko-vpp/data-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Use the same DATABASE_URL the API uses
export DATABASE_URL='postgresql+asyncpg://gecko:<password>@127.0.0.1:5433/gecko_vpp'
# (Postgres is bound only to 127.0.0.1:5433 from the host — fine from inside the VPS)

python -m data_generator.main --reset
python -m data_generator.coverage   # exits 0 if every §11 criterion has rows
```

`--reset` truncates every domain table and reseeds; without `--reset`
the run is idempotent (skips rows that already exist).

### 2.6 Caddyfile entry

Add the API hostname to the shared Caddyfile:

```caddyfile
api.gecko.your-domain.tld {
    encode zstd gzip
    reverse_proxy gecko-api:8000
}
```

Reload Caddy without dropping connections:

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

The `gecko-api` hostname resolves because both `caddy` and `gecko-api`
are on the `caddy_web` network — Docker provides DNS.

---

## 3. Frontend on Vercel

```bash
cd apps/web

# One-time:
vercel link                                       # link to your Vercel project
vercel env add NEXT_PUBLIC_API_BASE production    # value: https://api.gecko.your-domain.tld
vercel env add NEXT_PUBLIC_GA_ID production       # optional: G-XXXXXXXXXX (skip to omit GA)

# Deploy:
vercel deploy --prod
```

If you push to `master` on GitHub the Vercel project auto-deploys; you
only need `vercel deploy --prod` for the first cut or for out-of-band
deploys.

The `apps/web/package.json` scripts use `next dev --webpack` and
`next build --webpack`. **Do not switch to Turbopack** —
`@scalar/api-reference-react` and `cmdk` import paths the Turbopack
resolver does not handle yet.

---

## 4. DNS via Cloudflare

Two records on your zone:

| Type | Name | Target | Proxy | Used for |
|---|---|---|---|---|
| `CNAME` | `krytsia` (or your chosen subdomain) | `cname.vercel-dns.com.` | DNS-only (grey cloud) | Vercel-served frontend |
| `A` | `api.gecko` (or your chosen API subdomain) | Hetzner VPS public IPv4 | DNS-only (grey cloud) | Caddy → FastAPI |

Cloudflare proxying ("orange cloud") on the API record breaks
Let's Encrypt HTTP-01 challenges on Caddy unless you switch to DNS-01.
Leaving it grey is simplest.

Cloudflare API token is stored at `~/.cloudflare/api-token` on the
operator's workstation (per the user's standing memory). To add a record
via API:

```bash
ZONE_ID=$(curl -s -H "Authorization: Bearer $(cat ~/.cloudflare/api-token)" \
  "https://api.cloudflare.com/client/v4/zones?name=your-domain.tld" | jq -r '.result[0].id')

curl -X POST -H "Authorization: Bearer $(cat ~/.cloudflare/api-token)" \
  -H "Content-Type: application/json" \
  -d '{"type":"A","name":"api.gecko","content":"<hetzner-ip>","proxied":false}' \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records"
```

---

## 5. Smoke-test

Once DNS, Caddy and Vercel are wired up:

```bash
# 1. API is reachable
curl -i https://api.gecko.your-domain.tld/
# expect: 200 OK + {"data":{"name":"GECKO VPP API","docs":"/docs","openapi":"/openapi.json"}}

# 2. OpenAPI is served
curl -s https://api.gecko.your-domain.tld/openapi.json | jq '.openapi'
# expect: "3.1.0"

# 3. A tenant-scoped endpoint returns data
curl -i -H "X-Tenant-Id: 11111111-1111-1111-1111-111111111111" \
     https://api.gecko.your-domain.tld/api/v1/assets
# expect: 200 with {"data":[...]} — assets array length should match
# the 8–12 asset target for producer-1

# 4. A missing tenant header errors cleanly
curl -i https://api.gecko.your-domain.tld/api/v1/assets
# expect: 400 with {"error":{"code":"MISSING_TENANT_HEADER",...}}

# 5. The frontend loads
curl -I https://krytsia.your-domain.tld/
# expect: 200
```

If any step fails, see §7 below.

---

## 6. Environment variables — full reference

### Backend (`/opt/gecko-vpp/.env`, read by `gecko-api`)

| Variable | Default in `.env.example` | What it does |
|---|---|---|
| `POSTGRES_DB` | `gecko_vpp` | Postgres database name |
| `POSTGRES_USER` | `gecko` | Postgres superuser (used only by container init) |
| `POSTGRES_PASSWORD` | — (required) | Postgres password |
| `POSTGRES_HOST` | `postgres` | Internal Docker hostname |
| `POSTGRES_PORT` | `5432` | Postgres port inside the container |
| `DATABASE_URL` | computed from the four above | Async SQLAlchemy URL used by the API |
| `API_HOST` | `0.0.0.0` | uvicorn bind address |
| `API_PORT` | `8000` | uvicorn bind port |
| `API_WORKERS` | `2` | uvicorn worker count |
| `APP_ENV` | `development` | `development` or `production` — gates debug surfaces |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `CORS_ORIGINS` | `https://gecko.radai-1984.dev,http://localhost:3000` | Comma-separated CORS allowlist appended to the built-in list |
| `TENANT_PRODUCER_UUID` | `11111111-...` | Fixed tenant UUID for `producer-1` |
| `TENANT_CI_UUID` | `22222222-...` | Fixed tenant UUID for `ci-1` |
| `TENANT_STORAGE_UUID` | `33333333-...` | Fixed tenant UUID for `storage-1` |
| `VOICE_PROVIDER` | `stub` | `stub` or `openai-realtime` |
| `OPENAI_API_KEY` | empty | Required only if `VOICE_PROVIDER=openai-realtime` |
| `SYNTH_DATE_START` | `2026-04-23` | Read by `data_generator` |
| `SYNTH_DATE_END` | `2026-05-23` | Read by `data_generator` |
| `SYNTH_RNG_SEED` | `42` | Determinism contract — same seed → same dataset |
| `NEXT_PUBLIC_API_BASE` | computed | Defined here for parity but only used by the frontend |

### Frontend (Vercel project env vars)

| Variable | What it does |
|---|---|
| `NEXT_PUBLIC_API_BASE` | URL of the FastAPI deployment, e.g. `https://api.gecko.your-domain.tld` |
| `NEXT_PUBLIC_GA_ID` | Optional Google Analytics 4 measurement ID (`G-XXXXXXXXXX`). When unset, GA is not loaded. |

---

## 7. Known issues and gotchas

These have all bitten the project at least once — they live here so the
next deployer skips the trap.

### 7.1 `caddy_web` network not attached → 502 from Caddy

**Symptom:** `docker compose up -d` succeeds, the API answers on the
host's port 8000 (in dev), but the public URL returns
`502 Bad Gateway`. Caddy logs show
`dial tcp: lookup gecko-api on 127.0.0.11:53: server misbehaving`.

**Cause:** the `docker-compose.prod.yml` overlay was not applied — see
§2.4.

**Fix:**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

If the network is genuinely missing:

```bash
docker network create caddy_web
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Sometimes `docker compose down` followed by `up` drops the API from
`caddy_web` even when the overlay was used. Always use both files for
both `up` and `down`.

### 7.2 `@vercel/analytics` breaks Next 16 build on Vercel

**Symptom:** local `next build --webpack` succeeds; Vercel deploy fails
with `Cannot read properties of undefined (reading 'modifyConfig')` or
similar.

**Cause:** `@vercel/analytics@2.x` injects a `modifyConfig` hook that
the Next 16 Vercel runtime no longer accepts.

**Fix:** **do not install `@vercel/analytics`**. The repo uses
`@next/third-parties` for Google Analytics instead. See the comment in
`apps/web/next.config.ts` and the memory
`project_vercel_analytics_next16_bug.md`.

### 7.3 Turbopack incompatibilities

**Symptom:** running `next dev` (default Turbopack) crashes with
`Cannot resolve module` on `@scalar/api-reference-react` or `cmdk`.

**Cause:** these packages publish import paths the Turbopack resolver
does not handle in Next 16.x.

**Fix:** the `dev` and `build` scripts in `apps/web/package.json`
already pin `--webpack`. Do not remove the flag.

### 7.4 RLS rejects everything because `app.tenant_id` was not set

**Symptom:** every endpoint returns empty arrays even though `\dt+` in
psql shows rows.

**Cause:** the FastAPI dependency that issues `SET LOCAL app.tenant_id
= ...` did not fire — usually because the route forgot to depend on
`get_db_session_with_tenant` or because `X-Tenant-Id` was missing from
the request.

**Fix:** check the request includes `X-Tenant-Id: <uuid>` and that the
route's signature uses the tenant-scoped session dependency.

### 7.5 Postgres bound to `127.0.0.1` only

Postgres is published on `127.0.0.1:5433` in the base compose file (no
host port at all in production). If you need to reach the DB from your
laptop, tunnel via SSH:

```bash
ssh -L 5433:127.0.0.1:5433 root@your-vps
# then connect to localhost:5433 from psql/DBeaver
```

This is intentional — the DB should never be reachable from the public
internet.

### 7.6 Forgetting to seed → empty dashboards

`alembic upgrade head` creates the schema but inserts only a few lookup
rows (EIC codes, regulator-event seeds). Without
`python -m data_generator.main --reset` the dashboards show empty
states. Run the coverage check (`python -m data_generator.coverage`)
after every seed — it will fail loudly if any §11 criterion has no
matching data.

---

## 8. Updating an existing deployment

```bash
cd /opt/gecko-vpp
git pull origin master
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec api alembic upgrade head    # if new migrations
```

If a release adds new tables or columns and you want the seeded dataset
to reflect them, re-run the generator:

```bash
cd /opt/gecko-vpp/data-generator
source .venv/bin/activate
python -m data_generator.main --reset
python -m data_generator.coverage
```

Frontend updates auto-deploy from `git push origin master`.
