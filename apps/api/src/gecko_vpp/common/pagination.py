"""Pagination + date-range query helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from fastapi import Query


# Synth window per .env — defaults align with seeded data.
SYNTH_DATE_START = date(2026, 4, 23)
SYNTH_DATE_END = date(2026, 5, 23)


@dataclass
class Pagination:
    page: int
    per_page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


def pagination_dep(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> Pagination:
    return Pagination(page=page, per_page=per_page)


@dataclass
class DateRange:
    date_start: date
    date_end: date


def date_range_dep(
    date_start: date | None = Query(None),
    date_end: date | None = Query(None),
) -> DateRange:
    """Default to last 7 days within the synth window if omitted."""
    if date_end is None:
        date_end = SYNTH_DATE_END
    if date_start is None:
        date_start = date_end - timedelta(days=6)
    return DateRange(date_start=date_start, date_end=date_end)


def pagination_meta(p: Pagination, total: int) -> dict[str, Any]:
    total_pages = (total + p.per_page - 1) // p.per_page if p.per_page else 1
    return {
        "pagination": {
            "page": p.page,
            "per_page": p.per_page,
            "total": total,
            "total_pages": total_pages,
        }
    }
