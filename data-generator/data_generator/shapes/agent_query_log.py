"""agents.query_log — pre-seed ~30 sample queries (one per intent × persona)
for visual richness on /admin/analyze. Required for §11.15.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    SYNTH_DATE_START,
    TENANTS,
)
from data_generator.rng import get_rng


KYIV_OFFSET = timezone(timedelta(hours=3))

# (persona, intent, user_text, response_text, confidence)
SAMPLE_QUERIES = (
    (
        "dispatcher_analyst",
        "asset_status",
        "Що зараз з виробництвом по Поляна СЕС-1?",
        "Поляна СЕС-1 виробляє 6.4 МВт (80% потужності), статус online.",
        0.94,
    ),
    (
        "dispatcher_analyst",
        "next_imbalance",
        "Коли очікується наступний небаланс?",
        "За прогнозом на 17:00 — невеликий short, ~3.2 МВт. Дисбаланс у межах допустимого.",
        0.88,
    ),
    (
        "dispatcher_analyst",
        "curtailment_explanation",
        "Чому Одеська ВЕС обмежена сьогодні?",
        "Команда ТСО на обмеження активна з 23:00 (нічна перепродукція). До 06:00.",
        0.92,
    ),
    (
        "market_analyst",
        "rdn_evening_peak",
        "Який вечірній пік РДН був учора?",
        "Учорашній пік 17:00–21:00: середня ціна 6650 UAH/MWh, 4 з 5 годин на капі.",
        0.96,
    ),
    (
        "market_analyst",
        "best_arbitrage",
        "Найкраща арбітражна можливість на завтра?",
        "Найвищий спред: charge 03:00 (1850 UAH/MWh) — discharge 19:00 (6900 UAH/MWh).",
        0.91,
    ),
    (
        "market_analyst",
        "br_settlement_check",
        "Скільки ми заплатили за небаланс минулого тижня?",
        "За тиждень 16–22.05 балансуючі розрахунки: −47 250 UAH (на користь системи).",
        0.85,
    ),
    (
        "energy_advisor",
        "bill_shave",
        "Як зменшити рахунок за травень?",
        "Перенесення гнучкого навантаження з 18:00–20:00 на 03:00–05:00 → економія 12%.",
        0.89,
    ),
    (
        "energy_advisor",
        "co2_progress",
        "Скільки CO₂ вдалось уникнути цього місяця?",
        "За поточний місяць — 42 т CO₂, що відповідає ~6% від річної цілі компанії.",
        0.93,
    ),
    (
        "energy_advisor",
        "outage_risk",
        "Чи будуть відключення завтра?",
        "За графіком Укренерго — без планових. Резерв системи 8.2%, ризик низький.",
        0.87,
    ),
    (
        "battery_coach",
        "when_to_charge",
        "Коли заряджати батарею сьогодні?",
        "Оптимальне вікно зарядки: 02:00–06:00. Прогноз ціни — 1700 UAH/MWh.",
        0.95,
    ),
    (
        "battery_coach",
        "soh_check",
        "Який стан здоров'я BESS-1?",
        "Капасити фейд: 2.4% (норма для віку). SOC-розкид: 12–88%, охолодження OK.",
        0.92,
    ),
    (
        "battery_coach",
        "frequency_revenue",
        "Скільки заробили на FCR за тиждень?",
        "За тиждень: FCR — 18 200 UAH, aFRR_up — 27 400 UAH. Сумарно 45 600 UAH.",
        0.90,
    ),
)


async def generate(conn: AsyncConnection) -> int:
    stmt = text(
        """
        INSERT INTO agents.query_log
            (tenant_id, persona, user_text, classified_intent, confidence,
             response_text, evidence, duration_ms, created_at)
        VALUES
            (CAST(:tenant_id AS uuid), :persona, :user_text, :intent,
             :confidence, :response_text, CAST(:evidence AS jsonb), :dur, :created_at)
        """
    )
    rng = get_rng("agent_queries")
    rows: list[dict[str, Any]] = []
    for ti, tenant in enumerate(TENANTS):
        for qi, (persona, intent, utext, response, conf) in enumerate(SAMPLE_QUERIES):
            # Each query mapped to one tenant primarily but pick persona compatibility
            if tenant.segment == "c-i" and persona in ("dispatcher_analyst", "market_analyst", "battery_coach"):
                # Skip these for c-i since their persona is energy_advisor
                if persona != "energy_advisor":
                    continue
            if tenant.segment == "storage" and persona == "energy_advisor":
                continue
            created_at = datetime.combine(
                SYNTH_DATE_START, datetime.min.time(),
                tzinfo=KYIV_OFFSET,
            ) + timedelta(days=int(rng.integers(0, 28)), hours=int(rng.integers(8, 22)))
            evidence = json.dumps(
                [
                    {"source": "market.rdn_prices", "ref": f"row#{qi+1}"},
                    {"source": "dispatch.telemetry", "ref": f"asset#{qi+1}"},
                ],
                ensure_ascii=False,
            )
            rows.append(
                {
                    "tenant_id": str(tenant.uuid),
                    "persona": persona,
                    "user_text": utext,
                    "intent": intent,
                    "confidence": conf,
                    "response_text": response,
                    "evidence": evidence,
                    "dur": int(rng.integers(120, 950)),
                    "created_at": created_at,
                }
            )
    if not rows:
        return 0
    result = await conn.execute(stmt, rows)
    return (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
