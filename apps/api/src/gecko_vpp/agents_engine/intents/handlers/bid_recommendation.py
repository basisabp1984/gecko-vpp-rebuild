"""bid_recommendation — last-7-day RDN stats, cap-pinning hours, recommendation."""

from __future__ import annotations

from datetime import timedelta
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
    d_next = d + timedelta(days=1)
    q = text(
        """
        SELECT AVG(price_uah_mwh)::float AS avg_price,
               MAX(price_uah_mwh)::float AS peak_price,
               MIN(price_uah_mwh)::float AS low_price,
               COUNT(*) FILTER (WHERE is_capped) AS capped_hours,
               COUNT(*) AS total_hours
        FROM market.rdn_prices
        WHERE tenant_id = :tid
          AND date BETWEEN (CAST(:d AS date) - INTERVAL '6 days') AND :d
        """
    )
    r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()

    # Top peak hours from yesterday for guidance.
    q2 = text(
        """
        SELECT hour, price_uah_mwh::float AS price
        FROM market.rdn_prices
        WHERE tenant_id = :tid AND date = :d
        ORDER BY price_uah_mwh DESC
        LIMIT 5
        """
    )
    peaks = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().all()
    peak_hours = sorted([int(p["hour"]) for p in peaks])

    return {
        "date_ua": date_ua(d),
        "date_next_ua": date_ua(d_next),
        "avg_price": float(r["avg_price"] or 0) if r else 0,
        "peak_price": float(r["peak_price"] or 0) if r else 0,
        "low_price": float(r["low_price"] or 0) if r else 0,
        "capped_hours": int(r["capped_hours"] or 0) if r else 0,
        "total_hours": int(r["total_hours"] or 0) if r else 0,
        "peak_hours_list": peak_hours,
        "_evidence": [
            evidence_row(
                "market.rdn_prices",
                columns=["price_uah_mwh", "is_capped"],
                ui_link=f"/producer/rynok?market=rdn&date={d.isoformat()}",
                label=f"РДН 7 днів до {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    if slots["total_hours"] == 0:
        return f"За попередній тиждень даних РДН не знайдено (market.rdn_prices)."
    peak_hours_str = ", ".join(f"{h}:00" for h in slots["peak_hours_list"]) if slots["peak_hours_list"] else "—"
    capped = slots["capped_hours"]
    cap_note = (
        f"Цінова стеля спрацьовувала в {capped} з {slots['total_hours']} годин — "
        "будьте обережні в пікові вікна. "
        if capped > 0
        else "Стеля за тиждень не спрацьовувала. "
    )
    return (
        f"На {slots['date_next_ua']} (на основі попереднього тижня): "
        f"середня ціна РДН {fmt_num(slots['avg_price'])} грн/МВт·год, "
        f"пік {fmt_num(slots['peak_price'])}, дно {fmt_num(slots['low_price'])}. "
        f"{cap_note}"
        f"Найдорожчі години вчорашнього дня: {peak_hours_str} — туди націлюйте продажі. "
        f"Базова рекомендація: SELL у пікові години за ціною ≥{fmt_num(slots['avg_price'])} грн/МВт·год, "
        f"уникайте BLOCK-bid в години стелі. "
        f"Джерело: market.rdn_prices."
    )
