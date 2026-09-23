from datetime import datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.enums import AppointmentStatus
from app.domain.models.appointment import Appointment


class MasterAppointmentCallback(CallbackData, prefix="mapt"):
    action: str  # open | back | close | confirm | cancel
    appointment_id: int = 0


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
) -> InlineKeyboardMarkup | None:
    """Confirm/cancel controls for master booking push notifications."""
    if now is not None and is_slot_past(slot_ends_at=slot_ends_at, now=now):
        return None

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
    if not row:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[row])


def get_master_bookings_list_kb(
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
                    callback_data=MasterAppointmentCallback(
                        action="open",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("master_bookings_close_button"),
                callback_data=MasterAppointmentCallback(action="close").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_master_booking_card_kb(
        *,
        appointment: Appointment,
        i18n: dict[str, str],
        now: datetime,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    past = is_slot_past(slot_ends_at=appointment.ends_at, now=now)

    if not past:
        actions: list[InlineKeyboardButton] = []
        if appointment.status == AppointmentStatus.PENDING:
            actions.append(
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
            actions.append(
                InlineKeyboardButton(
                    text=i18n.get("master_cancel_button"),
                    callback_data=MasterAppointmentCallback(
                        action="cancel",
                        appointment_id=appointment.id,
                    ).pack(),
                )
            )
        if actions:
            rows.append(actions)

    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("master_bookings_back_button"),
                callback_data=MasterAppointmentCallback(
                    action="back",
                    appointment_id=appointment.id,
                ).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
