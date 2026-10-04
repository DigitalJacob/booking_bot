from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.hub import HubCallback
from app.domain.enums import ReminderKind


class ReminderCallback(CallbackData, prefix="remind"):
    action: str  # cancel | cancel_yes | cancel_no | skip_reason
    appointment_id: int
    kind: str


def get_reminder_kb(
        *,
        i18n: dict[str, str],
        appointment_id: int,
        kind: ReminderKind,
) -> InlineKeyboardMarkup:
    packed_kind = kind.value
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
                        kind=packed_kind,
                    ).pack(),
                )
            ],
        ]
    )


def get_reminder_cancel_confirm_kb(
        *,
        i18n: dict[str, str],
        appointment_id: int,
        kind: ReminderKind,
) -> InlineKeyboardMarkup:
    packed_kind = kind.value
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("reminder_cancel_yes_button"),
                    callback_data=ReminderCallback(
                        action="cancel_yes",
                        appointment_id=appointment_id,
                        kind=packed_kind,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("reminder_cancel_no_button"),
                    callback_data=ReminderCallback(
                        action="cancel_no",
                        appointment_id=appointment_id,
                        kind=packed_kind,
                    ).pack(),
                )
            ],
        ]
    )


def get_reminder_reason_kb(
        *,
        i18n: dict[str, str],
        appointment_id: int,
        kind: ReminderKind,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("reminder_skip_reason_button"),
                    callback_data=ReminderCallback(
                        action="skip_reason",
                        appointment_id=appointment_id,
                        kind=kind.value,
                    ).pack(),
                )
            ],
        ]
    )
