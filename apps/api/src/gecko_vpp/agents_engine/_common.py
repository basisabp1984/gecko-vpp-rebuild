"""Common helpers for intent handlers."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Any


KYIV_TZ = timezone(timedelta(hours=3))


def synth_today(now: datetime | None = None) -> date:
    """The 'today' the synthetic dataset uses. Fixed window end = 2026-05-23.

    Reads from config; falls back to 2026-05-23 if config can't be loaded.
    """
    try:
        from gecko_vpp.config import get_settings
        s = get_settings()
        return date.fromisoformat(s.synth_date_end)
    except Exception:
        return date(2026, 5, 23)


def synth_now() -> datetime:
    """A 'now' anchored inside the synth window for deterministic queries."""
    d = synth_today()
    return datetime(d.year, d.month, d.day, 10, 0, tzinfo=KYIV_TZ)


def date_ua(d: date | datetime) -> str:
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d.%m.%Y")


def fmt_num(v: Any, digits: int = 1) -> str:
    """Ukrainian-style number: '1 234,5' for 1234.5."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    s = f"{f:,.{digits}f}"
    # Replace thin space and dot per UA convention.
    return s.replace(",", " ").replace(".", ",")


def fmt_uah(v: Any, digits: int = 0) -> str:
    if v is None:
        return "—"
    return f"{fmt_num(v, digits)} грн"


def to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def evidence_row(
    table: str,
    row_id: Any = None,
    columns: list[str] | None = None,
    ui_link: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """Build a single evidence chip in canonical shape."""
    out: dict[str, Any] = {"table": table}
    if row_id is not None:
        out["row_id"] = str(row_id)
    if columns:
        out["columns_used"] = list(columns)
    if ui_link:
        out["ui_link"] = ui_link
    if label:
        out["label"] = label
    return out
