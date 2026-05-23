"""forecast_accuracy — MAPE today across forecasts vs actuals."""

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
    # Use most recent forecast_type='refined' per (asset, kind, hour) joined to actuals.
    q = text(
        """
        WITH refined AS (
            SELECT DISTINCT ON (asset_id, forecast_kind, hour)
                tenant_id, asset_id, forecast_kind, date, hour, value_mwh
            FROM ems.forecasts
            WHERE tenant_id = :tid
              AND date = :d
              AND forecast_type = 'refined'
            ORDER BY asset_id, forecast_kind, hour, issued_at DESC
        )
        SELECT r.forecast_kind,
               AVG(CASE WHEN a.actual_mwh > 0
                        THEN ABS(r.value_mwh - a.actual_mwh) / a.actual_mwh * 100
                        ELSE NULL END)::float AS mape_pct,
               COUNT(*) AS n
        FROM refined r
        JOIN ems.forecast_actuals a
          ON a.tenant_id = r.tenant_id
         AND a.asset_id = r.asset_id
         AND a.forecast_kind = r.forecast_kind
         AND a.date = r.date
         AND a.hour = r.hour
        GROUP BY r.forecast_kind
        ORDER BY mape_pct ASC NULLS LAST
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    series = [
        {"kind": r["forecast_kind"], "mape": float(r["mape_pct"] or 0), "n": int(r["n"])}
        for r in rows
    ]
    return {
        "date_ua": date_ua(d),
        "series": series,
        "overall": (
            sum(s["mape"] for s in series) / len(series) if series else None
        ),
        "_evidence": [
            evidence_row(
                "ems.forecasts × ems.forecast_actuals",
                columns=["value_mwh", "actual_mwh"],
                ui_link=f"/producer/prognozy?date={d.isoformat()}",
                label=f"Прогнози vs факт за {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    d = slots["date_ua"]
    series = slots["series"]
    if not series or slots["overall"] is None:
        return f"За {d} даних для розрахунку MAPE не вистачає (ems.forecasts vs ems.forecast_actuals)."
    parts = ", ".join(
        f"{s['kind']}: {fmt_num(s['mape'])}%" for s in series
    )
    return (
        f"Точність прогнозу за {d} (MAPE) — в середньому {fmt_num(slots['overall'])}%. "
        f"По типах: {parts}. "
        f"Джерело: ems.forecasts × ems.forecast_actuals."
    )
