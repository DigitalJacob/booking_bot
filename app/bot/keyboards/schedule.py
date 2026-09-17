from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import WorkingHours


class ScheduleNavCallback(CallbackData, prefix="sch"):
    action: str  # add | close | save | back | cancel


WEEKDAY_KEYS = {
    1: "schedule_weekday_1",
    2: "schedule_weekday_2",
    3: "schedule_weekday_3",
    4: "schedule_weekday_4",
    5: "schedule_weekday_5",
    6: "schedule_weekday_6",
    7: "schedule_weekday_7",
}


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


def get_schedule_list_kb(*, i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("schedule_add_button"),
                    callback_data=ScheduleNavCallback(action="add").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("schedule_close_button"),
                    callback_data=ScheduleNavCallback(action="close").pack(),
                )
            ],
        ]
    )
