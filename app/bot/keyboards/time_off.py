import calendar
from datetime import date, time, timedelta

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.schedule import WEEKDAY_KEYS
from app.bot.utils.format import to_local
from app.domain.models import TimeOff


class TimeOffNavCallback(CallbackData, prefix="toff"):
    action: str  # close | add | cancel | days | hours | month_* | save_anyway | warn_back


class TimeOffDayCallback(CallbackData, prefix="toffday"):
    value: str  # YYYY-MM-DD


class TimeOffPadCallback(CallbackData, prefix="toffpad"):
    n: int = 0


class TimeOffDeleteCallback(CallbackData, prefix="toffdel"):
    time_off_id: int


class TimeOffConfirmCallback(CallbackData, prefix="toffcfm"):
    time_off_id: int
    action: str


def _month_nav_row(
        *,
        i18n: dict[str, str],
        is_current_month: bool,
) -> list[InlineKeyboardButton]:
    nav: list[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text=i18n.get("time_off_month_prev"),
            callback_data=TimeOffNavCallback(action="month_prev").pack(),
        )
    ]
    if not is_current_month:
        nav.append(
            InlineKeyboardButton(
                text=i18n.get("time_off_month_current"),
                callback_data=TimeOffNavCallback(
                    action="month_current",
                ).pack(),
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=i18n.get("time_off_month_next"),
            callback_data=TimeOffNavCallback(action="month_next").pack(),
        )
    )
    return nav


def get_time_off_day_calendar_kb(
        *,
        year: int,
        month: int,
        open_days: set[int],
        i18n: dict[str, str],
        is_current_month: bool,
) -> InlineKeyboardMarkup:
    """Month grid; only ``open_days`` (work days) are selectable."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=i18n.get(WEEKDAY_KEYS[weekday]),
                callback_data=TimeOffPadCallback(n=weekday).pack(),
            )
            for weekday in range(1, 8)
        ]
    ]

    cal = calendar.Calendar(firstweekday=0)  # Monday
    for week in cal.monthdayscalendar(year, month):
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data=TimeOffPadCallback(n=0).pack(),
                    )
                )
                continue
            if day in open_days:
                row.append(
                    InlineKeyboardButton(
                        text=i18n.get("time_off_calendar_day_open").format(
                            day=day,
                        ),
                        callback_data=TimeOffDayCallback(
                            value=date(year, month, day).isoformat(),
                        ).pack(),
                    )
                )
                continue
            row.append(
                InlineKeyboardButton(
                    text=i18n.get("time_off_calendar_day").format(day=day),
                    callback_data=TimeOffPadCallback(n=day).pack(),
                )
            )
        rows.append(row)

    rows.append(_month_nav_row(i18n=i18n, is_current_month=is_current_month))
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("time_off_cancel_button"),
                callback_data=TimeOffNavCallback(action="cancel").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_time_off_line(
        row: TimeOff,
        i18n: dict[str, str],
        bot_timezone: str,
) -> str:
    start_local = to_local(row.starts_at, bot_timezone)
    end_local = to_local(row.ends_at, bot_timezone)

    is_full_day = (
        start_local.time() == time.min
        and end_local.time() == time.min
    )
    if is_full_day:
        # half-open: end is next midnight → show last inclusive day
        end_display = end_local - timedelta(seconds=1)
        start_d = start_local.strftime("%d.%m.%Y")
        end_d = end_display.strftime("%d.%m.%Y")
        when = start_d if start_d == end_d else f"{start_d}-{end_d}"
    else:
        day = start_local.strftime("%d.%m.%Y")
        starts = start_local.strftime("%H:%M")
        ends = end_local.strftime("%H:%M")
        when = f"{day} {starts}–{ends}"

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


def get_time_off_kind_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    """Choose full-day range vs hours in one day."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_kind_days_button"),
                    callback_data=TimeOffNavCallback(action="days").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_kind_hours_button"),
                    callback_data=TimeOffNavCallback(action="hours").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_cancel_button"),
                    callback_data=TimeOffNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_time_off_edit_kb(
        *,
        rows: list[TimeOff],
        i18n: dict[str, str],
        bot_timezone: str,
) -> InlineKeyboardMarkup:
    """List with delete/add; back returns to hub schedule section."""
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
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("time_off_back_button"),
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


def get_time_off_warn_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_warn_anyway"),
                    callback_data=TimeOffNavCallback(
                        action="save_anyway",
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("time_off_warn_back"),
                    callback_data=TimeOffNavCallback(
                        action="warn_back",
                    ).pack(),
                )
            ],
        ]
    )
