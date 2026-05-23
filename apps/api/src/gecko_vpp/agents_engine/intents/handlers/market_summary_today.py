"""market_summary_today — one-line summary across RDN/BR for today."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine._common import (
    date_ua,
    evidence_row,
    fmt_num,
    fmt_uah,
    synth_today,
)


async def fetch_slots(session: AsyncSession, *, tenant_id: str, now: Any = None) -> dict[str, Any]:
    d = synth_today()
    q = text(
        """
        SELECT AVG(price_uah_mwh)::float AS avg_p,
               MAX(price_uah_mwh)::float AS max_p,
               MIN(price_uah_mwh)::float AS min_p,
               SUM(volume_mwh)::float AS vol,
               COUNT(*) FILTER (WHERE is_capped) AS capped
        FROM market.rdn_prices
        WHERE tenant_id = :tid AND date = :d
        """
    )
    r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()

    q2 = text(
        """
        SELECT SUM(settlement_uah)::float AS uah,
               SUM(our_imbalance_mwh)::float AS imb
        FROM market.br_settlements
        WHERE tenant_id = :tid AND date = :d
        """
    )
    r2 = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().first()

    return {
        "date_ua": date_ua(d),
        "rdn": {
            "avg": float(r["avg_p"] or 0) if r else 0,
            "max": float(r["max_p"] or 0) if r else 0,
            "min": float(r["min_p"] or 0) if r else 0,
            "vol": float(r["vol"] or 0) if r else 0,
            "capped": int(r["capped"] or 0) if r else 0,
        },
        "br": {
            "uah": float(r2["uah"] or 0) if r2 else 0,
            "imb": float(r2["imb"] or 0) if r2 else 0,
        },
        "_evidence": [
            evidence_row(
                "market.rdn_prices + market.br_settlements",
                columns=["price_uah_mwh", "settlement_uah", "is_capped"],
                ui_link=f"/producer/rynok?date={d.isoformat()}",
                label=f"Підсумок ринку {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    rdn = slots["rdn"]
    br = slots["br"]
    if rdn["vol"] == 0 and br["uah"] == 0:
        return f"За {slots['date_ua']} ринкових даних не зафіксовано (market.*)."
    cap_note = f"(стеля {rdn['capped']} год)" if rdn["capped"] > 0 else "(стеля не спрацьовувала)"
    return (
        f"Підсумок ринку за {slots['date_ua']}: "
        f"РДН — середня {fmt_num(rdn['avg'])} грн/МВт·год, "
        f"діапазон {fmt_num(rdn['min'])}–{fmt_num(rdn['max'])}, "
        f"обсяг {fmt_num(rdn['vol'])} МВт·год {cap_note}. "
        f"БР — небаланс {fmt_num(br['imb'], 2)} МВт·год, розрахунок {fmt_uah(br['uah'])}. "
        f"Джерело: market.rdn_prices + market.br_settlements."
    )
