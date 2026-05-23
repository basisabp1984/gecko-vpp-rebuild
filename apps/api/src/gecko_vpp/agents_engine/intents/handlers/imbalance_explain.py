"""imbalance_explain — pull today's worst BR imbalance hour."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine._common import (
    date_ua,
    evidence_row,
    fmt_num,
    synth_today,
)


async def fetch_slots(session: AsyncSession, *, tenant_id: str, now: Any = None) -> dict[str, Any]:
    d = synth_today()
    q = text(
        """
        SELECT id, date, hour, our_imbalance_mwh, price_short_uah_mwh,
               price_long_uah_mwh, system_direction, settlement_uah
        FROM market.br_settlements
        WHERE tenant_id = :tid
          AND date = :d
        ORDER BY ABS(our_imbalance_mwh) DESC
        LIMIT 1
        """
    )
    row = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()

    # Also pull daily sum for context.
    q2 = text(
        """
        SELECT SUM(our_imbalance_mwh)::float AS total_imb,
               SUM(settlement_uah)::float AS total_uah
        FROM market.br_settlements
        WHERE tenant_id = :tid AND date = :d
        """
    )
    daily = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().first()

    return {
        "date_ua": date_ua(d),
        "worst": (
            {
                "row_id": row["id"],
                "hour": row["hour"],
                "imbalance_mwh": float(row["our_imbalance_mwh"]),
                "price_short": float(row["price_short_uah_mwh"]),
                "price_long": float(row["price_long_uah_mwh"]),
                "direction": row["system_direction"],
                "settlement_uah": float(row["settlement_uah"]),
            }
            if row
            else None
        ),
        "total_imb": float(daily["total_imb"] or 0) if daily else 0.0,
        "total_uah": float(daily["total_uah"] or 0) if daily else 0.0,
        "_evidence": [
            evidence_row(
                "market.br_settlements",
                row_id=row["id"] if row else None,
                columns=["our_imbalance_mwh", "price_short_uah_mwh", "system_direction"],
                ui_link=f"/producer/rynok?market=br&date={d.isoformat()}",
                label=f"БР за {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    d = slots["date_ua"]
    w = slots["worst"]
    if not w:
        return f"За {d} даних балансуючого ринку не знайдено (market.br_settlements)."
    direction_uk = {"SHORT": "дефіцит", "LONG": "профіцит", "BALANCED": "баланс"}.get(
        w["direction"], w["direction"]
    )
    return (
        f"За {d} найбільший небаланс — година {w['hour']}: "
        f"{fmt_num(w['imbalance_mwh'], 2)} МВт·год ({direction_uk}), "
        f"ціна {fmt_num(w['price_short'])} грн/МВт·год коротко / "
        f"{fmt_num(w['price_long'])} грн/МВт·год довго. "
        f"Загалом за день — {fmt_num(slots['total_imb'], 2)} МВт·год небалансу, "
        f"розрахунок {fmt_num(slots['total_uah'])} грн. "
        f"Джерело: market.br_settlements (рядок #{w['row_id']})."
    )
