"""dispatch_advice_now — what to do this hour for batteries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine._common import (
    date_ua,
    evidence_row,
    fmt_num,
    synth_now,
    synth_today,
)


async def fetch_slots(session: AsyncSession, *, tenant_id: str, now: Any = None) -> dict[str, Any]:
    d = synth_today()
    hour_now = synth_now().hour + 1  # synth schema is 1..24
    # Find this hour's price (or last known) and the next 6 hours.
    q = text(
        """
        SELECT hour, price_uah_mwh::float AS price
        FROM market.rdn_prices
        WHERE tenant_id = :tid AND date = :d
        ORDER BY hour
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    prices = [{"h": int(r["hour"]), "p": float(r["price"])} for r in rows]
    current = next((p for p in prices if p["h"] == hour_now), prices[0] if prices else None)
    upcoming = [p for p in prices if p["h"] > hour_now][:6]
    avg = sum(p["p"] for p in prices) / len(prices) if prices else 0
    next_cheap = min(upcoming, key=lambda p: p["p"], default=None)
    next_peak = max(upcoming, key=lambda p: p["p"], default=None)

    return {
        "date_ua": date_ua(d),
        "hour_now": hour_now,
        "current": current,
        "avg": avg,
        "next_cheap": next_cheap,
        "next_peak": next_peak,
        "_evidence": [
            evidence_row(
                "market.rdn_prices",
                columns=["hour", "price_uah_mwh"],
                ui_link="/storage/uze",
                label=f"РДН {date_ua(d)} (наступні 6 год)",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    cur = slots["current"]
    avg = slots["avg"]
    if not cur:
        return f"На {slots['date_ua']} даних РДН немає для рекомендацій."
    action = "ТРИМАТИ idle"
    if cur["p"] < avg * 0.85:
        action = "ЗАРЯДЖАТИ (ціна нижче середньої)"
    elif cur["p"] > avg * 1.15:
        action = "РОЗРЯДЖАТИ (ціна вище середньої)"
    upcoming_note = ""
    if slots["next_cheap"]:
        upcoming_note += (
            f" Найближче дешеве вікно — {slots['next_cheap']['h']}:00 "
            f"({fmt_num(slots['next_cheap']['p'])} грн)."
        )
    if slots["next_peak"]:
        upcoming_note += (
            f" Найближчий пік — {slots['next_peak']['h']}:00 "
            f"({fmt_num(slots['next_peak']['p'])} грн)."
        )
    return (
        f"Поточна година {cur['h']}:00 на {slots['date_ua']}: "
        f"ціна РДН {fmt_num(cur['p'])} грн/МВт·год при середній {fmt_num(avg)} грн. "
        f"Рекомендація: {action}.{upcoming_note} "
        f"Джерело: market.rdn_prices."
    )
