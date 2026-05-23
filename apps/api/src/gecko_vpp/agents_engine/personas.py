"""Persona registry — 4 personas, voice tone, allowed intents, fallback samples."""

from __future__ import annotations

from typing import TypedDict


class PersonaConfig(TypedDict):
    code: str
    display_name: str
    voice: str
    greeting: str
    allowed_intents: list[str]
    fallback_sample_questions: list[str]


PERSONAS: dict[str, PersonaConfig] = {
    "dispatcher_analyst": {
        "code": "dispatcher_analyst",
        "display_name": "Диспетчерський аналітик",
        "voice": "formal",
        "greeting": "Я — Диспетчерський аналітик. Допоможу з виробництвом, диспетчеризацією, прогнозами.",
        "allowed_intents": [
            "production_today",
            "production_trend_7d",
            "imbalance_explain",
            "forecast_accuracy",
            "next_maintenance",
            "regulator_recent",
        ],
        "fallback_sample_questions": [
            "що сьогодні з виробництвом?",
            "як йшло виробництво за тиждень?",
            "поясни небаланс сьогодні",
            "яка точність прогнозу?",
            "коли наступне ТО?",
        ],
    },
    "market_analyst": {
        "code": "market_analyst",
        "display_name": "Ринковий аналітик",
        "voice": "formal",
        "greeting": "Я — Ринковий аналітик. Допоможу з біддингом, виторгом і ціновими вікнами.",
        "allowed_intents": [
            "bid_recommendation",
            "revenue_breakdown",
            "arbitrage_window",
            "rdn_cap_alert",
            "market_summary_today",
            "regulator_recent",
        ],
        "fallback_sample_questions": [
            "який бід на завтра?",
            "розбий виторг по каналах",
            "коли арбітражне вікно?",
            "чи спрацьовувала цінова стеля?",
            "підсумок ринку сьогодні",
        ],
    },
    "energy_advisor": {
        "code": "energy_advisor",
        "display_name": "Енергетичний радник",
        "voice": "advisor",
        "greeting": "Я — Енергетичний радник. Підкажу, як зекономити та підготуватись до сценаріїв.",
        "allowed_intents": [
            "scenario_blackout",
            "scenario_imbalance",
            "self_consumption_today",
            "tariff_impact",
            "regulator_recent",
            "savings_summary",
        ],
        "fallback_sample_questions": [
            "що якщо буде блекаут?",
            "сценарій небалансу",
            "скільки спожили своєї генерації?",
            "вплив тарифу на оплату",
            "скільки зекономили?",
        ],
    },
    "battery_coach": {
        "code": "battery_coach",
        "display_name": "Тренер по батареях",
        "voice": "coach",
        "greeting": "Я — Тренер по батареях. Підкажу графік заряд/розряд, цикли і поточний SOC.",
        "allowed_intents": [
            "battery_schedule",
            "battery_cycle_check",
            "arbitrage_window",
            "soc_status_now",
            "dispatch_advice_now",
        ],
        "fallback_sample_questions": [
            "коли заряджати батарею?",
            "перевір цикли батареї",
            "коли арбітражне вікно?",
            "який поточний SOC?",
            "що робити з диспетчеризацією зараз?",
        ],
    },
}

ALLOWED_PERSONAS = frozenset(PERSONAS.keys())


def persona_allows(persona: str, intent: str) -> bool:
    """True iff the persona has the intent in its allowed list."""
    cfg = PERSONAS.get(persona)
    if cfg is None:
        return False
    return intent in cfg["allowed_intents"]


def fallback_questions(persona: str) -> list[str]:
    cfg = PERSONAS.get(persona)
    if cfg is None:
        return []
    return list(cfg["fallback_sample_questions"])
