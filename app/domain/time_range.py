"""Half-open datetime interval helpers shared by domain services."""

from __future__ import annotations

from datetime import UTC, datetime


def as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def intervals_overlap(
    start: datetime,
    end: datetime,
    other_start: datetime,
    other_end: datetime,
) -> bool:
    """True when [start, end) and [other_start, other_end) overlap."""
    return start < other_end and end > other_start
