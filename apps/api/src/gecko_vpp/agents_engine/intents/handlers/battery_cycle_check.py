"""battery_cycle_check — count discharge cycles in last 30 days."""

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
    # Equivalent full cycles: sum(|discharge MWh|) / nameplate MWh.
    q = text(
        """
        SELECT a.display_name,
               a.storage_capacity_mwh::float AS cap_mwh,
               SUM(ABS(LEAST(t.active_power_mw, 0)))::float AS discharge_mwh,
               SUM(GREATEST(t.active_power_mw, 0))::float AS charge_mwh,
               MAX(t.soc_pct)::float AS max_soc,
               MIN(t.soc_pct)::float AS min_soc
        FROM core.assets a
        JOIN dispatch.telemetry t
          ON t.asset_id = a.id
         AND t.tenant_id = a.tenant_id
         AND t.date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
        WHERE a.tenant_id = :tid
          AND a.asset_class = 'УЗЕ'
        GROUP BY a.display_name, a.storage_capacity_mwh
        ORDER BY discharge_mwh DESC
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    batteries = []
    for r in rows:
        cap = float(r["cap_mwh"] or 1)
        disc = float(r["discharge_mwh"] or 0)
        efc = disc / cap if cap > 0 else 0
        batteries.append({
            "name": r["display_name"],
            "cap_mwh": cap,
            "discharge_mwh": disc,
            "charge_mwh": float(r["charge_mwh"] or 0),
            "efc_30d": efc,
            "max_soc": float(r["max_soc"] or 0),
            "min_soc": float(r["min_soc"] or 0),
        })
    return {
        "date_ua": date_ua(d),
        "batteries": batteries,
        "_evidence": [
            evidence_row(
                "dispatch.telemetry + core.assets (asset_class='УЗЕ')",
                columns=["active_power_mw", "soc_pct", "storage_capacity_mwh"],
                ui_link="/storage/zvity",
                label=f"Цикли УЗЕ 30 днів до {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    bats = slots["batteries"]
    if not bats:
        return f"На {slots['date_ua']} батарей (УЗЕ) у портфелі не знайдено."
    lines = []
    for b in bats:
        # Project to 365 days; 6000-cycle nameplate per battery spec.
        annual_efc = b["efc_30d"] * (365 / 30)
        budget_used_pct = (annual_efc / 6000 * 100) if annual_efc else 0
        lines.append(
            f"{b['name']}: за 30 днів {fmt_num(b['discharge_mwh'])} МВт·год розряду "
            f"≈ {fmt_num(b['efc_30d'], 2)} ЕFC (екв.повних циклів), "
            f"проєкція на рік ~{fmt_num(annual_efc, 0)} EFC "
            f"({fmt_num(budget_used_pct, 1)}% від 6000-циклового ресурсу). "
            f"SOC діапазон {fmt_num(b['min_soc'], 0)}–{fmt_num(b['max_soc'], 0)}%."
        )
    return (
        f"Перевірка циклів батарей (30 днів до {slots['date_ua']}):\n"
        + "\n".join(lines)
        + "\nДжерело: dispatch.telemetry + core.assets."
    )
