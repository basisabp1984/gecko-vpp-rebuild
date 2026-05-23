# CONTRIBUTING — onboarding to Krytsia

This is a demo repository, not a maintained product, so there are no
maintainer-only rules and no CLA. The goal of this file is to get a
new contributor from `git clone` to a passing local build in under
30 minutes.

---

## 1. Local setup

### 1.1 Clone the repo

```bash
git clone https://github.com/<your-fork-or-upstream>/gecko-vpp-rebuild
cd gecko-vpp-rebuild
cp .env.example .env       # then edit POSTGRES_PASSWORD at minimum
```

### 1.2 Database (Docker)

The fastest path to a working Postgres is the same compose file the
production deploy uses:

```bash
docker compose up -d postgres
docker compose exec postgres psql -U gecko -d gecko_vpp -c "SELECT 1;"
```

The container binds Postgres to `127.0.0.1:5433` on the host — handy
for DBeaver / psql / running tests against it without going through
`docker compose exec`. The DATABASE_URL in `.env.example` points at
`postgres:5432` (the in-network hostname); when running the API or
generator from the host instead of a container, point at
`localhost:5433`:

```bash
# tests + local python from the host:
export DATABASE_URL='postgresql+asyncpg://gecko:<password>@127.0.0.1:5433/gecko_vpp'
```

### 1.3 Backend

```bash
cd apps/api
python -m venv .venv

# PowerShell (Windows):
.venv\Scripts\Activate.ps1

# bash (WSL / macOS / Linux):
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head
uvicorn gecko_vpp.main:app --reload --host 127.0.0.1 --port 8000
```

The API is then at `http://127.0.0.1:8000`. Swagger docs:
`http://127.0.0.1:8000/docs`. OpenAPI JSON: `/openapi.json`.

### 1.4 Synthetic data

Without seeded data every dashboard is empty. Seed once from the host:

```bash
cd data-generator
python -m venv .venv
.venv\Scripts\activate          # PowerShell
# or: source .venv/bin/activate

pip install -e .
python -m data_generator.main --reset
python -m data_generator.coverage      # exits 0 if every §11 criterion has rows
```

`--reset` truncates every domain table and reseeds deterministically
from `SYNTH_RNG_SEED`. Without `--reset` the generator is idempotent
(skips rows that already exist).

### 1.5 Frontend

```bash
cd apps/web
npm install
npm run dev      # this runs `next dev --webpack` — do NOT change to turbopack
```

Open `http://localhost:3000` in a Chromium-based browser. Brave with
strict shields and Firefox with strict tracking protection may block
the GA4 script, which is harmless for local dev but produces console
noise.

The `dev` script pins `--webpack` because `@scalar/api-reference-react`
and `cmdk` ship import paths the Turbopack resolver does not handle
yet. Same for `npm run build`.

---

## 2. Running tests

### 2.1 Backend

```bash
cd apps/api
pytest -v
```

The current test suite is the RLS smoke test in `tests/test_rls.py` —
it asserts that `gecko_api` cannot read another tenant's rows when
`app.tenant_id` is unset or wrong. It needs the Postgres container
running on `127.0.0.1:5433` (see §1.2) and `DATABASE_URL` exported in
the shell.

### 2.2 Frontend

There is no Playwright suite committed in the current cut; type-checking
is the canonical fast feedback loop:

```bash
cd apps/web
npm run typecheck     # tsc --noEmit
npm run lint          # eslint
```

`npm run build` is the production-equivalent smoke — it exercises every
route through `next build --webpack`.

---

## 3. Code style

| Language | Tools | Run from |
|---|---|---|
| Python | `ruff` (lint + format), `mypy` (type-check) | `apps/api/` |
| TypeScript | `tsc --noEmit`, `eslint` (Next defaults) | `apps/web/` |
| SQL | hand-formatted; lower-case keywords; one column per line in DDL — see `apps/api/migrations/versions/` for the house style | n/a |
| Markdown | GitHub-flavored. Headings sentence-case. No trailing whitespace. | n/a |

Suggested before pushing:

```bash
# backend
cd apps/api
ruff check src tests
ruff format --check src tests
mypy src

# frontend
cd apps/web
npm run typecheck
npm run lint
```

---

## 4. Branching

- **`master`** is production. Vercel auto-deploys from `master`.
- Feature branches: `feat/<short-description>` or `fix/<short-description>`.
- PRs are welcome. There is no required reviewer — this is a demo
  repo — but please run the smoke tests in §2 before pushing.
- **Never** `git push --force` to `master`. If a bad commit lands, add
  a `revert` commit on top.

---

## 5. Commit messages

The repo uses **Conventional Commits in Ukrainian** — the existing
history is the source of truth. Inspect with `git log --oneline`:

```
feat(web): підключити Google Analytics 4 через @next/third-parties
feat(web): i18n EN/PL/UK/RU + locale switcher + сховати Developer
feat(web): Phase A — кінематографічний hero + AI-перше позиціонування
feat(web): підняти видимість AI агентів — FAB + showcase на головній
fix(api): додати krytsia.radai-1984.dev у CORS allowlist
feat: rebrand from GECKO VPP to Krytsia
```

Format:

```
<type>(<scope>): <короткий опис, до 70 символів, без крапки в кінці>

<optional body explaining WHY — 2-5 lines, blank line above>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`,
`style`. Scopes: `web`, `api`, `data-generator`, `sdk-ts`, `sdk-py`,
`infra`, or any module-level scope you find useful. Scope is optional
for repo-wide changes.

The `Co-Authored-By` trailer reflects honest attribution — the project
was built with significant Claude assistance and every commit carries
that line. Keep it on commits you author too.

---

## 6. Architecture orientation

For a 10-minute overview see [`ARCHITECTURE.md`](ARCHITECTURE.md). For
the deep dive see
[`phase-3-architecture/ARCHITECTURE.md`](phase-3-architecture/ARCHITECTURE.md)
(~38 pages — has every table DDL, every endpoint contract, FMEA, design
tokens).

For "what was built and why," read [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md)
(v0.4 frozen). For the most recent direction (cinematic hero, AI-first
positioning, 4 locales, GA4) read
[`BRIEF_V05_AMENDMENT.md`](BRIEF_V05_AMENDMENT.md).

Module READMEs to skim before changing code in that area:

- [`apps/api/README.md`](apps/api/README.md) — backend layout, RLS
  smoke test
- [`apps/web/README.md`](apps/web/README.md) — frontend dev loop
- [`data-generator/README.md`](data-generator/README.md) — what gets
  seeded and how
- [`packages/sdk-ts/README.md`](packages/sdk-ts/README.md),
  [`packages/sdk-py/README.md`](packages/sdk-py/README.md) — SDK
  conventions

---

## 7. AI-assisted development

This repository was built with significant assistance from Claude (and
some GPT). Every commit message includes
`Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
as honest attribution. When you commit, keep that trailer on your own
commits if AI helped — it is not a credit grab, it is a record of how
the artifact came to be.

The development process follows a private methodology repository
("the bible") that lives at
`D:\ВС коде вайбкодинг\Инструкции-PORT\` on the original author's
machine — a separate git repo not published here. It encodes the
six-phase task lifecycle (Understanding → Solution → Architecture →
Implementation → Verification → Operation) that
[`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md),
[`BRIEF_V05_AMENDMENT.md`](BRIEF_V05_AMENDMENT.md), and the
`phase-{1,2,3}-*/` directories are artefacts of. You do not need it to
contribute — but if you see references to "Phase 4 implementation" or
"§11 acceptance criteria," that is where they come from.
