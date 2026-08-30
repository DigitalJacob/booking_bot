from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import Service, Slot


class ServiceCallback(CallbackData, prefix="svc"):
    service_id: int


class DayCallback(CallbackData, prefix="bday"):
    value: str


class SlotCallback(CallbackData, prefix="slot"):
    slot_id: int


class BookingNavCallback(CallbackData, prefix="bk"):
    action: str


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


def get_days_kb(
        *,
        days: list[date],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for day in days:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=day.strftime("%d.%m.%Y"),
                    callback_data=DayCallback(value=day.isoformat()).pack(),
                )
            ]
        )
    buttons.append(_nav_row(i18n, with_back=True))
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_slots_kb(
        *,
        slots: list[Slot],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for slot in slots:
        row.append(
            InlineKeyboardButton(
                text=slot.starts_at.strftime("%H:%M"),
                callback_data=SlotCallback(slot_id=slot.id).pack(),
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
