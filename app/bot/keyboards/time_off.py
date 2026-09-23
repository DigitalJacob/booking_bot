from datetime import timedelta, time

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.utils.format import to_local
from app.domain.models import TimeOff


class TimeOffNavCallback(CallbackData, prefix="toff"):
    action: str  # add | close | cancel


class TimeOffDeleteCallback(CallbackData, prefix="toffdel"):
    time_off_id: int


class TimeOffConfirmCallback(CallbackData, prefix="toffcfm"):
    time_off_id: int
    action: str


def format_time_off_line(
        row: TimeOff,
        i18n: dict[str, str],
        bot_timezone: str,
) -> str:
    start_local = to_local(row.starts_at, bot_timezone)
    end_local = to_local(row.ends_at, bot_timezone)
    # full-day half-open: end is next midnight → show last inclusive day
    end_display = end_local
    if end_local.time() == time.min:
        end_display = end_local - timedelta(seconds=1)

    start_d = start_local.strftime("%d.%m.%Y")
    end_d = end_display.strftime("%d.%m.%Y")
    if start_d == end_d:
        when = start_d
    else:
        when = f"{start_d}-{end_d}"

    note = f" - {row.note}" if row.note else ""
    return i18n.get("time_off_list_item").format(when=when, note=note)


def get_time_off_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_cancel_button"),
                    callback_data=TimeOffNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_time_off_list_kb(
        *,
        rows: list[TimeOff],
        i18n: dict[str, str],
        bot_timezone: str,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for row in rows:
        label = i18n.get("time_off_delete_button").format(
            item=format_time_off_line(row, i18n, bot_timezone).lstrip("• ").strip(),
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=TimeOffDeleteCallback(
                        time_off_id=row.id,
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("time_off_add_button"),
                callback_data=TimeOffNavCallback(action="add").pack(),
            ),
            InlineKeyboardButton(
                text=i18n.get("time_off_close_button"),
                callback_data=TimeOffNavCallback(action="close").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_off_confirm_delete_kb(
        *,
        time_off_id: int,
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_confirm_yes"),
                    callback_data=TimeOffConfirmCallback(
                        time_off_id=time_off_id,
                        action="yes",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=i18n.get("time_off_confirm_no"),
                    callback_data=TimeOffConfirmCallback(
                        time_off_id=time_off_id,
                        action="no",
                    ).pack(),
                ),
            ]
        ]
    )
