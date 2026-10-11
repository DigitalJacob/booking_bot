"""Shared helpers and FSM keys for master time off / breaks."""

from __future__ import annotations

from datetime import date, datetime, time

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards.time_off import get_time_off_cancel_kb
from app.bot.utils.format import get_zone
from app.bot.utils.hub_nav import show_hub_prompt

MONTH_KEY = "toff_month"  # YYYY-MM
MAX_WARN_LINES = 8
PENDING_STARTS_KEY = "toff_starts_at"
PENDING_ENDS_KEY = "toff_ends_at"
PENDING_WHEN_KEY = "toff_when"
PENDING_KIND_KEY = "toff_kind"  # hours | days


def is_breaks_mode(schedule_mode: str) -> bool:
    return schedule_mode == "monthly"


def list_from_dt(bot_timezone: str) -> datetime:
    zone = get_zone(bot_timezone)
    now_local = datetime.now(zone)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def today_local(bot_timezone: str) -> date:
    return list_from_dt(bot_timezone).date()


def parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def format_day_range(starts: date, ends: date) -> str:
    start_d = starts.strftime("%d.%m.%Y")
    end_d = ends.strftime("%d.%m.%Y")
    if start_d == end_d:
        return start_d
    return f"{start_d}-{end_d}"


def format_hours_when(day: date, starts: time, ends: time) -> str:
    return f"{day.strftime('%d.%m.%Y')} {starts.strftime('%H:%M')}–{ends.strftime('%H:%M')}"


async def show_time_off_prompt(
    *,
    message: Message,
    state: FSMContext,
    text: str,
    i18n: dict[str, str],
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Show FSM prompt on the tapped hub message / sticky when possible."""
    kb = reply_markup if reply_markup is not None else get_time_off_cancel_kb(i18n)
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=kb,
    )
