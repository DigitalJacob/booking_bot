from datetime import datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
        with_close: bool = True,
) -> InlineKeyboardMarkup | None:
    """
    Master appointment controls.
    with_close=False: push notifications (confirm/cancel only; hub opens after).
    with_close=True: /today cards (Close strips the keyboard).
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

    if with_close:
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

    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)
