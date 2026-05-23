"""next_maintenance — list assets currently or soon-to-be in maintenance."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine._common import (
    date_ua,
    evidence_row,
    synth_today,
)


async def fetch_slots(session: AsyncSession, *, tenant_id: str, now: Any = None) -> dict[str, Any]:
    d = synth_today()
    # Synth data: maintenance signal lives in dispatch.telemetry.status='maintenance'
    # OR core.assets.status='maintenance'. We surface both.
    q = text(
        """
        SELECT a.id, a.display_name, a.asset_class, a.status AS asset_status,
               COUNT(t.*) FILTER (WHERE t.status = 'maintenance') AS maint_hours
        FROM core.assets a
        LEFT JOIN dispatch.telemetry t
          ON t.asset_id = a.id
         AND t.tenant_id = a.tenant_id
         AND t.date >= (CAST(:d AS date) - INTERVAL '7 days')
         AND t.date <= :d
        WHERE a.tenant_id = :tid
        GROUP BY a.id, a.display_name, a.asset_class, a.status
        ORDER BY maint_hours DESC, a.display_name
        LIMIT 5
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    in_maint = [r for r in rows if (r["maint_hours"] or 0) > 0 or r["asset_status"] == "maintenance"]
    return {
        "date_ua": date_ua(d),
        "in_maint": [
            {
                "name": r["display_name"],
                "class": r["asset_class"],
                "status": r["asset_status"],
                "hours": int(r["maint_hours"] or 0),
            }
            for r in in_maint
        ],
        "_evidence": [
            evidence_row(
                "core.assets + dispatch.telemetry.status",
                columns=["status", "display_name"],
                ui_link="/producer/aktyvy",
                label="Стан активів і обслуговування",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    d = slots["date_ua"]
    in_maint = slots["in_maint"]
    if not in_maint:
        return (
            f"На {d} активних подій ТО не зафіксовано. Жоден з активів не у статусі "
            f"'maintenance' за останні 7 днів. Джерело: core.assets + dispatch.telemetry."
        )
    lines = "; ".join(
        f"{a['name']} ({a['class']}, {a['hours']} год за тиждень)" for a in in_maint
    )
    return (
        f"На {d} в обслуговуванні / готуються до ТО: {lines}. "
        f"Запланувати наступне вікно ТО можна через /producer/dyspetcheryzatsiya. "
        f"Джерело: core.assets + dispatch.telemetry.status='maintenance'."
    )
