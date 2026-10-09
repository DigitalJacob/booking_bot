from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.hub import HubCallback
from app.domain.enums import ReminderKind


class ReminderCallback(CallbackData, prefix="remind"):
    action: str  # cancel
    appointment_id: int
    kind: str


def get_reminder_kb(
        *,
        i18n: dict[str, str],
        appointment_id: int,
        kind: ReminderKind,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("reminder_ok_button"),
                    callback_data=HubCallback(action="dismiss").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("reminder_cancel_button"),
                    callback_data=ReminderCallback(
                        action="cancel",
                        appointment_id=appointment_id,
                        kind=kind.value,
                    ).pack(),
                )
            ],
        ]
    )
