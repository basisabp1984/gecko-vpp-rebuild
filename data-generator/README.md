# GECKO VPP — Synthetic Data Generator (Stage 4c)

Generates 30 days of realistic Ukrainian-energy synthetic data (РДН, ВДР,
БР, ДД, telemetry, forecasts, KPI, regulatory) for the 3 demo tenants.

## Setup

```powershell
cd data-generator
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Run

```powershell
# Idempotent insert (skips rows that already exist)
python -m data_generator.main

# Truncate + reseed (deterministic given SYNTH_RNG_SEED in .env)
python -m data_generator.main --reset

# Custom window
python -m data_generator.main --start-date 2026-04-23 --end-date 2026-05-23
```

## Verify coverage

```powershell
python -m data_generator.coverage
```

Exits 0 if every §11 acceptance criterion has matching data, 1 otherwise.

## Layout

- `data_generator/config.py` — reads `.env`, exposes tenant specs + window
- `data_generator/rng.py` — seeded numpy RNG factory (cached per-tag)
- `data_generator/db.py` — async engine + transactional connection
- `data_generator/main.py` — pipeline orchestrator with `--reset` flag
- `data_generator/coverage.py` — §11 coverage validator
- `data_generator/shapes/` — per-table generators (one module each)

## Conventions

- Determinism contract (ARCHITECTURE.md §3.11.4): same `SYNTH_RNG_SEED`
  produces the same data. Every `np.random.*` call goes through `rng.py`.
- Window: 2026-04-23 .. 2026-05-23 inclusive (31 days × 24 hours).
- Europe/Kyiv = +03:00 throughout (no DST transition inside the window).
- `dispatch.telemetry.interval_start` is **computed in Python** (not
  GENERATED — partition-key constraint, see `difficulties_log.md`).

## Coverage criteria (currently asserted)

See `coverage.py` for the full list. Highlights:

- §11.4   30 days × 24h РДН per tenant
- §11.11  ≥ 25 EIC codes across Y/X/W/V types
- §11.12  Asset capacities 1–20 МВт
- §11.19  ≥ 1 ACK forecast submission per tenant
- §11.20  ≥ 12 КЕП-signed documents with `is_demo_stub=TRUE`
- §11.21  Single-pane: РДН + ВДР + БР + ДД all present
- §11.22  CO₂ avoided KPI > 0 for RES assets
- §11.25  ≥ 5 cap-pinned РДН hours (production-fidelity sniff)
- §11.27  ≥ 1 curtailment event + ≥ 1 imbalance spike
