from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import WorkingHours


WEEKDAY_KEYS = {
    1: "schedule_weekday_1",
    2: "schedule_weekday_2",
    3: "schedule_weekday_3",
    4: "schedule_weekday_4",
    5: "schedule_weekday_5",
    6: "schedule_weekday_6",
    7: "schedule_weekday_7",
}


class ScheduleNavCallback(CallbackData, prefix="sch"):
    action: str  # edit | view | close | add | save | back | cancel


class ScheduleWeekdayCallback(CallbackData, prefix="schwd"):
    weekday: int


class ScheduleDeleteCallback(CallbackData, prefix="schdel"):
    working_hours_id: int


class ScheduleConfirmCallback(CallbackData, prefix="schcfm"):
    working_hours_id: int
    action: str  # yes | no


def format_interval_line(
        row: WorkingHours,
        i18n: dict[str, str],
) -> str:
    weekday = i18n.get(WEEKDAY_KEYS[row.weekday])
    starts = row.starts_time.strftime("%H:%M")
    ends = row.ends_time.strftime("%H:%M")
    return i18n.get("schedule_list_item").format(
        weekday=weekday,
        starts=starts,
        ends=ends,
    )


def get_schedule_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("schedule_cancel_button"),
                    callback_data=ScheduleNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_schedule_view_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    """Read-only schedule: edit entry + back to hub schedule section."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("schedule_edit_button"),
                    callback_data=ScheduleNavCallback(action="edit").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("schedule_back_button"),
                    callback_data=ScheduleNavCallback(action="close").pack(),
                )
            ],
        ]
    )


def get_schedule_edit_kb(
        *,
        rows: list[WorkingHours],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    """Edit mode: delete rows, add interval, back to view."""
    buttons: list[list[InlineKeyboardButton]] = []
    for row in rows:
        label = i18n.get("schedule_delete_button").format(
            item=format_interval_line(row, i18n).lstrip("• ").strip(),
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=ScheduleDeleteCallback(
                        working_hours_id=row.id,
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("schedule_add_button"),
                callback_data=ScheduleNavCallback(action="add").pack(),
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("schedule_back_button"),
                callback_data=ScheduleNavCallback(action="view").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_schedule_confirm_delete_kb(
        *,
        working_hours_id: int,
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("schedule_confirm_yes"),
                    callback_data=ScheduleConfirmCallback(
                        working_hours_id=working_hours_id,
                        action="yes",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=i18n.get("schedule_confirm_no"),
                    callback_data=ScheduleConfirmCallback(
                        working_hours_id=working_hours_id,
                        action="no",
                    ).pack(),
                ),
            ]
        ]
    )


def get_weekdays_kb(
        *,
        selected: set[int],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for weekday in range(1, 8):
        mark = "✓ " if weekday in selected else ""
        label = mark + i18n.get(WEEKDAY_KEYS[weekday])
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=ScheduleWeekdayCallback(weekday=weekday).pack(),
            )
        )
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("schedule_save_button"),
                callback_data=ScheduleNavCallback(action="save").pack(),
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("schedule_back_button"),
                callback_data=ScheduleNavCallback(action="back").pack(),
            ),
            InlineKeyboardButton(
                text=i18n.get("schedule_cancel_button"),
                callback_data=ScheduleNavCallback(action="cancel").pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
