"""Hourly telemetry per asset.

Shape rules per asset class (research_asset_data_shape.md PART A):
- СЕС: cosine solar curve × cloud factor (AR(1)) × seasonal scale. Zero at
  night. April-May central UA target CF ~16–18%. Add `irradiance_w_m2` extra.
- ВЕС: persistent OU-like wind speed → P-curve power. Mean ~30% × capacity
  in spring. Hour-over-hour autocorrelation 0.9.
- ГПУ: dispatch when РДН > 4500 AND not deep night. Heat-rate 40%.
- УЗЕ: SoC cycle — charge 00:00–06:00, discharge 17:00–21:00, RTE 88%,
  DOD 10–90%. ``cumulative_cycles`` accumulated.
- Active consumer / consumer: industrial base 30% + ramp to 80% in 08:00–18:00.
  ``active_power_mw`` is NEGATIVE for consumption rows (per spine convention).
- Curtailment events: 2026-05-12 solar midday & 2026-05-04 wind overnight
  (one asset each). Status = 'curtailed_by_TSO', availability_pct < 50%.
- Planned maintenance: 'Кагарлицька ВЕС' offline 2026-05-08 to 2026-05-12 ←
  matches ARCHITECTURE.md §3.11.3 events #4 spec.

Telemetry primary key is (tenant_id, asset_id, interval_start).
``interval_start`` is computed in Python (not GENERATED — see
difficulties_log.md / dispatch.telemetry note in models/dispatch.py).
"""

from __future__ import annotations

from datetime import date as DateT, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    SYNTH_DATE_END,
    SYNTH_DATE_START,
    date_range_inclusive,
)
from data_generator.rng import get_rng
from data_generator.shapes.assets import ALL_ASSETS, AssetSpec


# Europe/Kyiv is +03:00 throughout our window (no DST per ARCHITECTURE.md §6).
KYIV_OFFSET = timezone(timedelta(hours=3))


# Events from ARCHITECTURE.md §3.11.3
SOLAR_CURTAILMENT_DAY = DateT(2026, 5, 12)
WIND_CURTAILMENT_DAY = DateT(2026, 5, 4)
MAINT_START = DateT(2026, 5, 8)
MAINT_END = DateT(2026, 5, 12)
MAINT_ASSET_CODE = "kaharlyk-ves-1"


# --- Solar curve (CF as fraction of nameplate, April/May central UA) ---
# Map hour-of-day → solar capacity factor on a clear day at this season.
_SOLAR_CLEAR_CF = {
    0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.05,
    6: 0.18, 7: 0.38, 8: 0.55, 9: 0.70, 10: 0.80, 11: 0.88,
    12: 0.92, 13: 0.90, 14: 0.82, 15: 0.68, 16: 0.50,
    17: 0.32, 18: 0.15, 19: 0.04, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0,
}


def _solar_power_for_hour(
    asset: AssetSpec, d: DateT, hour: int, rng: np.random.Generator,
    cloud_state: list[float],
) -> tuple[float, float, str, float]:
    """Return (active_power_mw, irradiance_w_m2, status, availability_pct)."""
    h_idx = hour - 1  # hour 1..24 → 0..23
    clear_cf = _SOLAR_CLEAR_CF.get(h_idx, 0.0)
    # AR(1) cloud factor in [0.15, 1.0]; persistent across hours
    cloud_prev = cloud_state[0]
    cloud = 0.85 * cloud_prev + 0.15 * float(rng.uniform(0.5, 1.0))
    cloud = float(np.clip(cloud + float(rng.normal(0.0, 0.06)), 0.15, 1.0))
    cloud_state[0] = cloud
    cf = clear_cf * cloud

    status = "online" if clear_cf > 0.01 else "idle"
    availability = 100.0

    # Solar curtailment event — midday on 2026-05-12 for first СЕС
    if (
        d == SOLAR_CURTAILMENT_DAY
        and 11 <= hour <= 15
        and asset.code == "polyana-ses-1"
    ):
        cf = cf * 0.25  # clamped to 25% of available
        status = "curtailed_by_TSO"
        availability = 35.0

    power_mw = cf * asset.capacity_mw
    # POA irradiance proxy ~ cf × 1000 W/m²
    irradiance = max(0.0, cf * 1000.0)
    return power_mw, irradiance, status, availability


def _wind_power_for_hour(
    asset: AssetSpec, d: DateT, hour: int, rng: np.random.Generator,
    wind_state: list[float],
) -> tuple[float, float, str, float]:
    """OU-like persistent wind. Return (mw, wind_speed_m_s, status, avail)."""
    # OU process with mean 30% CF, σ=0.18, persistence 0.9
    prev = wind_state[0]
    target = 0.30 + float(rng.normal(0.0, 0.18))
    cf = 0.9 * prev + 0.1 * target + float(rng.normal(0.0, 0.05))
    cf = float(np.clip(cf, 0.02, 0.95))
    wind_state[0] = cf
    wind_speed = 4.0 + cf * 18.0  # 4..22 m/s

    status = "online"
    availability = 100.0

    # Planned maintenance for Kaharlyk ВЕС
    if (
        asset.code == MAINT_ASSET_CODE
        and MAINT_START <= d <= MAINT_END
    ):
        cf = 0.0
        wind_speed = 0.0
        status = "maintenance"
        availability = 0.0

    # Wind curtailment overnight on 2026-05-04 for Odesa ВЕС
    if (
        asset.code == "odesa-ves-1"
        and d == WIND_CURTAILMENT_DAY
        and (hour <= 5 or hour >= 23)
    ):
        cf = cf * 0.20
        status = "curtailed_by_TSO"
        availability = 30.0

    power_mw = cf * asset.capacity_mw
    return power_mw, wind_speed, status, availability


def _gpu_power_for_hour(
    asset: AssetSpec, d: DateT, hour: int, rng: np.random.Generator,
    rdn_price: float,
) -> tuple[float, str, float]:
    """ГПУ dispatched when РДН > 4500 UAH/MWh AND it's not deep-night/weekend
    low. Outside that, off or idle.
    """
    # Dispatch threshold + min stable load 40%
    if rdn_price > 4500 and 7 <= hour <= 23:
        # Load factor scales with how high above threshold
        lf = float(np.clip(0.5 + (rdn_price - 4500) / 4000, 0.4, 1.0))
        # Small noise (±5%)
        lf = float(np.clip(lf + float(rng.normal(0.0, 0.04)), 0.4, 1.0))
        power_mw = lf * asset.capacity_mw
        status = "online"
        availability = 100.0
    else:
        power_mw = 0.0
        status = "idle"
        availability = 100.0
    return power_mw, status, availability


def _consumer_power_for_hour(
    asset: AssetSpec, d: DateT, hour: int, rng: np.random.Generator,
) -> tuple[float, str, float]:
    """Industrial load shape (negative power = consumption from grid)."""
    # Base 30% always-on (refrigeration / always-on processes)
    base = 0.30
    if 7 <= hour <= 20 and d.weekday() < 5:
        # Daytime ramp up to ~85% peak
        if hour < 9:
            day = 0.30 + 0.25 * (hour - 6) / 3
        elif hour > 18:
            day = 0.30 + 0.20 * (21 - hour) / 3
        else:
            day = 0.85
        cf = max(base, day)
    else:
        cf = base
    cf += float(rng.normal(0.0, 0.04))
    cf = float(np.clip(cf, 0.10, 0.95))
    # Active consumer (flex) is similar but smaller. Consumer is full.
    power_mw = -cf * asset.capacity_mw  # negative = consumption
    return power_mw, "online", 100.0


def _battery_step(
    asset: AssetSpec,
    hour: int,
    rdn_price: float,
    soc_pct: float,
    cumulative_cycles: float,
    rng: np.random.Generator,
) -> tuple[float, float, float, str]:
    """One hour of battery operation.

    Returns (active_power_mw, new_soc_pct, new_cumulative_cycles, status).
    Convention: positive active_power_mw = discharging to grid; negative =
    charging. SoC range 10–90%.
    """
    cap_mwh = float(asset.storage_capacity_mwh or asset.capacity_mw * 2.0)
    max_power = asset.capacity_mw
    rte = 0.88  # round-trip efficiency
    eff_one_way = rte ** 0.5  # ~0.938

    # Decision tree based on hour-of-day arbitrage windows
    if 1 <= hour <= 6 and soc_pct < 88:
        # Charge during cheap overnight
        target_charge = min(max_power, (88 - soc_pct) / 100 * cap_mwh)
        # Sign convention: charging = negative power
        power_mw = -target_charge
        # SoC increase: energy_into_battery × eff
        soc_increase = (target_charge * eff_one_way) / cap_mwh * 100
        new_soc = min(90.0, soc_pct + soc_increase)
        status = "online"
    elif 17 <= hour <= 21 and soc_pct > 12:
        # Discharge during evening peak
        target_dis = min(max_power, (soc_pct - 12) / 100 * cap_mwh)
        power_mw = target_dis
        soc_decrease = (target_dis / eff_one_way) / cap_mwh * 100
        new_soc = max(10.0, soc_pct - soc_decrease)
        status = "online"
    elif 11 <= hour <= 14 and rdn_price < 3200 and soc_pct < 70:
        # Optional midday charge from cheap solar surplus
        target_charge = min(max_power * 0.5, (75 - soc_pct) / 100 * cap_mwh)
        power_mw = -target_charge
        soc_increase = (target_charge * eff_one_way) / cap_mwh * 100
        new_soc = min(80.0, soc_pct + soc_increase)
        status = "online"
    else:
        power_mw = 0.0
        new_soc = soc_pct
        status = "idle"

    # Add small noise so curves aren't perfectly identical day-to-day
    power_mw += float(rng.normal(0.0, max_power * 0.02))
    new_soc = float(np.clip(new_soc, 10.0, 90.0))

    # Cycles bookkeeping: half-cycle per energy_exchanged
    energy_swing = abs(power_mw) / cap_mwh
    new_cycles = cumulative_cycles + 0.5 * energy_swing
    return power_mw, new_soc, new_cycles, status


async def _fetch_rdn_for_tenant(
    conn: AsyncConnection, tenant_id: UUID
) -> dict[tuple[DateT, int], float]:
    """Pre-fetch all РДН prices for one tenant → {(date, hour): price}."""
    res = await conn.execute(
        text(
            """
            SELECT date, hour, price_uah_mwh
            FROM market.rdn_prices
            WHERE tenant_id = CAST(:tid AS uuid)
            """
        ),
        {"tid": str(tenant_id)},
    )
    out: dict[tuple[DateT, int], float] = {}
    for row in res:
        out[(row.date, row.hour)] = float(row.price_uah_mwh)
    return out


async def generate(conn: AsyncConnection) -> int:
    """Insert dispatch.telemetry for every (asset, day, hour) in window."""
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    insert_stmt = text(
        """
        INSERT INTO dispatch.telemetry
            (tenant_id, asset_id, date, hour, interval_start,
             active_power_mw, reactive_power_mvar, soc_pct,
             availability_pct, status, data_quality, source, extras)
        VALUES
            (CAST(:tenant_id AS uuid), CAST(:asset_id AS uuid),
             :date, :hour, :interval_start,
             :active_power_mw, :reactive_power_mvar, :soc_pct,
             :availability_pct, :status, 'R', 'synthetic',
             CAST(:extras AS jsonb))
        ON CONFLICT (tenant_id, asset_id, interval_start) DO NOTHING
        """
    )

    # Pre-fetch РДН per tenant (used by ГПУ + УЗЕ dispatch).
    rdn_cache: dict[UUID, dict[tuple[DateT, int], float]] = {}
    for asset in ALL_ASSETS:
        if asset.tenant_id not in rdn_cache:
            rdn_cache[asset.tenant_id] = await _fetch_rdn_for_tenant(
                conn, asset.tenant_id
            )

    for asset in ALL_ASSETS:
        rng = get_rng(f"telemetry:{asset.tenant_id}:{asset.code}")
        rows: list[dict[str, Any]] = []
        # Stateful machinery
        cloud_state = [float(rng.uniform(0.5, 1.0))]
        wind_state = [0.30]
        soc_pct = 50.0
        cum_cycles = 0.0

        for d in dates:
            for hour in range(1, 25):
                # interval_start: Kyiv-local wall clock with +03:00 offset
                interval_start = datetime.combine(
                    d, time(hour - 1, 0), tzinfo=KYIV_OFFSET
                )
                rdn = rdn_cache[asset.tenant_id].get((d, hour), 3500.0)
                reactive_mvar = None
                soc_val: float | None = None
                extras: dict[str, Any] = {}

                if asset.asset_class == "СЕС":
                    p_mw, irr, status, avail = _solar_power_for_hour(
                        asset, d, hour, rng, cloud_state
                    )
                    extras["irradiance_w_m2"] = round(irr, 1)
                elif asset.asset_class == "ВЕС":
                    p_mw, wspeed, status, avail = _wind_power_for_hour(
                        asset, d, hour, rng, wind_state
                    )
                    extras["wind_speed_m_s"] = round(wspeed, 2)
                elif asset.asset_class == "ГПУ":
                    p_mw, status, avail = _gpu_power_for_hour(
                        asset, d, hour, rng, rdn
                    )
                    extras["fuel_flow_nm3_h"] = round(p_mw * 230, 1)  # ~230 nm3/MWh
                elif asset.asset_class == "УЗЕ":
                    p_mw, soc_pct, cum_cycles, status = _battery_step(
                        asset, hour, rdn, soc_pct, cum_cycles, rng
                    )
                    avail = 100.0
                    soc_val = soc_pct
                    extras["cumulative_cycles"] = round(cum_cycles, 3)
                else:  # Споживач / АктСпож
                    p_mw, status, avail = _consumer_power_for_hour(
                        asset, d, hour, rng
                    )
                    # Reactive power roughly 30% of active for industrial load
                    reactive_mvar = round(abs(p_mw) * 0.30, 3)

                rows.append(
                    {
                        "tenant_id": str(asset.tenant_id),
                        "asset_id": str(asset.asset_id),
                        "date": d,
                        "hour": hour,
                        "interval_start": interval_start,
                        "active_power_mw": Decimal(f"{p_mw:.3f}"),
                        "reactive_power_mvar": (
                            Decimal(f"{reactive_mvar:.3f}")
                            if reactive_mvar is not None
                            else None
                        ),
                        "soc_pct": (
                            Decimal(f"{soc_val:.2f}") if soc_val is not None else None
                        ),
                        "availability_pct": Decimal(f"{avail:.2f}"),
                        "status": status,
                        "extras": _json_dumps(extras),
                    }
                )

        # Batch insert per asset (~744 rows). Comfortable for asyncpg.
        result = await conn.execute(insert_stmt, rows)
        total += (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
    return total


def _json_dumps(d: dict[str, Any]) -> str:
    """Minimal JSON serialisation (avoid pulling json module at top)."""
    import json

    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))
