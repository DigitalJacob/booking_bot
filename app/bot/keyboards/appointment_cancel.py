from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AppointmentCancelCallback(CallbackData, prefix="acancel"):
    action: str  # yes | no | skip_reason
    appointment_id: int
    source: str
    mode: str = "cancel"  # cancel | decline
    reminder_kind: str = ""


def get_appointment_cancel_confirm_kb(
        *,
        i18n: dict[str, str],
        appointment_id: int,
        source: str,
        mode: str = "cancel",
        reminder_kind: str = "",
) -> InlineKeyboardMarkup:
    yes_key = (
        "decline_yes_button" if mode == "decline" else "cancel_yes_button"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get(yes_key),
                    callback_data=AppointmentCancelCallback(
                        action="yes",
                        appointment_id=appointment_id,
                        source=source,
                        mode=mode,
                        reminder_kind=reminder_kind,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("cancel_no_button"),
                    callback_data=AppointmentCancelCallback(
                        action="no",
                        appointment_id=appointment_id,
                        source=source,
                        mode=mode,
                        reminder_kind=reminder_kind,
                    ).pack(),
                )
            ],
        ]
    )


def get_appointment_cancel_reason_kb(
        *,
        i18n: dict[str, str],
        appointment_id: int,
        source: str,
        mode: str = "cancel",
        reminder_kind: str = "",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("cancel_skip_reason_button"),
                    callback_data=AppointmentCancelCallback(
                        action="skip_reason",
                        appointment_id=appointment_id,
                        source=source,
                        mode=mode,
                        reminder_kind=reminder_kind,
                    ).pack(),
                )
            ],
        ]
    )
