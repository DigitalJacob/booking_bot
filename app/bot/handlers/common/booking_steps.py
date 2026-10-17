"""Shared booking funnel screens (client self-book and master book-for-client)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards.booking import (
    get_confirm_kb,
    get_day_calendar_kb,
    get_months_kb,
    get_services_kb,
    get_windows_kb,
)
from app.bot.keyboards.work_days import month_label
from app.bot.utils.format import format_dt, to_local
from app.bot.utils.format import format_price as _format_price
from app.domain.models import Service, TimeWindow


def format_price(price: Decimal | None, i18n: dict[str, str]) -> str:
    return _format_price(price, i18n, empty_key="book_price_empty")


def unique_days(windows: list[TimeWindow], bot_timezone: str) -> list[date]:
    return sorted({to_local(window.starts_at, bot_timezone).date() for window in windows})


def windows_on_day(
    windows: list[TimeWindow],
    day: date,
    bot_timezone: str,
) -> list[TimeWindow]:
    return [window for window in windows if to_local(window.starts_at, bot_timezone).date() == day]


def days_in_month(days: list[date], year: int, month: int) -> list[date]:
    return [day for day in days if day.year == year and day.month == month]


def bookable_months(
    open_months: list[tuple[int, int]],
    days: list[date],
) -> list[tuple[int, int]]:
    """Open schedule months that still have at least one free slot day."""
    day_months = {(day.year, day.month) for day in days}
    return [month for month in open_months if month in day_months]


async def show_services(
    *,
    message: Message,
    services: list[Service],
    i18n: dict[str, str],
    edit: bool,
) -> None:
    text = i18n.get("book_choose_service")
    kb = get_services_kb(services=services, i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def show_months(
    *,
    message: Message,
    months: list[tuple[int, int]],
    i18n: dict[str, str],
) -> None:
    await message.edit_text(
        text=i18n.get("book_choose_month"),
        reply_markup=get_months_kb(months=months, i18n=i18n),
    )


async def show_days(
    *,
    message: Message,
    year: int,
    month: int,
    days: list[date],
    i18n: dict[str, str],
) -> None:
    await message.edit_text(
        text=i18n.get("book_choose_day").format(
            month=month_label(year, month, i18n),
        ),
        reply_markup=get_day_calendar_kb(
            year=year,
            month=month,
            open_days={day.day for day in days},
            i18n=i18n,
        ),
    )


async def show_windows(
    *,
    message: Message,
    windows: list[TimeWindow],
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await message.edit_text(
        text=i18n.get("book_choose_window"),
        reply_markup=get_windows_kb(
            windows=windows,
            i18n=i18n,
            bot_timezone=bot_timezone,
        ),
    )


async def show_confirm(
    *,
    message: Message,
    service: Service,
    starts_at: datetime,
    i18n: dict[str, str],
    bot_timezone: str,
    header: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
    confirm_key: str = "book_confirm",
) -> None:
    text = i18n.get(confirm_key).format(
        title=service.title,
        when=format_dt(starts_at, bot_timezone),
        duration=service.duration_minutes,
        price=format_price(service.price, i18n),
    )
    if header:
        text = f"{header}\n\n{text}"
    await message.edit_text(
        text=text,
        reply_markup=reply_markup or get_confirm_kb(i18n=i18n),
    )
