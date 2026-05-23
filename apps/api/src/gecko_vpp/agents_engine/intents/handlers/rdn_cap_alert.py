"""rdn_cap_alert — count of capped hours in the last 7 days."""

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
        SELECT date, hour, price_uah_mwh::float AS price, cap_uah_mwh::float AS cap, is_capped
        FROM market.rdn_prices
        WHERE tenant_id = :tid
          AND date BETWEEN (CAST(:d AS date) - INTERVAL '6 days') AND :d
          AND is_capped = TRUE
        ORDER BY date DESC, hour
        LIMIT 50
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    capped = [
        {"date": r["date"], "hour": int(r["hour"]), "price": float(r["price"]), "cap": float(r["cap"] or 0)}
        for r in rows
    ]

    q2 = text(
        """
        SELECT COUNT(*) FILTER (WHERE is_capped) AS n_cap,
               COUNT(*) AS n_total
        FROM market.rdn_prices
        WHERE tenant_id = :tid
          AND date BETWEEN (CAST(:d AS date) - INTERVAL '6 days') AND :d
        """
    )
    r2 = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().first()

    return {
        "date_ua": date_ua(d),
        "capped": capped,
        "n_cap": int(r2["n_cap"] or 0) if r2 else 0,
        "n_total": int(r2["n_total"] or 0) if r2 else 0,
        "_evidence": [
            evidence_row(
                "market.rdn_prices",
                columns=["is_capped", "cap_uah_mwh", "price_uah_mwh"],
                ui_link="/producer/rynok?market=rdn",
                label="Цінова стеля РДН за тиждень",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    n = slots["n_cap"]
    total = slots["n_total"]
    if n == 0:
        return (
            f"За тиждень до {slots['date_ua']} цінова стеля РДН НЕ спрацьовувала "
            f"({total} годин перевірено). Ризик capping низький. Джерело: market.rdn_prices."
        )
    pct = (n / total * 100) if total else 0
    sample = slots["capped"][:5]
    sample_str = ", ".join(f"{s['date'].strftime('%d.%m')} {s['hour']}:00" for s in sample)
    return (
        f"За тиждень до {slots['date_ua']} цінова стеля РДН спрацювала {n} разів "
        f"({fmt_num(pct, 1)}% від {total} годин). Останні випадки: {sample_str}. "
        f"Розгляньте VDR-арбітраж замість BLOCK-bid у пікові години. "
        f"Джерело: market.rdn_prices.is_capped."
    )
