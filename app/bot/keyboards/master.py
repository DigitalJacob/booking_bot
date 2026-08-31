from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.enums import AppointmentStatus
from app.domain.models.appointment import Appointment


class MasterAppointmentCallback(CallbackData, prefix="mapt"):
    action: str
    appointment_id: int


def get_appointment_actions_kb(
        *,
        appointment: Appointment,
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    row: list[InlineKeyboardButton] = []
    if appointment.status == AppointmentStatus.PENDING:
        row.append(
            InlineKeyboardButton(
                text=i18n.get("master_confirm_button"),
                callback_data=MasterAppointmentCallback(
                    action="confirm",
                    appointment_id=appointment.id,
                ).pack(),
            )
        )
    if appointment.status in (
        AppointmentStatus.PENDING,
        AppointmentStatus.CONFIRMED,
    ):
        row.append(
            InlineKeyboardButton(
                text=i18n.get("master_cancel_button"),
                callback_data=MasterAppointmentCallback(
                    action="cancel",
                    appointment_id=appointment.id,
                ).pack(),
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])
