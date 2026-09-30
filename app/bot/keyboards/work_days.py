import calendar

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.schedule import WEEKDAY_KEYS


class WorkDaysNavCallback(CallbackData, prefix="wd"):
    action: str  # close|cancel|next|back|confirm_yes|confirm_no|save_anyway|summary


class WorkDaysMonthCallback(CallbackData, prefix="wdm"):
    year: int
    month: int


class WorkDaysDayCallback(CallbackData, prefix="wdd"):
    day: int  # day of month 1..31


class WorkDaysPadCallback(CallbackData, prefix="wdp"):
    n: int = 0


def month_label(year: int, month: int, i18n: dict[str, str]) -> str:
    name = i18n.get(f"work_days_month_{month}")
    return f"{name} {year}"


def get_work_days_months_kb(
        *,
        months: list[tuple[int, int]],
        marked: set[tuple[int, int]],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for year, month in months:
        mark = "✓ " if (year, month) in marked else ""
        buttons.append(
            [
                InlineKeyboardButton(
                    text=mark + month_label(year, month, i18n),
                    callback_data=WorkDaysMonthCallback(
                        year=year,
                        month=month,
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("work_days_back_button"),
                callback_data=WorkDaysNavCallback(action="close").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_work_days_calendar_kb(
        *,
        year: int,
        month: int,
        selected_days: set[int],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=i18n.get(WEEKDAY_KEYS[weekday]),
                callback_data=WorkDaysPadCallback(n=weekday).pack(),
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
                        callback_data=WorkDaysPadCallback(n=0).pack(),
                    )
                )
                continue
            mark = "✓" if day in selected_days else str(day)
            row.append(
                InlineKeyboardButton(
                    text=mark,
                    callback_data=WorkDaysDayCallback(day=day).pack(),
                )
            )
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("work_days_summary_button"),
                callback_data=WorkDaysNavCallback(action="summary").pack(),
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("work_days_next_button"),
                callback_data=WorkDaysNavCallback(action="next").pack(),
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("work_days_back_button"),
                callback_data=WorkDaysNavCallback(action="back").pack(),
            ),
            InlineKeyboardButton(
                text=i18n.get("work_days_cancel_button"),
                callback_data=WorkDaysNavCallback(action="cancel").pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_work_days_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("work_days_cancel_button"),
                    callback_data=WorkDaysNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_work_days_confirm_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("work_days_confirm_yes"),
                    callback_data=WorkDaysNavCallback(
                        action="confirm_yes",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=i18n.get("work_days_confirm_no"),
                    callback_data=WorkDaysNavCallback(
                        action="confirm_no",
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("work_days_cancel_button"),
                    callback_data=WorkDaysNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_work_days_warn_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("work_days_warn_anyway"),
                    callback_data=WorkDaysNavCallback(
                        action="save_anyway",
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("work_days_warn_back"),
                    callback_data=WorkDaysNavCallback(
                        action="confirm_no",
                    ).pack(),
                )
            ],
        ]
    )
