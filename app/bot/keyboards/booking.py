import calendar
from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.schedule import WEEKDAY_KEYS
from app.bot.keyboards.work_days import month_label_short
from app.bot.utils.format import format_time
from app.domain.models import Service, TimeWindow


class ServiceCallback(CallbackData, prefix="svc"):
    service_id: int


class MonthCallback(CallbackData, prefix="bmon"):
    year: int
    month: int


class DayCallback(CallbackData, prefix="bday"):
    value: str


class DayPadCallback(CallbackData, prefix="bpad"):
    n: int = 0


class BookingNavCallback(CallbackData, prefix="bk"):
    action: str


class WindowCallback(CallbackData, prefix="win", sep="|"):
    starts_at: str  # ISO datetime UTC


def _nav_row(
        i18n: dict[str, str],
        *,
        with_back: bool,
) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    if with_back:
        buttons.append(
            InlineKeyboardButton(
                text=i18n.get("book_back_button"),
                callback_data=BookingNavCallback(action="back").pack(),
            )
        )
    buttons.append(
        InlineKeyboardButton(
            text=i18n.get("book_cancel_button"),
            callback_data=BookingNavCallback(action="cancel").pack(),
        )
    )
    return buttons


def get_services_kb(
        *,
        services: list[Service],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for service in services:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=i18n.get("service_button").format(
                        title=service.title,
                        duration=service.duration_minutes,
                    ),
                    callback_data=ServiceCallback(service_id=service.id).pack(),
                )
            ]
        )
    buttons.append(_nav_row(i18n, with_back=False))
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_months_kb(
        *,
        months: list[tuple[int, int]],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for year, month in months:
        row.append(
            InlineKeyboardButton(
                text=month_label_short(year, month, i18n),
                callback_data=MonthCallback(year=year, month=month).pack(),
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(_nav_row(i18n, with_back=True))
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_day_calendar_kb(
        *,
        year: int,
        month: int,
        open_days: set[int],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    """Month grid; only ``open_days`` (day-of-month) are selectable."""
    buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=i18n.get(WEEKDAY_KEYS[weekday]),
                callback_data=DayPadCallback(n=weekday).pack(),
            )
            for weekday in range(1, 8)
        ]
    ]

    cal = calendar.Calendar(firstweekday=0)  # Monday
    for week in cal.monthdayscalendar(year, month):
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0 or day not in open_days:
                row.append(
                    InlineKeyboardButton(
                        text=" " if day == 0 else "·",
                        callback_data=DayPadCallback(n=day).pack(),
                    )
                )
                continue
            row.append(
                InlineKeyboardButton(
                    text=str(day),
                    callback_data=DayCallback(
                        value=date(year, month, day).isoformat(),
                    ).pack(),
                )
            )
        buttons.append(row)

    buttons.append(_nav_row(i18n, with_back=True))
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_kb(*, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("book_confirm_button"),
                    callback_data=BookingNavCallback(action="confirm").pack(),
                )
            ],
            _nav_row(i18n, with_back=True),
        ]
    )


def get_windows_kb(
        *,
        windows: list[TimeWindow],
        i18n: dict[str, str],
        bot_timezone: str,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for window in windows:
        row.append(
            InlineKeyboardButton(
                text=format_time(window.starts_at, bot_timezone),
                callback_data=WindowCallback(
                    starts_at=window.starts_at.isoformat(),
                ).pack(),
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(_nav_row(i18n, with_back=True))
    return InlineKeyboardMarkup(inline_keyboard=buttons)
