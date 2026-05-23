"""Per-intent handler modules.

Each submodule exports `fetch_slots(session, *, tenant_id, now) -> dict` and
`render(slots, persona) -> str`.

The intent registry (`intents/__init__.py`) imports these from here.
"""

from gecko_vpp.agents_engine.intents.handlers import (
    arbitrage_window,
    battery_cycle_check,
    battery_schedule,
    bid_recommendation,
    dispatch_advice_now,
    forecast_accuracy,
    imbalance_explain,
    market_summary_today,
    next_maintenance,
    production_today,
    production_trend_7d,
    rdn_cap_alert,
    regulator_recent,
    revenue_breakdown,
    savings_summary,
    scenario_blackout,
    scenario_imbalance,
    self_consumption_today,
    soc_status_now,
    tariff_impact,
)

__all__ = [
    "arbitrage_window",
    "battery_cycle_check",
    "battery_schedule",
    "bid_recommendation",
    "dispatch_advice_now",
    "forecast_accuracy",
    "imbalance_explain",
    "market_summary_today",
    "next_maintenance",
    "production_today",
    "production_trend_7d",
    "rdn_cap_alert",
    "regulator_recent",
    "revenue_breakdown",
    "savings_summary",
    "scenario_blackout",
    "scenario_imbalance",
    "self_consumption_today",
    "soc_status_now",
    "tariff_impact",
]
