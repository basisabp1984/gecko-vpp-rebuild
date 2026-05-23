"""soc_status_now — latest SOC per battery."""

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
        SELECT DISTINCT ON (a.id)
               a.display_name,
               t.soc_pct::float AS soc,
               t.active_power_mw::float AS pw,
               t.status,
               t.date, t.hour
        FROM core.assets a
        JOIN dispatch.telemetry t
          ON t.asset_id = a.id
         AND t.tenant_id = a.tenant_id
        WHERE a.tenant_id = :tid
          AND a.asset_class = 'УЗЕ'
          AND t.soc_pct IS NOT NULL
        ORDER BY a.id, t.date DESC, t.hour DESC
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id})).mappings().all()
    bats = [
        {
            "name": r["display_name"],
            "soc": float(r["soc"]),
            "power_mw": float(r["pw"]),
            "status": r["status"],
            "as_of": f"{r['date']} {r['hour']}:00",
        }
        for r in rows
    ]
    return {
        "date_ua": date_ua(d),
        "batteries": bats,
        "_evidence": [
            evidence_row(
                "dispatch.telemetry.soc_pct (latest per УЗЕ)",
                columns=["soc_pct", "active_power_mw", "status"],
                ui_link="/storage/uze",
                label="Поточний SOC батарей",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    bats = slots["batteries"]
    if not bats:
        return f"У портфелі немає УЗЕ або відсутні дані SOC (dispatch.telemetry)."
    lines = []
    for b in bats:
        mode = "розряд" if b["power_mw"] < 0 else "заряд" if b["power_mw"] > 0 else "idle"
        lines.append(
            f"{b['name']}: SOC {fmt_num(b['soc'], 0)}%, режим {mode} "
            f"({fmt_num(abs(b['power_mw']), 2)} МВт), станом на {b['as_of']}."
        )
    return (
        "Поточний стан батарей:\n"
        + "\n".join(lines)
        + "\nДжерело: dispatch.telemetry (latest per asset)."
    )
