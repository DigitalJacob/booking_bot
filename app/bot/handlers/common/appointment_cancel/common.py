"""Shared helpers and FSM keys for appointment cancel / decline flow."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.utils.cancel_registry import (
    MASTER_SOURCES,
    SOURCE_REMINDER,
    CancelPhase,
    CancelResumeCtx,
    dispatch,
)
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.domain.enums import AppointmentStatus
from app.domain.models import Appointment, User
from app.infrastructure.database.repositories import Repositories

BOOKINGS_NAV_KEYS = ("bookings_week_start", "bookings_month", "bookings_day")

REASON_MAX_LEN = 200
APPT_KEY = "cancel_appointment_id"
SOURCE_KEY = "cancel_source"
MODE_KEY = "cancel_mode"
KIND_KEY = "cancel_reminder_kind"
PROMPT_ID_KEY = "cancel_prompt_message_id"
STATUSES_KEY = "cancel_allowed_statuses"


def confirm_text_key(mode: str) -> str:
    return "decline_confirm" if mode == "decline" else "cancel_confirm"


def ask_reason_key(mode: str) -> str:
    return "decline_ask_reason" if mode == "decline" else "cancel_ask_reason"


async def clear_cancel_state(state: FSMContext) -> None:
    """Clear cancel FSM but keep sticky hub nav and master Bookings nav keys."""
    data = await state.get_data()
    bookings_keep = {
        key: data[key] for key in BOOKINGS_NAV_KEYS if key in data and data[key] is not None
    }
    await clear_state_keep_hub(state)
    if bookings_keep:
        await state.update_data(bookings_keep)


def is_past(appointment: Appointment) -> bool:
    now = datetime.now(UTC)
    starts = appointment.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    return now >= starts


def is_appointment_past(appointment: Appointment, *, source: str) -> bool:
    """Master actions stay open until slot end; others until start."""
    now = datetime.now(UTC)
    if source in MASTER_SOURCES:
        ends = appointment.ends_at
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=UTC)
        return ends <= now
    return is_past(appointment)


def is_party(*, user: User, appointment: Appointment) -> bool:
    # client_user_id may be None for manual clients → only master matches.
    return user.user_id in (
        appointment.client_user_id,
        appointment.master_user_id,
    )


def default_allowed_statuses(source: str) -> frozenset[AppointmentStatus]:
    if source == SOURCE_REMINDER:
        return frozenset({AppointmentStatus.CONFIRMED})
    return frozenset(
        {
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED,
        }
    )


def statuses_from_state(raw: object) -> frozenset[AppointmentStatus]:
    if not isinstance(raw, list):
        return frozenset({AppointmentStatus.CONFIRMED})
    out: set[AppointmentStatus] = set()
    for item in raw:
        try:
            out.add(AppointmentStatus(item))
        except ValueError:
            continue
    return frozenset(out) or frozenset({AppointmentStatus.CONFIRMED})


def resume_ctx(
    *,
    bot: Bot,
    chat_id: int,
    message_id: int,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
    source: str,
    mode: str,
    state: FSMContext | None = None,
    appointment: Appointment | None = None,
    appointment_id: int | None = None,
    callback: CallbackQuery | None = None,
    reminder_kind: str = "",
    notice_key: str | None = None,
) -> CancelResumeCtx:
    return CancelResumeCtx(
        bot=bot,
        chat_id=chat_id,
        message_id=message_id,
        repos=repos,
        user=user,
        i18n=i18n,
        translations=translations,
        bot_timezone=bot_timezone,
        source=source,
        mode=mode,
        state=state,
        appointment=appointment,
        appointment_id=appointment_id,
        callback=callback,
        reminder_kind=reminder_kind,
        notice_key=notice_key,
    )


async def dispatch_resume(
    source: str,
    phase: CancelPhase,
    ctx: CancelResumeCtx,
) -> None:
    await dispatch(source, phase, ctx)


async def disarm_stale(
    *,
    callback: CallbackQuery,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
    source: str,
    appointment: Appointment,
    text_key: str,
    state: FSMContext | None = None,
) -> None:
    await dispatch_resume(
        source,
        "unavailable",
        resume_ctx(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            repos=repos,
            user=user,
            i18n=i18n,
            translations=translations,
            bot_timezone=bot_timezone,
            source=source,
            mode="cancel",
            state=state,
            appointment=appointment,
            appointment_id=appointment.id,
            callback=callback,
            notice_key=text_key,
        ),
    )


async def load_usable_appointment(
    *,
    callback: CallbackQuery,
    repos: Repositories,
    user: User | None,
    appointment_id: int,
    i18n: dict[str, str],
    allowed_statuses: frozenset[AppointmentStatus],
    source: str,
    bot_timezone: str,
    translations: dict,
    state: FSMContext | None = None,
) -> Appointment | None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        return None

    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if appointment is None or not is_party(user=user, appointment=appointment):
        await callback.answer(
            text=i18n.get("cancel_unavailable"),
            show_alert=True,
        )
        return None

    if appointment.status not in allowed_statuses:
        await callback.answer(
            text=i18n.get("cancel_unavailable"),
            show_alert=True,
        )
        await disarm_stale(
            callback=callback,
            repos=repos,
            user=user,
            i18n=i18n,
            translations=translations,
            bot_timezone=bot_timezone,
            source=source,
            appointment=appointment,
            text_key="cancel_unavailable",
            state=state,
        )
        return None

    if is_appointment_past(appointment, source=source):
        await callback.answer(
            text=i18n.get("cancel_past"),
            show_alert=True,
        )
        await disarm_stale(
            callback=callback,
            repos=repos,
            user=user,
            i18n=i18n,
            translations=translations,
            bot_timezone=bot_timezone,
            source=source,
            appointment=appointment,
            text_key="cancel_past",
            state=state,
        )
        return None

    return appointment
