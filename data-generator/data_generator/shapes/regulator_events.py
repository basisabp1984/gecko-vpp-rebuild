"""regulatory.regulator_events — НКРЕКП-style notices, ~10 in window.

Per ARCHITECTURE.md §3.11.3 #6: 2 TARIFF, 3 INFO, 2 NOTICE, 2 WARN, 1 CRITICAL.
"""

from __future__ import annotations

from datetime import date as DateT, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import SYNTH_DATE_END, SYNTH_DATE_START


EVENTS = [
    # (issuer, act_type, act_number, days_offset, title, category, severity, summary, full_text)
    (
        "НКРЕКП",
        "Постанова",
        "№ 421",
        2,
        "Перегляд тарифу на послуги передачі електричної енергії",
        "TARIFF",
        "NOTICE",
        "З 1 травня 2026 року тариф на послуги Укренерго підвищується на 4,2%.",
        "У зв'язку зі стабілізаційними заходами та зростанням операційних витрат...",
    ),
    (
        "НКРЕКП",
        "Постанова",
        "№ 458",
        7,
        "Граничні ціни на РДН/ВДР у травні 2026",
        "TARIFF",
        "INFO",
        "Граничні ціни на РДН і ВДР залишаються на рівні 5600–6900 UAH/MWh.",
        "Згідно з умовами надзвичайного стану в енергетиці...",
    ),
    (
        "Укренерго",
        "Розпорядження",
        "№ DSO-2026-118",
        10,
        "Планові обмеження ВДЕ у південному регіоні",
        "EMERGENCY",
        "WARN",
        "У період 12–14 травня — ймовірні обмеження ВДЕ через ремонтні роботи на ВПС.",
        "Внаслідок планових ремонтних робіт на дільниці 750 кВ...",
    ),
    (
        "Укренерго",
        "Оперативне розпорядження",
        "№ OPS-2026-247",
        14,
        "Розширене вікно подачі прогнозів",
        "INFO",
        "INFO",
        "Час подачі добових прогнозів продовжено до 13:00 (раніше — 11:00).",
        "Тимчасова умова в умовах воєнного стану...",
    ),
    (
        "ОРЕЕ",
        "Повідомлення",
        "OREE-2026-051",
        18,
        "Оновлення публікації РДН індексів",
        "INFO",
        "INFO",
        "З 20 травня індекси РДН публікуються щодня о 14:00.",
        "ДП Оператор ринку повідомляє про зміни регламенту публікації...",
    ),
    (
        "НКРЕКП",
        "Постанова",
        "№ 463",
        20,
        "Затверджено нову методику розрахунку тарифу для УЗЕ",
        "TARIFF",
        "NOTICE",
        "Затверджена методика розрахунку тарифу для систем УЗЕ потужністю >1 МВт.",
        "Методика враховує специфіку послуг частотного регулювання...",
    ),
    (
        "Кабмін",
        "Постанова",
        "КМУ-2026-184",
        22,
        "Зміни до Закону про ринок електричної енергії",
        "CODE_AMENDMENT",
        "WARN",
        "Внесено зміни до Розділу VII Закону про ринок електричної енергії.",
        "Внесено уточнення щодо балансуючих груп та відповідальності...",
    ),
    (
        "Укренерго",
        "Оперативне сповіщення",
        "ALERT-2026-091",
        25,
        "Критична подія в енергосистемі — посилений диспетчерський контроль",
        "EMERGENCY",
        "CRITICAL",
        "Введено посилений диспетчерський контроль у зв'язку з ушкодженням транзитної ЛЕП 750 кВ.",
        "Тимчасові обмеження дисбалансів. БРП мають утриматися від ризикових позицій...",
    ),
    (
        "ГП",
        "Інформаційне повідомлення",
        "GP-2026-076",
        4,
        "Закриття звітного періоду за квітень",
        "INFO",
        "INFO",
        "Звітний період за квітень закрито. Розрахункові акти вже доступні.",
        "Гарантований Покупець нагадує...",
    ),
    (
        "НКРЕКП",
        "Постанова",
        "№ 480",
        28,
        "Запровадження санкційного механізму для непідписаних актів",
        "SANCTION",
        "NOTICE",
        "З 1 червня 2026 — за непідписання актів у строк передбачено санкції.",
        "З метою забезпечення розрахункової дисципліни в ОРЕ...",
    ),
]


async def generate(conn: AsyncConnection) -> int:
    stmt = text(
        """
        INSERT INTO regulatory.regulator_events
            (issuer, act_type, act_number, issued_at, effective_at,
             title, category, severity, summary, affected_entities,
             affected_tenants, source_url, full_text)
        VALUES
            (:issuer, :act_type, :act_number, :issued_at, :effective_at,
             :title, :category, :severity, :summary, CAST(:affected_entities AS jsonb),
             CAST(:affected_tenants AS uuid[]), :source_url, :full_text)
        """
    )
    rows: list[dict[str, Any]] = []
    for ev in EVENTS:
        (
            issuer, act_type, act_number, days_offset, title,
            category, severity, summary, full_text,
        ) = ev
        issued_at = SYNTH_DATE_START + timedelta(days=days_offset)
        effective_at = issued_at + timedelta(days=7)
        rows.append(
            {
                "issuer": issuer,
                "act_type": act_type,
                "act_number": act_number,
                "issued_at": issued_at,
                "effective_at": effective_at,
                "title": title,
                "category": category,
                "severity": severity,
                "summary": summary,
                "affected_entities": '["UA-IPS"]',
                "affected_tenants": "{}",
                "source_url": "https://www.nerc.gov.ua/?",
                "full_text": full_text,
            }
        )
    result = await conn.execute(stmt, rows)
    return (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
