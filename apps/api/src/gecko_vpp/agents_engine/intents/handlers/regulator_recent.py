"""regulator_recent — recent regulator_events that affect this tenant."""

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
    # regulator_events is read-all, so no tenant filter needed for visibility.
    q = text(
        """
        SELECT id, issuer, act_type, act_number, issued_at, effective_at,
               title, category, severity, summary
        FROM regulatory.regulator_events
        WHERE issued_at >= (CAST(:d AS date) - INTERVAL '30 days')
        ORDER BY issued_at DESC, severity DESC
        LIMIT 5
        """
    )
    rows = (await session.execute(q, {"d": d})).mappings().all()
    events = [
        {
            "id": r["id"],
            "issuer": r["issuer"],
            "act_type": r["act_type"],
            "act_number": r["act_number"],
            "issued_at": r["issued_at"],
            "title": r["title"],
            "severity": r["severity"],
            "summary": r["summary"],
        }
        for r in rows
    ]
    return {
        "date_ua": date_ua(d),
        "events": events,
        "_evidence": [
            evidence_row(
                "regulatory.regulator_events",
                row_id=events[0]["id"] if events else None,
                columns=["issued_at", "severity", "title"],
                ui_link="/producer/spovishchennya",
                label="Регуляторні події (30 днів)",
            )
        ],
    }


def render(slots: dict[str, Any], persona: str) -> str:
    events = slots["events"]
    if not events:
        return (
            f"За останні 30 днів (до {slots['date_ua']}) регуляторних подій не зафіксовано. "
            "Джерело: regulatory.regulator_events."
        )
    lines = [
        f"{i + 1}) {e['issued_at'].strftime('%d.%m')} [{e['severity']}] "
        f"{e['issuer']}: {e['title']}"
        for i, e in enumerate(events[:3])
    ]
    return (
        "Останні регуляторні події:\n"
        + "\n".join(lines)
        + f"\nВсього за 30 днів: {len(events)}. Детальніше — /producer/spovishchennya. "
        + "Джерело: regulatory.regulator_events."
    )
