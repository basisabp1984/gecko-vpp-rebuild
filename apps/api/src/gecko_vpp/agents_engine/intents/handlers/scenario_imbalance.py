"""scenario_imbalance — risk of imbalance based on forecast confidence and recent BR exposure."""

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
        SELECT SUM(ABS(our_imbalance_mwh))::float AS imb_mwh,
               SUM(settlement_uah)::float AS uah,
               COUNT(*) FILTER (WHERE ABS(our_imbalance_mwh) > 0.5) AS spike_hours
        FROM market.br_settlements
        WHERE tenant_id = :tid
          AND date BETWEEN (CAST(:d AS date) - INTERVAL '6 days') AND :d
        """
    )
    r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()
    return {
        "date_ua": date_ua(d),
        "imb_mwh": float(r["imb_mwh"] or 0) if r else 0,
        "uah": float(r["uah"] or 0) if r else 0,
        "spike_hours": int(r["spike_hours"] or 0) if r else 0,
        "_evidence": [
            evidence_row(
                "market.br_settlements",
                columns=["our_imbalance_mwh", "settlement_uah"],
                ui_link="/producer/rynok?market=br",
                label=f"БР 7 днів до {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    if slots["imb_mwh"] == 0:
        return (
            f"За тиждень до {slots['date_ua']} ризик небалансу низький — "
            "БР-розрахунки відсутні. Джерело: market.br_settlements."
        )
    risk = "ВИСОКИЙ" if slots["spike_hours"] >= 10 else "СЕРЕДНІЙ" if slots["spike_hours"] >= 3 else "НИЗЬКИЙ"
    return (
        f"Сценарій небалансу (за тиждень до {slots['date_ua']}): "
        f"сумарний небаланс {fmt_num(slots['imb_mwh'], 2)} МВт·год, "
        f"оплата БР {fmt_uah(slots['uah'])}, "
        f"{slots['spike_hours']} годин зі сплеском (|imb| > 0.5 МВт·год). "
        f"Загальний ризик — {risk}. "
        f"Mitigation: refined-прогноз на D-1 17:30, переуступка через ВДР, "
        f"тримати спот-FCR резерв батареї. "
        f"Джерело: market.br_settlements."
    )
