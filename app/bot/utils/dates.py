"""Shared helpers for date/time tokens used in FSM and callbacks."""

from __future__ import annotations

from datetime import datetime, time


def parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def parse_year_month(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    try:
        year_s, month_s = raw.split("-", 1)
        year, month = int(year_s), int(month_s)
    except ValueError:
        return None
    if not 1 <= month <= 12:
        return None
    return year, month


def format_year_month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1
