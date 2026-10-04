from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.reminders import (
    ReminderCallback,
    get_reminder_cancel_confirm_kb,
    get_reminder_kb,
    get_reminder_reason_kb,
)
from app.bot.reminders import REMINDER_TEXT_KEY_BY_KIND
from app.bot.states.states import ReminderCancelSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.notify import (
    appointment_notice_parts,
    notify_appointment,
    supersede_master_action_push,
)
from app.domain.enums import AppointmentStatus, ReminderKind
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.models import Appointment, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


reminder_router = Router(name="reminders")

_REASON_MAX_LEN = 200
_REMINDER_APPT_KEY = "reminder_cancel_appointment_id"
_REMINDER_KIND_KEY = "reminder_cancel_kind"
_REMINDER_PROMPT_ID_KEY = "reminder_cancel_prompt_message_id"


def _parse_kind(raw: str) -> ReminderKind | None:
    try:
        return ReminderKind(raw)
    except ValueError:
        return None


async def _edit_dismissable(
        *,
        bot: Bot,
        chat_id: int,
        message_id: int,
        text: str,
        i18n: dict[str, str],
) -> None:
    with suppress(TelegramBadRequest):
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=get_hub_dismiss_kb(i18n),
        )


def _is_party(*, user: User, appointment: Appointment) -> bool:
    return user.user_id in (
        appointment.client_user_id,
        appointment.master_user_id,
    )


def _is_past(appointment: Appointment) -> bool:
    now = datetime.now(timezone.utc)
    starts = appointment.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=timezone.utc)
    return now >= starts


async def _load_usable_appointment(
        *,
        callback: CallbackQuery,
        repos: Repositories,
        user: User | None,
        appointment_id: int,
        i18n: dict[str, str],
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
    if appointment is None or not _is_party(user=user, appointment=appointment):
        await callback.answer(
            text=i18n.get("reminder_cancel_unavailable"),
            show_alert=True,
        )
        return None

    if appointment.status != AppointmentStatus.CONFIRMED:
        await callback.answer(
            text=i18n.get("reminder_cancel_unavailable"),
            show_alert=True,
        )
        await _edit_dismissable(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=i18n.get("reminder_cancel_unavailable"),
            i18n=i18n,
        )
        return None

    if _is_past(appointment):
        await callback.answer(
            text=i18n.get("reminder_cancel_past"),
            show_alert=True,
        )
        await _edit_dismissable(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=i18n.get("reminder_cancel_past"),
            i18n=i18n,
        )
        return None

    return appointment


async def _restore_reminder_message(
        *,
        callback: CallbackQuery,
        repos: Repositories,
        translations: dict,
        bot_timezone: str,
        appointment: Appointment,
        kind: ReminderKind,
        user: User,
) -> None:
    text_key = REMINDER_TEXT_KEY_BY_KIND[kind]
    i18n, text = await appointment_notice_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key=text_key,
        bot_timezone=bot_timezone,
        recipient_user_id=user.user_id,
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            reply_markup=get_reminder_kb(
                i18n=i18n,
                appointment_id=appointment.id,
                kind=kind,
            ),
        )


async def _finish_cancel(
        *,
        bot: Bot,
        chat_id: int,
        message_id: int,
        state: FSMContext,
        repos: Repositories,
        translations: dict,
        bot_timezone: str,
        user: User,
        i18n: dict[str, str],
        appointment_id: int,
        reason: str | None,
) -> None:
    booking = BookingService(repos)
    try:
        appointment = await booking.cancel(
            appointment_id=appointment_id,
            actor_user_id=user.user_id,
        )
    except (
        AppointmentNotFound,
        ForbiddenBookingAction,
        InvalidAppointmentStatus,
    ):
        await clear_state_keep_hub(state)
        await _edit_dismissable(
            bot=bot,
            chat_id=chat_id,
            message_id=message_id,
            text=i18n.get("reminder_cancel_failed"),
            i18n=i18n,
        )
        return

    if user.user_id == appointment.client_user_id:
        text_key = "master_booking_cancelled_by_client"
        superseded = await supersede_master_action_push(
            bot=bot,
            repos=repos,
            appointment=appointment,
            translations=translations,
            text_key=text_key,
            bot_timezone=bot_timezone,
            reason=reason,
        )
        if not superseded:
            await notify_appointment(
                bot=bot,
                repos=repos,
                appointment=appointment,
                recipient_user_id=appointment.master_user_id,
                translations=translations,
                text_key=text_key,
                bot_timezone=bot_timezone,
                with_dismiss=True,
                reason=reason,
            )
    else:
        await notify_appointment(
            bot=bot,
            repos=repos,
            appointment=appointment,
            recipient_user_id=appointment.client_user_id,
            translations=translations,
            text_key="client_booking_cancelled_by_master",
            bot_timezone=bot_timezone,
            with_dismiss=True,
            reason=reason,
        )

    await clear_state_keep_hub(state)
    await _edit_dismissable(
        bot=bot,
        chat_id=chat_id,
        message_id=message_id,
        text=i18n.get("reminder_cancelled_done"),
        i18n=i18n,
    )


@reminder_router.callback_query(ReminderCallback.filter(F.action == "cancel"))
async def process_reminder_cancel(
        callback: CallbackQuery,
        callback_data: ReminderCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        translations: dict,
        bot_timezone: str,
) -> None:
    kind = _parse_kind(callback_data.kind)
    if kind is None:
        await callback.answer(
            text=i18n.get("reminder_cancel_failed"),
            show_alert=True,
        )
        return

    appointment = await _load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    )
    if appointment is None or user is None:
        return

    _, text = await appointment_notice_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key="reminder_cancel_confirm",
        bot_timezone=bot_timezone,
        recipient_user_id=user.user_id,
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            reply_markup=get_reminder_cancel_confirm_kb(
                i18n=i18n,
                appointment_id=appointment.id,
                kind=kind,
            ),
        )
    await callback.answer()


@reminder_router.callback_query(ReminderCallback.filter(F.action == "cancel_no"))
async def process_reminder_cancel_no(
        callback: CallbackQuery,
        callback_data: ReminderCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        translations: dict,
        bot_timezone: str,
        state: FSMContext,
) -> None:
    kind = _parse_kind(callback_data.kind)
    if kind is None or user is None:
        await callback.answer(
            text=i18n.get("reminder_cancel_failed"),
            show_alert=True,
        )
        return

    appointment = await _load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    )
    if appointment is None:
        await clear_state_keep_hub(state)
        return

    await clear_state_keep_hub(state)
    await _restore_reminder_message(
        callback=callback,
        repos=repos,
        translations=translations,
        bot_timezone=bot_timezone,
        appointment=appointment,
        kind=kind,
        user=user,
    )
    await callback.answer()


@reminder_router.callback_query(ReminderCallback.filter(F.action == "cancel_yes"))
async def process_reminder_cancel_yes(
        callback: CallbackQuery,
        callback_data: ReminderCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        state: FSMContext,
) -> None:
    kind = _parse_kind(callback_data.kind)
    if kind is None:
        await callback.answer(
            text=i18n.get("reminder_cancel_failed"),
            show_alert=True,
        )
        return

    appointment = await _load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    )
    if appointment is None:
        return

    await state.set_state(ReminderCancelSG.reason)
    await state.update_data(
        {
            _REMINDER_APPT_KEY: appointment.id,
            _REMINDER_KIND_KEY: kind.value,
            _REMINDER_PROMPT_ID_KEY: callback.message.message_id,
        }
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=i18n.get("reminder_ask_reason"),
            reply_markup=get_reminder_reason_kb(
                i18n=i18n,
                appointment_id=appointment.id,
                kind=kind,
            ),
        )
    await callback.answer()


@reminder_router.callback_query(ReminderCallback.filter(F.action == "skip_reason"))
async def process_reminder_skip_reason(
        callback: CallbackQuery,
        callback_data: ReminderCallback,
        bot: Bot,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        translations: dict,
        bot_timezone: str,
) -> None:
    appointment = await _load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    )
    if appointment is None or user is None:
        await clear_state_keep_hub(state)
        return

    await _finish_cancel(
        bot=bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        state=state,
        repos=repos,
        translations=translations,
        bot_timezone=bot_timezone,
        user=user,
        i18n=i18n,
        appointment_id=appointment.id,
        reason=None,
    )
    await callback.answer()


@reminder_router.message(StateFilter(ReminderCancelSG.reason), F.text)
async def process_reminder_reason_text(
        message: Message,
        bot: Bot,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        translations: dict,
        bot_timezone: str,
) -> None:
    if user is None:
        await clear_state_keep_hub(state)
        return

    raw = (message.text or "").strip()
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    appointment_id = data.get(_REMINDER_APPT_KEY)
    prompt_id = data.get(_REMINDER_PROMPT_ID_KEY)
    kind = _parse_kind(str(data.get(_REMINDER_KIND_KEY) or ""))
    if not isinstance(appointment_id, int) or not isinstance(prompt_id, int):
        await clear_state_keep_hub(state)
        return

    if len(raw) > _REASON_MAX_LEN:
        if kind is None:
            return
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=(
                    f"{i18n.get('reminder_reason_too_long')}\n\n"
                    f"{i18n.get('reminder_ask_reason')}"
                ),
                reply_markup=get_reminder_reason_kb(
                    i18n=i18n,
                    appointment_id=appointment_id,
                    kind=kind,
                ),
            )
        return

    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if (
        appointment is None
        or not _is_party(user=user, appointment=appointment)
        or appointment.status != AppointmentStatus.CONFIRMED
        or _is_past(appointment)
    ):
        await clear_state_keep_hub(state)
        await _edit_dismissable(
            bot=bot,
            chat_id=message.chat.id,
            message_id=prompt_id,
            text=i18n.get("reminder_cancel_unavailable"),
            i18n=i18n,
        )
        return

    await _finish_cancel(
        bot=bot,
        chat_id=message.chat.id,
        message_id=prompt_id,
        state=state,
        repos=repos,
        translations=translations,
        bot_timezone=bot_timezone,
        user=user,
        i18n=i18n,
        appointment_id=appointment_id,
        reason=raw or None,
    )
