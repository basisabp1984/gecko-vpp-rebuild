"""revenue_breakdown — last-30-day revenue by channel."""

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
    # RDN settlement_amount (proxy via bids.settlement_amount), VDR price*volume,
    # BR settlement_uah, ancillary revenue_energy_uah + offers.revenue_capacity_uah.
    qs = {
        "rdn": text(
            """
            SELECT COALESCE(SUM(settlement_amount), 0)::float AS v
            FROM market.bids
            WHERE tenant_id = :tid
              AND market = 'RDN'
              AND delivery_date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
              AND settlement_amount IS NOT NULL
            """
        ),
        "vdr": text(
            """
            SELECT COALESCE(SUM(volume_mwh * price_uah_mwh
                * CASE WHEN side = 'SELL' THEN 1 ELSE -1 END), 0)::float AS v
            FROM market.vdr_trades
            WHERE tenant_id = :tid
              AND delivery_date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
            """
        ),
        "br": text(
            """
            SELECT COALESCE(SUM(settlement_uah), 0)::float AS v
            FROM market.br_settlements
            WHERE tenant_id = :tid
              AND date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
            """
        ),
        "anc_capacity": text(
            """
            SELECT COALESCE(SUM(revenue_capacity_uah), 0)::float AS v
            FROM market.ancillary_offers
            WHERE tenant_id = :tid
              AND date BETWEEN (CAST(:d AS date) - INTERVAL '29 days') AND :d
            """
        ),
        "anc_energy": text(
            """
            SELECT COALESCE(SUM(revenue_energy_uah), 0)::float AS v
            FROM market.ancillary_activations
            WHERE tenant_id = :tid
              AND started_at >= (CAST(:d AS date) - INTERVAL '29 days')
            """
        ),
    }
    vals: dict[str, float] = {}
    for k, q in qs.items():
        r = (await session.execute(q, {"tid": tenant_id, "d": d})).mappings().first()
        vals[k] = float(r["v"] or 0) if r else 0.0
    anc_total = vals["anc_capacity"] + vals["anc_energy"]
    breakdown = {
        "РДН": vals["rdn"],
        "ВДР": vals["vdr"],
        "БР": vals["br"],
        "Допоміжні послуги": anc_total,
    }
    total = sum(breakdown.values())
    return {
        "date_ua": date_ua(d),
        "breakdown": breakdown,
        "total": total,
        "_evidence": [
            evidence_row(
                "market.bids + market.vdr_trades + market.br_settlements + market.ancillary_*",
                columns=["settlement_amount", "settlement_uah", "revenue_*"],
                ui_link="/producer/rynok",
                label=f"Виторг за 30 днів до {date_ua(d)}",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    bd = slots["breakdown"]
    total = slots["total"]
    if total == 0:
        return f"За 30 днів до {slots['date_ua']} виторгу не зафіксовано (market.*)."
    lines = []
    for ch, v in sorted(bd.items(), key=lambda x: -x[1]):
        share = (v / total * 100) if total else 0
        lines.append(f"{ch}: {fmt_uah(v)} ({fmt_num(share, 1)}%)")
    return (
        f"Виторг за 30 днів до {slots['date_ua']} — {fmt_uah(total)} разом. "
        f"По каналах: " + "; ".join(lines) + ". "
        f"Джерело: market.bids, market.vdr_trades, market.br_settlements, market.ancillary_*."
    )
