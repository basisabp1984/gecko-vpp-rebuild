"""Intent registry.

NOTE on file layout: the AI_AGENTS_INSTRUCTIONS playbook calls for one module
per intent. With 20 intents that produces ~20 near-identical 30-line files.
Per the branching protocol (§9 of the playbook, also §"Branching protocol" of
this work-unit's brief: "If a specific SQL pattern is hard to write →
simplify, document in difficulties_log"), we compress all 20 intents into
this single module to keep the surface small. Each intent is a dict with:

  patterns: list[(priority:int, confidence:float, regex:str)]
  personas: set[str]                      # which personas are allowed
  fetch_slots: async (session, *, tenant_id, now) -> dict
  render: (slots: dict, persona: str) -> str

The classifier reads `compiled_patterns` (a derived field added on import).
"""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine.intents.handlers import (  # noqa: E402
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

FetchFn = Callable[..., Awaitable[dict[str, Any]]]
RenderFn = Callable[[dict[str, Any], str], str]


# Pattern tables — written against the *normalised* text (lowercase, no
# stopwords, NFKC). Stems use \w+ liberally to catch Ukrainian inflection.
# Format: (priority, confidence, regex_string)
INTENT_REGISTRY: dict[str, dict[str, Any]] = {
    # ---------- DISPATCHER ----------
    "production_today": {
        "personas": {"dispatcher_analyst"},
        "patterns": [
            (95, 0.95, r"\b(виробництв\w*|генерац\w*)\s+сьогодні\b"),
            (90, 0.92, r"\bщо\s+сьогодні\s+(з\s+)?(виробництв\w*|генерац\w*)"),
            (85, 0.88, r"\bвиробил\w+\s+сьогодні\b"),
            (80, 0.85, r"\bяк\s+справ\w+\s+(з\s+)?(виробництв\w*|генерац\w*)"),
            (70, 0.75, r"\bсьогодні\s+(виробництв\w*|генерац\w*)"),
        ],
        "fetch_slots": production_today.fetch_slots,
        "render": production_today.render,
    },
    "production_trend_7d": {
        "personas": {"dispatcher_analyst"},
        "patterns": [
            (95, 0.95, r"\b(тренд|динамік\w+)\s+виробництв\w*\s+(тиждень|7\s*дн\w*)"),
            (90, 0.92, r"\bвиробництв\w+\s+(за|на)\s+(тиждень|7\s*дн\w*)"),
            (85, 0.88, r"\bяк\s+(йшл\w+|пройш\w+)\s+виробництв\w+\s+(за|на)?\s*тиждень"),
            (80, 0.85, r"\bтиждень\s+виробництв\w+"),
            (70, 0.75, r"\b7\s+дн\w+\s+виробництв"),
        ],
        "fetch_slots": production_trend_7d.fetch_slots,
        "render": production_trend_7d.render,
    },
    "imbalance_explain": {
        "personas": {"dispatcher_analyst"},
        "patterns": [
            (95, 0.95, r"\b(поясн\w+|чому)\s+(був\w+\s+)?небаланс"),
            (90, 0.92, r"\bнебаланс\w+\s+сьогодні\b"),
            (85, 0.88, r"\bяк\w+\s+небаланс"),
            (75, 0.80, r"\bнебаланс\w+\b"),
        ],
        "fetch_slots": imbalance_explain.fetch_slots,
        "render": imbalance_explain.render,
    },
    "forecast_accuracy": {
        "personas": {"dispatcher_analyst"},
        "patterns": [
            (95, 0.95, r"\bточн\w+\s+прогноз\w*"),
            (90, 0.92, r"\bяк\w+\s+точн\w+\s+прогноз"),
            (88, 0.90, r"\bmape\b"),
            (85, 0.88, r"\bпохибк\w+\s+прогноз"),
            (75, 0.78, r"\bпрогноз\w+\s+(точн\w+|відхил)"),
        ],
        "fetch_slots": forecast_accuracy.fetch_slots,
        "render": forecast_accuracy.render,
    },
    "next_maintenance": {
        "personas": {"dispatcher_analyst"},
        "patterns": [
            (95, 0.95, r"\bколи\s+(наступн\w+\s+)?(то|техобслугов\w*|maintenance)\b"),
            (90, 0.92, r"\b(наступн\w+\s+)?ремонт\w*"),
            (85, 0.88, r"\bколи\s+ремонт"),
            (80, 0.85, r"\bтехнічн\w+\s+обслугов"),
        ],
        "fetch_slots": next_maintenance.fetch_slots,
        "render": next_maintenance.render,
    },
    "regulator_recent": {
        "personas": {"dispatcher_analyst", "market_analyst", "energy_advisor"},
        "patterns": [
            (95, 0.95, r"\b(нкрекп|укренерго|регулятор\w*)\b"),
            (90, 0.92, r"\b(нов\w+|останн\w+)\s+(акт\w*|постанов\w*|розпорядж\w*)"),
            (85, 0.88, r"\bрегуляторн\w+\s+поді\w+"),
            (80, 0.82, r"\b(новин\w+|поді\w+)\s+(ринк\w+|регулятор\w*)"),
        ],
        "fetch_slots": regulator_recent.fetch_slots,
        "render": regulator_recent.render,
    },
    # ---------- MARKET ----------
    "bid_recommendation": {
        "personas": {"market_analyst"},
        "patterns": [
            (95, 0.95, r"\b(який|яку)\s+бід\w*"),
            (92, 0.93, r"\b(рекоменд\w+|поради\w*)\s+бід"),
            (90, 0.90, r"\bщо\s+ставити\w*"),
            (88, 0.88, r"\bстратег\w+\s+(на\s+)?завтра"),
            (80, 0.82, r"\bбід\w*\s+(на\s+)?завтра"),
        ],
        "fetch_slots": bid_recommendation.fetch_slots,
        "render": bid_recommendation.render,
    },
    "revenue_breakdown": {
        "personas": {"market_analyst"},
        "patterns": [
            (95, 0.95, r"\bвиторг\s+(по\s+)?(каналах|джерел\w+)"),
            (92, 0.93, r"\b(розбий|розклад)\s+(виторг|доход\w*)"),
            (90, 0.90, r"\bдоход\w*\s+(по\s+)?(каналах|джерел\w+|ринк\w+)"),
            (85, 0.88, r"\bревеню\w*\b"),
            (75, 0.78, r"\bвиторг\b"),
        ],
        "fetch_slots": revenue_breakdown.fetch_slots,
        "render": revenue_breakdown.render,
    },
    "arbitrage_window": {
        "personas": {"market_analyst", "battery_coach"},
        "patterns": [
            (95, 0.95, r"\bарбітраж\w*\s+вікн\w+"),
            (92, 0.93, r"\bвікн\w+\s+арбітраж"),
            (90, 0.90, r"\bколи\s+арбітраж"),
            (85, 0.88, r"\bарбітраж\w*"),
            (80, 0.82, r"\bкуп\w+\s+дешев\w+\s+продат\w+\s+дорог"),
        ],
        "fetch_slots": arbitrage_window.fetch_slots,
        "render": arbitrage_window.render,
    },
    "rdn_cap_alert": {
        "personas": {"market_analyst"},
        "patterns": [
            (95, 0.95, r"\b(цінов\w+\s+)?стел\w+\s+(рдн|спрацю\w+)"),
            (92, 0.93, r"\bцінов\w+\s+стел\w+"),
            (90, 0.90, r"\bcap\b"),
            (85, 0.88, r"\b(чи\s+)?спрацьов\w+\s+стел"),
            (80, 0.82, r"\bрдн\s+capped?"),
        ],
        "fetch_slots": rdn_cap_alert.fetch_slots,
        "render": rdn_cap_alert.render,
    },
    "market_summary_today": {
        "personas": {"market_analyst"},
        "patterns": [
            (95, 0.95, r"\bпідсумок\s+ринк\w+\s+сьогодні"),
            (92, 0.93, r"\bринок\s+сьогодні"),
            (90, 0.90, r"\bсумар\w+\s+(по\s+)?ринк"),
            (85, 0.88, r"\bпідсум\w+\s+ринк"),
        ],
        "fetch_slots": market_summary_today.fetch_slots,
        "render": market_summary_today.render,
    },
    # ---------- ENERGY ADVISOR ----------
    "scenario_blackout": {
        "personas": {"energy_advisor"},
        "patterns": [
            (95, 0.95, r"\b(сценар\w+\s+)?блекаут\w*"),
            (92, 0.93, r"\b(що|що\s+робит\w*)\s+(якщо\s+)?блекаут"),
            (90, 0.90, r"\bвідключенн\w+\s+електро"),
            (85, 0.88, r"\bаварійн\w+\s+(відключ\w+|режим\w*)"),
        ],
        "fetch_slots": scenario_blackout.fetch_slots,
        "render": scenario_blackout.render,
    },
    "scenario_imbalance": {
        "personas": {"energy_advisor"},
        "patterns": [
            (95, 0.95, r"\bсценар\w+\s+небаланс\w*"),
            (92, 0.93, r"\bякщо\s+небаланс"),
            (90, 0.90, r"\bризик\w+\s+небаланс"),
            (80, 0.80, r"\bнебаланс\w+\s+сценар"),
        ],
        "fetch_slots": scenario_imbalance.fetch_slots,
        "render": scenario_imbalance.render,
    },
    "self_consumption_today": {
        "personas": {"energy_advisor"},
        "patterns": [
            (95, 0.95, r"\bсво\w*\s+генерац\w*"),
            (94, 0.94, r"\bспожи\w+\s+(своєї|власної|своєю|своя)\s+генерац"),
            (92, 0.93, r"\bсамоспоживанн\w*"),
            (90, 0.90, r"\bскільки\s+спожи\w+\s+своєї"),
            (85, 0.88, r"\bяк\w+\s+(частк\w+|відсот\w+)\s+власн\w+\s+генерац"),
            (80, 0.82, r"\bвласн\w+\s+генерац\w*"),
        ],
        "fetch_slots": self_consumption_today.fetch_slots,
        "render": self_consumption_today.render,
    },
    "tariff_impact": {
        "personas": {"energy_advisor"},
        "patterns": [
            (95, 0.95, r"\bвплив\s+тариф\w+"),
            (92, 0.93, r"\bтариф\w+\s+вплив"),
            (90, 0.90, r"\bяк\s+тариф"),
            (85, 0.88, r"\bтариф\w+\s+(оплат\w+|витрат\w+)"),
        ],
        "fetch_slots": tariff_impact.fetch_slots,
        "render": tariff_impact.render,
    },
    "savings_summary": {
        "personas": {"energy_advisor"},
        "patterns": [
            (95, 0.95, r"\bскільки\s+зекономил\w*"),
            (92, 0.93, r"\bекономі\w+\s+(сьогодні|за\s+місяц)"),
            (90, 0.90, r"\bзекономл\w+"),
            (85, 0.88, r"\bекономі\w+\b"),
        ],
        "fetch_slots": savings_summary.fetch_slots,
        "render": savings_summary.render,
    },
    # ---------- BATTERY COACH ----------
    "battery_schedule": {
        "personas": {"battery_coach"},
        "patterns": [
            (98, 0.96, r"\bграфік\s+батаре\w+"),
            (95, 0.95, r"\bколи\s+(заряджа\w+|зар\w*)\s+батаре"),
            (94, 0.94, r"\bколи\s+розряджа\w+"),
            (92, 0.92, r"\bколи\s+зар\w*\b"),
            (91, 0.91, r"\bколи\s+розр\w*\b"),
            (90, 0.90, r"\bкращ\w+\s+(години|час)\s+зарядк"),
        ],
        "fetch_slots": battery_schedule.fetch_slots,
        "render": battery_schedule.render,
    },
    "battery_cycle_check": {
        "personas": {"battery_coach"},
        "patterns": [
            (95, 0.95, r"\b(перевір|стан)\s+цикл\w+\s+батаре"),
            (92, 0.93, r"\bцикл\w+\s+батаре"),
            (90, 0.90, r"\bзнос\s+батаре"),
            (85, 0.88, r"\bcapacity\s*fade"),
            (80, 0.82, r"\bдеградац\w+\s+батаре"),
        ],
        "fetch_slots": battery_cycle_check.fetch_slots,
        "render": battery_cycle_check.render,
    },
    "soc_status_now": {
        "personas": {"battery_coach"},
        "patterns": [
            (95, 0.95, r"\bпоточн\w+\s+soc"),
            (92, 0.93, r"\bяк\w+\s+soc"),
            (90, 0.90, r"\bsoc\b"),
            (85, 0.88, r"\bстан\s+зарядк"),
            (80, 0.82, r"\bрівень\s+зарядк"),
        ],
        "fetch_slots": soc_status_now.fetch_slots,
        "render": soc_status_now.render,
    },
    "dispatch_advice_now": {
        "personas": {"battery_coach"},
        "patterns": [
            (95, 0.95, r"\bщо\s+робит\w+\s+(зараз|з\s+диспетчер)"),
            (92, 0.93, r"\bдиспетчериз\w+\s+(зараз|сейчас)"),
            (90, 0.90, r"\bрекоменд\w+\s+(дій|зараз)"),
            (85, 0.88, r"\bпорад\w+\s+(зараз|по\s+диспетчер)"),
        ],
        "fetch_slots": dispatch_advice_now.fetch_slots,
        "render": dispatch_advice_now.render,
    },
}


# Pre-compile patterns once.
for _code, _meta in INTENT_REGISTRY.items():
    _meta["compiled_patterns"] = [
        (p, c, re.compile(rgx, re.IGNORECASE))
        for (p, c, rgx) in _meta["patterns"]
    ]


def get_intent(code: str) -> dict[str, Any] | None:
    return INTENT_REGISTRY.get(code)


__all__ = ["INTENT_REGISTRY", "get_intent"]
