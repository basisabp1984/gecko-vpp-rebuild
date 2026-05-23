"""production_today — total MWh and top assets today."""

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


async def fetch_slots(
    session: AsyncSession, *, tenant_id: str, now: Any = None
) -> dict[str, Any]:
    d = synth_today()
    q = text(
        """
        SELECT a.display_name, a.asset_class,
               SUM(GREATEST(t.active_power_mw, 0))::float AS mwh,
               AVG(t.availability_pct)::float AS avail
        FROM dispatch.telemetry t
        JOIN core.assets a ON a.id = t.asset_id
        WHERE t.tenant_id = :tid
          AND t.date = :d
        GROUP BY a.display_name, a.asset_class
        ORDER BY mwh DESC
        LIMIT 5
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    total = sum(float(r["mwh"] or 0) for r in rows)
    avg_avail = (
        sum(float(r["avail"] or 0) for r in rows) / len(rows) if rows else 100.0
    )
    top = [
        {"name": r["display_name"], "class": r["asset_class"], "mwh": float(r["mwh"] or 0)}
        for r in rows[:3]
    ]
    return {
        "date_ua": date_ua(d),
        "total_mwh": total,
        "avg_availability": avg_avail,
        "top": top,
        "row_count": len(rows),
        "_evidence": [
            evidence_row(
                "dispatch.telemetry",
                columns=["active_power_mw", "availability_pct"],
                ui_link=f"/producer/aktyvy?date={d.isoformat()}",
                label=f"Телеметрія за {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    d = slots["date_ua"]
    total = slots["total_mwh"]
    avail = slots["avg_availability"]
    top = slots["top"]
    if not top or total <= 0:
        return (
            f"На основі телеметрії за {d} — активних МВт·год не зафіксовано. "
            "Перевірте статус активів у /producer/aktyvy."
        )
    top_str = "; ".join(
        f"{i + 1}) {a['name']} — {fmt_num(a['mwh'])} МВт·год"
        for i, a in enumerate(top)
    )
    return (
        f"Сьогодні ({d}) портфель видав {fmt_num(total)} МВт·год. "
        f"Топ активи: {top_str}. Середня доступність — {fmt_num(avail)}%. "
        f"На основі дані dispatch.telemetry."
    )
