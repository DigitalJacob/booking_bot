from datetime import timedelta, time

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.utils.format import to_local
from app.domain.models import TimeOff


class TimeOffNavCallback(CallbackData, prefix="toff"):
    action: str  # add | close | cancel


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


def get_time_off_list_kb(*, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_add_button"),
                    callback_data=TimeOffNavCallback(action="add").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_close_button"),
                    callback_data=TimeOffNavCallback(action="close").pack(),
                )
            ],
        ]
    )
