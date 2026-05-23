"""self_consumption_today — share of own-gen consumed locally today."""

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
    # Own generation: СЕС/ВЕС/ГПУ active_power_mw > 0
    # Load: Споживач/АктСпож active_power_mw < 0 (sign convention: consumption is negative)
    q = text(
        """
        SELECT
            SUM(GREATEST(t.active_power_mw, 0)) FILTER (
                WHERE a.asset_class IN ('СЕС','ВЕС','ГПУ')
            )::float AS gen_mwh,
            SUM(ABS(LEAST(t.active_power_mw, 0))) FILTER (
                WHERE a.asset_class IN ('Споживач','АктСпож')
            )::float AS load_mwh
        FROM dispatch.telemetry t
        JOIN core.assets a ON a.id = t.asset_id
        WHERE t.tenant_id = :tid
          AND t.date = :d
        """
    )
    r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()
    gen = float(r["gen_mwh"] or 0) if r else 0.0
    load = float(r["load_mwh"] or 0) if r else 0.0
    self_consumed = min(gen, load)
    share = (self_consumed / load * 100) if load > 0 else 0.0
    surplus = max(0.0, gen - load)
    return {
        "date_ua": date_ua(d),
        "gen": gen,
        "load": load,
        "self_consumed": self_consumed,
        "share_pct": share,
        "surplus": surplus,
        "_evidence": [
            evidence_row(
                "dispatch.telemetry × core.assets.asset_class",
                columns=["active_power_mw", "asset_class"],
                ui_link=f"/c-i/?date={d.isoformat()}",
                label=f"Своя vs спожита генерація {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    if slots["load"] == 0 and slots["gen"] == 0:
        return f"На {slots['date_ua']} даних телеметрії генерації/споживання немає."
    surplus_note = (
        f" Надлишок продано на РДН: {fmt_num(slots['surplus'])} МВт·год."
        if slots["surplus"] > 0
        else ""
    )
    return (
        f"На {slots['date_ua']}: власна генерація {fmt_num(slots['gen'])} МВт·год, "
        f"споживання {fmt_num(slots['load'])} МВт·год. "
        f"Самоспоживання {fmt_num(slots['self_consumed'])} МВт·год — "
        f"{fmt_num(slots['share_pct'], 1)}% потреби покрито власною генерацією.{surplus_note} "
        f"Джерело: dispatch.telemetry + core.assets."
    )
