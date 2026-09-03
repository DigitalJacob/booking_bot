from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models.appointment import Appointment


class ClientAppointmentCallback(CallbackData, prefix="capt"):
    action: str
    appointment_id: int


def get_my_booking_actions_kb(
        *,
        appointment: Appointment,
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("my_bookings_cancel_button"),
                    callback_data=ClientAppointmentCallback(
                        action="cancel",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("my_bookings_close_button"),
                    callback_data=ClientAppointmentCallback(
                        action="close",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            ],
        ]
    )
