"""РДН (day-ahead market) hourly prices.

Shape rules (research_market_data_shape.md §1):
- Double-peak daily curve:
  * Trough 03:00–05:00 ~1,500–2,500 UAH/MWh
  * Morning peak 08:00–10:00 ~4,500–5,500
  * Midday dip 12:00–14:00 ~2,500–3,500 (PV pushes prices down in spring)
  * Evening peak 17:00–21:00 ~5,500–7,500 (war-era structurally pinned)
- Cap-pinning at evening peak (17–21h): per-hour probability 40%, clamped
  to RDN_CAP_PEAK (6900 UAH/MWh).
- Negative price day around 2026-05-04: midday prices ≤ 0 UAH/MWh (2-3h).
- Weekday/weekend modifier: weekend −10–15% on baseload.
- Random noise: AR(1)-ish persistence ±15%.

Per tenant — same shape (single market), but each tenant gets its own copy
since RLS isolates by tenant_id. Daily index labels populated.
"""

from __future__ import annotations

from datetime import date as DateT
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    BZN_EIC_UA_IPS,
    CAP_PINNING_HOURS,
    CAP_PINNING_PROBABILITY,
    RDN_CAP_DEFAULT,
    RDN_CAP_OFFPEAK,
    RDN_CAP_PEAK,
    SYNTH_DATE_END,
    SYNTH_DATE_START,
    TENANTS,
    date_range_inclusive,
)
from data_generator.rng import get_rng


# Hourly base curve (UAH/MWh) — central spring weekday shape.
# Index 0 → hour=1 (00:00), index 23 → hour=24 (23:00).
_BASE_CURVE: tuple[float, ...] = (
    2200,  # 1  (00–01)
    2000,
    1800,
    1700,  # 4  (03–04)  ← trough
    1700,
    1900,
    2400,
    3200,  # 8  (07–08)  ← morning ramp
    4400,
    4900,  # 10 (09–10)  ← morning peak
    4300,
    3500,
    3000,  # 13 (12–13)  ← midday dip (PV)
    3100,
    3500,
    4200,
    4900,
    5700,  # 18 (17–18)
    6300,
    6600,  # 20 (19–20)  ← evening peak
    6400,
    5400,  # 22 (21–22)
    3900,
    2800,  # 24 (23–00)
)


NEGATIVE_DAY = DateT(2026, 5, 4)
WIND_CURTAILMENT_DAY = DateT(2026, 5, 4)   # overnight low-load high-wind
SOLAR_CURTAILMENT_DAY = DateT(2026, 5, 12)  # midday surplus


def _daily_factor(d: DateT, rng: np.random.Generator) -> float:
    """Day-level multiplier from random walk around 1.0."""
    # Weekend reduction
    if d.weekday() >= 5:
        weekend_mult = 0.88
    else:
        weekend_mult = 1.0
    # Persistent daily noise (±10%)
    noise = float(rng.normal(0.0, 0.05))
    return weekend_mult * (1.0 + np.clip(noise, -0.10, 0.10))


def build_day_hours(
    d: DateT, rng_day: np.random.Generator
) -> list[dict[str, Any]]:
    """Compute one day × 24 hours of РДН prices for one tenant."""
    day_mult = _daily_factor(d, rng_day)
    rows: list[dict[str, Any]] = []
    # Persistent AR(1) noise across hours within the day
    eps_prev = 0.0
    for hour in range(1, 25):
        base = _BASE_CURVE[hour - 1] * day_mult
        # AR(1) noise: ε_t = 0.6 ε_{t-1} + N(0, σ)
        eps = 0.6 * eps_prev + float(rng_day.normal(0.0, 0.08))
        eps = float(np.clip(eps, -0.18, 0.18))
        eps_prev = eps
        price = base * (1.0 + eps)

        # Cap-pinning: evening peak hours hit RDN_CAP_PEAK with set probability
        is_capped = False
        cap_val: float | None = None
        if hour in CAP_PINNING_HOURS:
            if float(rng_day.random()) < CAP_PINNING_PROBABILITY:
                price = float(RDN_CAP_PEAK)
                is_capped = True
                cap_val = float(RDN_CAP_PEAK)

        # Negative price day: midday hours go to ~0
        if d == NEGATIVE_DAY and 12 <= hour <= 14:
            price = float(rng_day.uniform(-150.0, 50.0))
            is_capped = False
            cap_val = None

        # Hard floor at -300 (very rare on UA market but allow tiny excursions)
        price = max(price, -300.0)
        # Hard cap (apply default cap if not pinned)
        if not is_capped:
            cap_for_hour = (
                RDN_CAP_PEAK
                if hour in CAP_PINNING_HOURS
                else (RDN_CAP_OFFPEAK if hour in (1, 2, 3, 4, 5, 23, 24) else RDN_CAP_DEFAULT)
            )
            if price > cap_for_hour:
                price = float(cap_for_hour)
                is_capped = True
                cap_val = float(cap_for_hour)

        # Cleared volume: roughly tracks demand shape. UA cleared МВт is ~3-9 GW.
        # We synthesise a tenant-share scaled volume — small per tenant.
        base_vol_mwh = 800 + 450 * (_BASE_CURVE[hour - 1] / max(_BASE_CURVE)) ** 1.2
        volume_mwh = float(base_vol_mwh * (1.0 + 0.05 * float(rng_day.normal())))

        rows.append(
            {
                "date": d,
                "hour": hour,
                "price_uah_mwh": Decimal(f"{price:.2f}"),
                "volume_mwh": Decimal(f"{volume_mwh:.3f}"),
                "is_capped": is_capped,
                "cap_uah_mwh": (
                    Decimal(f"{cap_val:.2f}") if cap_val is not None else None
                ),
            }
        )

    # Daily index labels (mean of base / peak / offpeak hours).
    prices = np.array([float(r["price_uah_mwh"]) for r in rows])
    daily_base = float(prices.mean())
    daily_peak = float(prices[16:21].mean())   # hours 17–21
    daily_off = float(np.concatenate([prices[:6], prices[22:]]).mean())
    for r in rows:
        r["daily_index_base"] = Decimal(f"{daily_base:.2f}")
        r["daily_index_peak"] = Decimal(f"{daily_peak:.2f}")
        r["daily_index_offpeak"] = Decimal(f"{daily_off:.2f}")
    return rows


async def generate(conn: AsyncConnection) -> int:
    """Insert market.rdn_prices for all tenants × all days × 24h."""
    dates = date_range_inclusive(SYNTH_DATE_START, SYNTH_DATE_END)
    total = 0
    stmt = text(
        """
        INSERT INTO market.rdn_prices
            (tenant_id, bidding_zone_eic, date, hour, price_uah_mwh,
             volume_mwh, is_capped, cap_uah_mwh,
             daily_index_base, daily_index_peak, daily_index_offpeak)
        VALUES
            (CAST(:tenant_id AS uuid), :bzn_eic, :date, :hour,
             :price_uah_mwh, :volume_mwh, :is_capped, :cap_uah_mwh,
             :daily_index_base, :daily_index_peak, :daily_index_offpeak)
        ON CONFLICT (tenant_id, bidding_zone_eic, date, hour) DO NOTHING
        """
    )
    for tenant in TENANTS:
        batch: list[dict[str, Any]] = []
        for d in dates:
            # Per-tenant per-day RNG — keeps determinism even if we
            # reorder generators in a future refactor.
            rng = get_rng(f"rdn_prices:{tenant.code}:{d.isoformat()}")
            day_rows = build_day_hours(d, rng)
            for r in day_rows:
                r["tenant_id"] = str(tenant.uuid)
                r["bzn_eic"] = BZN_EIC_UA_IPS
                batch.append(r)
        result = await conn.execute(stmt, batch)
        total += result.rowcount if result.rowcount is not None else len(batch)
    return total
