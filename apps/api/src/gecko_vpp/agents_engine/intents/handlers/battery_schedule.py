"""battery_schedule — when to charge / discharge based on today's RDN prices."""

from __future__ import annotations

from datetime import timedelta
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
        SELECT hour, price_uah_mwh::float AS p
        FROM market.rdn_prices
        WHERE tenant_id = :tid AND date = :d
        ORDER BY hour
        """
    )
    rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    if not rows:
        d = d - timedelta(days=1)
        rows = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().all()
    prices = sorted([{"h": int(r["hour"]), "p": float(r["p"])} for r in rows], key=lambda x: x["p"])
    cheap = sorted(prices[:3], key=lambda x: x["h"])
    peak = sorted(prices[-3:], key=lambda x: x["h"])

    # Current SOC of any UZE.
    q2 = text(
        """
        SELECT AVG(soc_pct)::float AS soc
        FROM dispatch.telemetry t
        JOIN core.assets a ON a.id = t.asset_id
        WHERE t.tenant_id = :tid
          AND t.date = :d
          AND a.asset_class = 'УЗЕ'
          AND t.soc_pct IS NOT NULL
        """
    )
    r2 = (await session.execute(q2, {"tid": tenant_id, "d": d})).mappings().first()
    soc = float(r2["soc"]) if r2 and r2["soc"] is not None else None

    return {
        "date_ua": date_ua(d),
        "cheap": cheap,
        "peak": peak,
        "soc": soc,
        "_evidence": [
            evidence_row(
                "market.rdn_prices + dispatch.telemetry.soc_pct",
                columns=["price_uah_mwh", "hour", "soc_pct"],
                ui_link=f"/storage/uze?date={d.isoformat()}",
                label=f"РДН + SOC {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    if not slots["cheap"] or not slots["peak"]:
        return f"Не знайдено даних РДН на {slots['date_ua']} для розкладу батареї."
    cheap_avg = sum(c["p"] for c in slots["cheap"]) / len(slots["cheap"])
    peak_avg = sum(p["p"] for p in slots["peak"]) / len(slots["peak"])
    cheap_range = f"{slots['cheap'][0]['h']}:00–{slots['cheap'][-1]['h'] + 1}:00"
    peak_range = f"{slots['peak'][0]['h']}:00–{slots['peak'][-1]['h'] + 1}:00"
    soc_str = f"{fmt_num(slots['soc'], 0)}%" if slots["soc"] is not None else "невідомо"
    return (
        f"Графік батареї на {slots['date_ua']}: "
        f"ЗАРЯД у дешеві години {cheap_range} (середня ціна {fmt_num(cheap_avg)} грн/МВт·год). "
        f"РОЗРЯД у пікові години {peak_range} (середня ціна {fmt_num(peak_avg)} грн/МВт·год). "
        f"Спред {fmt_num(peak_avg - cheap_avg)} грн/МВт·год. "
        f"Поточний SOC — {soc_str}. "
        f"Джерело: market.rdn_prices + dispatch.telemetry.soc_pct."
    )
