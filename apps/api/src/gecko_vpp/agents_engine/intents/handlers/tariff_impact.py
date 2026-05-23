"""tariff_impact — what tariff bands cost over the last 30 days."""

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
    # Approximate tariff bands from RDN price percentiles for the tenant's BZN.
    q = text(
        """
        SELECT AVG(price_uah_mwh)::float AS avg_p,
               percentile_cont(0.10) WITHIN GROUP (ORDER BY price_uah_mwh)::float AS p10,
               percentile_cont(0.90) WITHIN GROUP (ORDER BY price_uah_mwh)::float AS p90,
               COUNT(*) AS n
        FROM market.rdn_prices
        WHERE tenant_id = :tid
          AND date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
        """
    )
    r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()

    # Tenant's consumption over the same window.
    q2 = text(
        """
        SELECT SUM(ABS(LEAST(t.active_power_mw, 0)))::float AS load_mwh
        FROM dispatch.telemetry t
        JOIN core.assets a ON a.id = t.asset_id
        WHERE t.tenant_id = :tid
          AND t.date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
          AND a.asset_class IN ('Споживач','АктСпож')
        """
    )
    r2 = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().first()
    load = float(r2["load_mwh"] or 0) if r2 else 0.0
    avg = float(r["avg_p"] or 0) if r else 0
    p10 = float(r["p10"] or 0) if r else 0
    p90 = float(r["p90"] or 0) if r else 0

    return {
        "date_ua": date_ua(d),
        "avg_price": avg,
        "off_peak_price": p10,
        "peak_price": p90,
        "load_mwh": load,
        "total_at_avg": load * avg,
        "savings_if_shift": load * 0.2 * (p90 - p10),  # shift 20% to off-peak
        "_evidence": [
            evidence_row(
                "market.rdn_prices + dispatch.telemetry",
                columns=["price_uah_mwh", "active_power_mw"],
                ui_link=f"/c-i/rynok?date={d.isoformat()}",
                label=f"Тариф vs споживання 30 днів до {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    if slots["load_mwh"] == 0:
        return f"За 30 днів до {slots['date_ua']} даних про споживання не знайдено."
    return (
        f"Вплив тарифу на 30 днів до {slots['date_ua']}: "
        f"середня ціна РДН {fmt_num(slots['avg_price'])} грн/МВт·год "
        f"(off-peak {fmt_num(slots['off_peak_price'])}, "
        f"peak {fmt_num(slots['peak_price'])}). "
        f"Споживання {fmt_num(slots['load_mwh'])} МВт·год, оплата за середнім тарифом ≈ {fmt_uah(slots['total_at_avg'])}. "
        f"Перенесення 20% навантаження з піка в off-peak зекономить {fmt_uah(slots['savings_if_shift'])}/місяць. "
        f"Джерело: market.rdn_prices + dispatch.telemetry."
    )
