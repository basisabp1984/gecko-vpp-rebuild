"""scenario_blackout — what to do during a blackout (uses asset capacity + UZE soc)."""

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
    # Aggregate self-gen and storage stand-by capacity.
    q = text(
        """
        SELECT a.asset_class, SUM(a.capacity_mw)::float AS cap_mw,
               SUM(COALESCE(a.storage_capacity_mwh, 0))::float AS stor_mwh,
               COUNT(*) AS n
        FROM core.assets a
        WHERE a.tenant_id = :tid
          AND a.status = 'active'
        GROUP BY a.asset_class
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id})).mappings().all()
    classes = {r["asset_class"]: {"cap_mw": float(r["cap_mw"]), "stor_mwh": float(r["stor_mwh"] or 0), "n": int(r["n"])} for r in rows}

    # Average SOC of UZE.
    q2 = text(
        """
        SELECT AVG(soc_pct)::float AS avg_soc
        FROM dispatch.telemetry
        WHERE tenant_id = :tid
          AND date = :d
          AND soc_pct IS NOT NULL
        """
    )
    r2 = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().first()

    return {
        "date_ua": date_ua(d),
        "classes": classes,
        "avg_soc": float(r2["avg_soc"]) if r2 and r2["avg_soc"] is not None else None,
        "_evidence": [
            evidence_row(
                "core.assets + dispatch.telemetry.soc_pct",
                columns=["capacity_mw", "storage_capacity_mwh", "soc_pct"],
                ui_link="/c-i/aktyvy",
                label=f"Капасіті портфеля на {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    cls = slots["classes"]
    soc = slots["avg_soc"]
    if not cls:
        return f"На {slots['date_ua']} активів у портфелі не знайдено для сценарію блекауту."
    self_gen = cls.get("СЕС", {}).get("cap_mw", 0) + cls.get("ВЕС", {}).get("cap_mw", 0) + cls.get("ГПУ", {}).get("cap_mw", 0)
    stor = cls.get("УЗЕ", {}).get("stor_mwh", 0)
    autonomy_h = (stor * (soc / 100 if soc else 0.5)) / max(self_gen + 0.1, 1) if self_gen > 0 else 0
    soc_str = f"{fmt_num(soc, 0)}%" if soc is not None else "невідомо"
    return (
        f"Сценарій блекауту (на {slots['date_ua']}): "
        f"власна генерація — {fmt_num(self_gen, 2)} МВт (СЕС/ВЕС/ГПУ), "
        f"резерв УЗЕ — {fmt_num(stor, 1)} МВт·год при середньому SOC {soc_str}. "
        f"Орієнтовна автономність критичного навантаження: ~{fmt_num(autonomy_h, 1)} год. "
        f"Рекомендація: підняти SOC до 90% до прогнозованого піка, перейти на острівний режим за командою. "
        f"Джерело: core.assets + dispatch.telemetry."
    )
