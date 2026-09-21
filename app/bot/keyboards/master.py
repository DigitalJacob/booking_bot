from datetime import datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.hub import HubCallback
from app.domain.enums import AppointmentStatus
from app.domain.models.appointment import Appointment


class MasterAppointmentCallback(CallbackData, prefix="mapt"):
    action: str
    appointment_id: int


def is_slot_past(
        *,
        slot_ends_at: datetime | None,
        now: datetime,
) -> bool:
    if slot_ends_at is None:
        return False
    return slot_ends_at <= now


def get_appointment_actions_kb(
        *,
        appointment: Appointment,
        i18n: dict[str, str],
        now: datetime | None = None,
        slot_ends_at: datetime | None = None,
        dismiss: bool = False,
) -> InlineKeyboardMarkup | None:
    """
    Master appointment controls.
    dismiss=True: OK (hub dismiss) for push notifications.
    dismiss=False: Close (strip keyboard) for /today cards.
    """
    if now is not None and is_slot_past(slot_ends_at=slot_ends_at, now=now):
        return None

    rows: list[list[InlineKeyboardButton]] = []
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
    if row:
        rows.append(row)

    if dismiss:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.get("hub_ok_button"),
                    callback_data=HubCallback(action="dismiss").pack(),
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.get("master_close_button"),
                    callback_data=MasterAppointmentCallback(
                        action="close",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
