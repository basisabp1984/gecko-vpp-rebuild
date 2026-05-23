"""savings_summary — kpi_daily aggregated for last 30 days."""

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
        SELECT
            SUM(grn_saved_uah)::float AS saved,
            SUM(grn_earned_uah)::float AS earned,
            SUM(co2_avoided_tn)::float AS co2,
            AVG(availability_pct)::float AS avail,
            COUNT(DISTINCT date) AS days
        FROM ems.kpi_daily
        WHERE tenant_id = :tid
          AND date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
        """
    )
    r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()
    return {
        "date_ua": date_ua(d),
        "saved": float(r["saved"] or 0) if r else 0,
        "earned": float(r["earned"] or 0) if r else 0,
        "co2": float(r["co2"] or 0) if r else 0,
        "avail": float(r["avail"] or 0) if r else 0,
        "days": int(r["days"] or 0) if r else 0,
        "_evidence": [
            evidence_row(
                "ems.kpi_daily",
                columns=["grn_saved_uah", "grn_earned_uah", "co2_avoided_tn"],
                ui_link="/c-i/zvity",
                label=f"KPI 30 днів до {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    if slots["days"] == 0:
        return f"За 30 днів до {slots['date_ua']} KPI не знайдено (ems.kpi_daily)."
    return (
        f"Економія/виторг за {slots['days']} днів до {slots['date_ua']}: "
        f"зекономлено {fmt_uah(slots['saved'])}, зароблено {fmt_uah(slots['earned'])}. "
        f"Уникнуто CO₂: {fmt_num(slots['co2'], 2)} тон. "
        f"Доступність парку — {fmt_num(slots['avail'], 1)}%. "
        f"Джерело: ems.kpi_daily."
    )
