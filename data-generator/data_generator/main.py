"""Generator entrypoint.

CLI:
  python -m data_generator.main                # idempotent insert
  python -m data_generator.main --reset        # truncate + reseed
  python -m data_generator.main --start-date 2026-04-23 --end-date 2026-05-23
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import date

from sqlalchemy import text

from data_generator import config
from data_generator.db import connect, dispose
from data_generator.rng import reset_cache
from data_generator.shapes import (
    agent_query_log,
    ancillary,
    assets,
    bids,
    br_settlements,
    dd_contracts,
    forecast_submissions,
    forecasts,
    instructions,
    kpi_daily,
    optimisations,
    rdn_prices,
    regulator_events,
    settlements,
    setpoints,
    signed_documents,
    telemetry,
    users,
)


# Order matters because of FK dependencies.
PIPELINE: list[tuple[str, callable]] = [
    ("assets",                assets.generate),
    ("users",                 users.generate),
    ("rdn_prices",            rdn_prices.generate),
    ("vdr_trades",            __import__(
        "data_generator.shapes.vdr_trades", fromlist=["generate"]
    ).generate),
    ("br_settlements",        br_settlements.generate),
    ("dd_contracts+lines",    dd_contracts.generate),
    ("bids",                  bids.generate),
    ("ancillary",             ancillary.generate),
    ("telemetry",             telemetry.generate),
    ("setpoints",             setpoints.generate),
    ("instructions+acks",     instructions.generate),
    ("forecasts+actuals",     forecasts.generate),
    ("kpi_daily",             kpi_daily.generate),
    ("optimisations",         optimisations.generate),
    ("forecast_submissions",  forecast_submissions.generate),
    ("settlements+lines",     settlements.generate),
    ("signed_documents",      signed_documents.generate),
    ("regulator_events",      regulator_events.generate),
    ("agent_query_log",       agent_query_log.generate),
]


# Tables to TRUNCATE on --reset (in FK-safe order).
# core.tenants + core.eic_codes are pre-seeded by migration 012 — DO NOT touch.
TRUNCATE_ORDER = [
    "audit.events",
    "agents.response_cache",
    "agents.query_log",
    "regulatory.signed_documents",
    "regulatory.settlement_statement_lines",
    "regulatory.settlement_statements",
    "regulatory.forecast_submissions",
    "regulatory.regulator_events",
    "ems.optimisation_runs",
    "ems.kpi_daily",
    "ems.forecast_actuals",
    "ems.forecasts",
    "dispatch.instruction_acks",
    "dispatch.instructions",
    "dispatch.operator_adjustments",
    "dispatch.setpoints",
    "dispatch.telemetry",
    "market.ancillary_activations",
    "market.ancillary_offers",
    "market.bids",
    "market.dd_contract_hourly_volume",
    "market.dd_contracts",
    "market.br_settlements",
    "market.vdr_trades",
    "market.rdn_prices",
    "core.assets",
    "core.users",
]


async def reset_db() -> None:
    """TRUNCATE every domain table (preserves tenants + eic_codes)."""
    async with connect() as conn:
        for tbl in TRUNCATE_ORDER:
            await conn.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))


async def refresh_kpi_portfolio_mv() -> None:
    async with connect() as conn:
        await conn.execute(text("REFRESH MATERIALIZED VIEW ems.kpi_portfolio_30d"))


async def run_pipeline() -> dict[str, int]:
    """Run every shape generator in order. Returns row counts per stage."""
    counts: dict[str, int] = {}
    for label, fn in PIPELINE:
        t0 = time.perf_counter()
        async with connect() as conn:
            n = await fn(conn)
        elapsed = time.perf_counter() - t0
        counts[label] = n or 0
        print(f"  [{elapsed:6.2f}s] {label:28s} -> {n or 0} rows")
    return counts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="data_generator")
    parser.add_argument(
        "--reset", action="store_true",
        help="TRUNCATE all domain tables before generating",
    )
    parser.add_argument(
        "--start-date", type=str, default=None,
        help="Override SYNTH_DATE_START (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date", type=str, default=None,
        help="Override SYNTH_DATE_END (YYYY-MM-DD)",
    )
    return parser.parse_args()


async def main_async() -> int:
    args = _parse_args()
    if args.start_date:
        config.SYNTH_DATE_START = date.fromisoformat(args.start_date)  # type: ignore[misc]
    if args.end_date:
        config.SYNTH_DATE_END = date.fromisoformat(args.end_date)  # type: ignore[misc]

    print("=" * 60)
    print("GECKO VPP — Synthetic Data Generator")
    print(f"  Window: {config.SYNTH_DATE_START} .. {config.SYNTH_DATE_END}")
    print(f"  RNG seed: {config.SYNTH_RNG_SEED}")
    print(f"  Tenants: {len(config.TENANTS)}")
    print("=" * 60)

    if args.reset:
        print("--reset: truncating domain tables…")
        await reset_db()
        reset_cache()  # ensure RNG cache is fresh too

    counts = await run_pipeline()

    print("Refreshing ems.kpi_portfolio_30d materialised view…")
    await refresh_kpi_portfolio_mv()

    total = sum(counts.values())
    print("-" * 60)
    print(f"TOTAL ROWS INSERTED: {total}")
    print("-" * 60)
    await dispose()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
