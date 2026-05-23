"""arbitrage_window — cheapest 3 hours + peakiest 3 hours today/tomorrow."""

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
    # Use today's prices if available, else fall back to yesterday.
    q = text(
        """
        SELECT hour, price_uah_mwh::float AS price
        FROM market.rdn_prices
        WHERE tenant_id = :tid
          AND date = :d
        ORDER BY hour
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    if not rows:
        d = d - timedelta(days=1)
        rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    prices = sorted([{"hour": int(r["hour"]), "price": float(r["price"])} for r in rows], key=lambda x: x["price"])
    cheap = prices[:3]
    peak = sorted(prices[-3:], key=lambda x: -x["price"])
    spread = (peak[0]["price"] - cheap[0]["price"]) if (peak and cheap) else 0.0
    return {
        "date_ua": date_ua(d),
        "cheap": cheap,
        "peak": peak,
        "spread": spread,
        "_evidence": [
            evidence_row(
                "market.rdn_prices",
                columns=["price_uah_mwh", "hour"],
                ui_link=f"/producer/rynok?market=rdn&date={d.isoformat()}",
                label=f"РДН {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    cheap = slots["cheap"]
    peak = slots["peak"]
    if not cheap or not peak:
        return f"За {slots['date_ua']} даних РДН не знайдено."
    cheap_hours = ", ".join(f"{c['hour']}:00 ({fmt_num(c['price'])} грн)" for c in cheap)
    peak_hours = ", ".join(f"{p['hour']}:00 ({fmt_num(p['price'])} грн)" for p in peak)
    return (
        f"Арбітражне вікно на {slots['date_ua']}: дешеві години — {cheap_hours}; "
        f"пікові години — {peak_hours}. "
        f"Спред {fmt_num(slots['spread'])} грн/МВт·год — заряджайтесь у дешеві години, "
        f"розряджайтесь у пікові. "
        f"Джерело: market.rdn_prices."
    )
