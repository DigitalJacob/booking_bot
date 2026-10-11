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
