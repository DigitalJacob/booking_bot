from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models.appointment import Appointment


class ClientAppointmentCallback(CallbackData, prefix="capt"):
    action: str  # open | cancel | back | close
    appointment_id: int = 0


def get_my_bookings_list_kb(
        *,
        appointments: list[Appointment],
        labels: dict[int, str],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for appointment in appointments:
        rows.append(
            [
                InlineKeyboardButton(
                    text=labels.get(appointment.id, str(appointment.id)),
                    callback_data=ClientAppointmentCallback(
                        action="open",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("my_bookings_close_button"),
                callback_data=ClientAppointmentCallback(action="close").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_my_booking_card_kb(
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
                    text=i18n.get("my_bookings_back_button"),
                    callback_data=ClientAppointmentCallback(
                        action="back",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            ],
        ]
    )
