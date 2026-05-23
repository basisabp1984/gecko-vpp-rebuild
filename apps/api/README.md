# gecko-vpp-api

FastAPI backend for GECKO VPP v2 — DB layer (Stage 4b) and REST API (Stage 4d).

See `phase-3-architecture/BACKEND_DB_INSTRUCTIONS.md` (DB layer) and
`phase-3-architecture/BACKEND_API_INSTRUCTIONS.md` (API layer) for the full playbooks.

## Local install (Windows / PowerShell)

```powershell
cd apps\api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Local install (bash / WSL / macOS)

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run migrations against the local Postgres

The project root `.env` file holds `DATABASE_URL`. Migrations use the sync
psycopg driver (alembic + async is more pain than worth); the app itself uses
async + asyncpg.

```bash
# from apps/api/ with .venv active
alembic upgrade head
```

## Run the RLS smoke test

```bash
pytest tests/test_rls.py -v
```

## What is in here

```
apps/api/
├── pyproject.toml
├── alembic.ini
├── migrations/                 # alembic — 001..012
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/gecko_vpp/
│   ├── config.py               # pydantic-settings (reads .env)
│   ├── db.py                   # async engine + session
│   └── models/
│       ├── base.py             # DeclarativeBase + naming convention
│       ├── core.py             # core schema ORM
│       ├── market.py
│       ├── dispatch.py
│       ├── ems.py
│       ├── regulatory.py
│       ├── agents.py
│       └── audit.py
└── tests/
    └── test_rls.py             # RLS smoke test
```
