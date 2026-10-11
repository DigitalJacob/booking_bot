"""Shared helpers and constants for master work days."""

from __future__ import annotations

from datetime import date, time

MONTH_CHOICES = 12
MAX_WARN_LINES = 8


def format_hm(value: time) -> str:
    return value.strftime("%H:%M")


def format_day_list(values: list[str] | set[str]) -> str:
    days = sorted(date.fromisoformat(value) for value in values)
    return ", ".join(day.strftime("%d.%m") for day in days)


def day_sets(data: dict) -> tuple[set[str], set[str], set[str], set[str]]:
    current = set(data.get("wd_days") or [])
    initial = set(data.get("wd_days_initial") or [])
    removed = initial - current
    added = current - initial
    return current, initial, removed, added
