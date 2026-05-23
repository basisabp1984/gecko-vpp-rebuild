"""production_trend_7d — 7-day MWh series."""

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
    d_end = synth_today()
    q = text(
        """
        SELECT t.date, SUM(GREATEST(t.active_power_mw, 0))::float AS mwh
        FROM dispatch.telemetry t
        WHERE t.tenant_id = :tid
          AND t.date BETWEEN (CAST(:d_end AS date) - INTERVAL '6 days') AND :d_end
        GROUP BY t.date
        ORDER BY t.date
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d_end": d_end})).mappings().all()
    series = [{"date": r["date"], "mwh": float(r["mwh"] or 0)} for r in rows]
    total = sum(s["mwh"] for s in series)
    avg = total / len(series) if series else 0.0
    best = max(series, key=lambda x: x["mwh"]) if series else None
    worst = min(series, key=lambda x: x["mwh"]) if series else None
    return {
        "series": series,
        "total": total,
        "avg": avg,
        "best": best,
        "worst": worst,
        "date_ua": date_ua(d_end),
        "_evidence": [
            evidence_row(
                "dispatch.telemetry",
                columns=["active_power_mw", "date"],
                label=f"7-денний тренд до {date_ua(d_end)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    series = slots["series"]
    if not series:
        return (
            f"За останні 7 днів (до {slots['date_ua']}) телеметрії не знайдено. "
            "Перевірте під'єднання активів."
        )
    best = slots["best"]
    worst = slots["worst"]
    return (
        f"За останні 7 днів портфель видав {fmt_num(slots['total'])} МВт·год "
        f"(в середньому {fmt_num(slots['avg'])} МВт·год/день). "
        f"Найкращий день — {best['date'].strftime('%d.%m')}: {fmt_num(best['mwh'])} МВт·год; "
        f"найгірший — {worst['date'].strftime('%d.%m')}: {fmt_num(worst['mwh'])} МВт·год. "
        f"Джерело: dispatch.telemetry, вікно до {slots['date_ua']}."
    )
