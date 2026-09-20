from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.schedule import WEEKDAY_KEYS
from app.bot.utils.format import format_time
from app.domain.models import Service, TimeWindow


class ServiceCallback(CallbackData, prefix="svc"):
    service_id: int


class DayCallback(CallbackData, prefix="bday"):
    value: str


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


def _format_day_button(day: date, i18n: dict[str, str]) -> str:
    weekday = i18n.get(WEEKDAY_KEYS[day.isoweekday()])
    return f"{weekday} {day.strftime('%d.%m')}"


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


def get_days_kb(
        *,
        days: list[date],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for day in days:
        row.append(
            InlineKeyboardButton(
                text=_format_day_button(day, i18n),
                callback_data=DayCallback(value=day.isoformat()).pack(),
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
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
