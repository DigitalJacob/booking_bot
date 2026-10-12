from contextlib import suppress

from aiogram import Bot, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.appointment_cancel.common import (
    APPT_KEY,
    KIND_KEY,
    MODE_KEY,
    PROMPT_ID_KEY,
    REASON_MAX_LEN,
    SOURCE_KEY,
    STATUSES_KEY,
    ask_reason_key,
    clear_cancel_state,
    confirm_text_key,
    default_allowed_statuses,
    dispatch_resume,
    is_appointment_past,
    is_party,
    load_usable_appointment,
    resume_ctx,
    statuses_from_state,
)
from app.bot.handlers.common.appointment_cancel.router import appointment_cancel_router
from app.bot.keyboards.appointment_cancel import (
    AppointmentCancelCallback,
    get_appointment_cancel_confirm_kb,
    get_appointment_cancel_reason_kb,
)
from app.bot.states.states import AppointmentCancelSG
from app.bot.utils.cancel_registry import MASTER_SOURCES, SOURCE_REMINDER
from app.bot.utils.notify import (
    appointment_notice_parts,
    notify_appointment,
    supersede_master_action_push,
)
from app.domain.enums import AppointmentStatus, ReminderKind, parse_reminder_kind
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


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
    source: str,
    mode: str,
    callback: CallbackQuery | None = None,
    reminder_kind: str = "",
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
        await clear_cancel_state(state)
        failed = await repos.appointments.get_appointment(
            appointment_id=appointment_id,
        )
        await dispatch_resume(
            source,
            "unavailable",
            resume_ctx(
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
                appointment=failed,
                appointment_id=appointment_id,
                callback=callback,
                reminder_kind=reminder_kind,
                notice_key="cancel_failed",
            ),
        )
        if callback is not None:
            await callback.answer(
                text=i18n.get("cancel_failed"),
                show_alert=True,
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

    await clear_cancel_state(state)
    await dispatch_resume(
        source,
        "success",
        resume_ctx(
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
            appointment_id=appointment.id,
            callback=callback,
            reminder_kind=reminder_kind,
        ),
    )


async def start_appointment_cancel(
    *,
    callback: CallbackQuery,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
    appointment_id: int,
    source: str,
    mode: str = "cancel",
    reminder_kind: ReminderKind | None = None,
    allowed_statuses: frozenset[AppointmentStatus] | None = None,
    state: FSMContext | None = None,
) -> None:
    """Show confirm screen for cancelling / declining an appointment."""
    statuses = allowed_statuses or default_allowed_statuses(source)
    appointment = await load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=appointment_id,
        i18n=i18n,
        allowed_statuses=statuses,
        source=source,
        bot_timezone=bot_timezone,
        translations=translations,
        state=state,
    )
    if appointment is None or user is None:
        return

    packed_kind = reminder_kind.value if reminder_kind is not None else ""
    _, text = await appointment_notice_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key=confirm_text_key(mode),
        bot_timezone=bot_timezone,
        recipient_user_id=user.user_id,
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            reply_markup=get_appointment_cancel_confirm_kb(
                i18n=i18n,
                appointment_id=appointment.id,
                source=source,
                mode=mode,
                reminder_kind=packed_kind,
            ),
        )
    await callback.answer()


@appointment_cancel_router.callback_query(
    AppointmentCancelCallback.filter(F.action == "no"),
)
async def process_cancel_no(
    callback: CallbackQuery,
    callback_data: AppointmentCancelCallback,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
    state: FSMContext,
) -> None:
    statuses = default_allowed_statuses(callback_data.source)
    appointment = await load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
        allowed_statuses=statuses,
        source=callback_data.source,
        bot_timezone=bot_timezone,
        translations=translations,
        state=state,
    )
    if appointment is None or user is None:
        await clear_cancel_state(state)
        return

    await clear_cancel_state(state)

    if (
        callback_data.source == SOURCE_REMINDER
        and parse_reminder_kind(callback_data.reminder_kind) is None
    ):
        await callback.answer(
            text=i18n.get("cancel_failed"),
            show_alert=True,
        )
        return

    await dispatch_resume(
        callback_data.source,
        "abort",
        resume_ctx(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            repos=repos,
            user=user,
            i18n=i18n,
            translations=translations,
            bot_timezone=bot_timezone,
            source=callback_data.source,
            mode=callback_data.mode,
            state=state,
            appointment=appointment,
            appointment_id=appointment.id,
            callback=callback,
            reminder_kind=callback_data.reminder_kind,
        ),
    )
    await callback.answer()


@appointment_cancel_router.callback_query(
    AppointmentCancelCallback.filter(F.action == "yes"),
)
async def process_cancel_yes(
    callback: CallbackQuery,
    callback_data: AppointmentCancelCallback,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
    state: FSMContext,
) -> None:
    statuses = default_allowed_statuses(callback_data.source)
    appointment = await load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
        allowed_statuses=statuses,
        source=callback_data.source,
        bot_timezone=bot_timezone,
        translations=translations,
        state=state,
    )
    if appointment is None:
        return

    await state.set_state(AppointmentCancelSG.reason)
    await state.update_data(
        {
            APPT_KEY: appointment.id,
            SOURCE_KEY: callback_data.source,
            MODE_KEY: callback_data.mode,
            KIND_KEY: callback_data.reminder_kind,
            PROMPT_ID_KEY: callback.message.message_id,
            STATUSES_KEY: [status.value for status in statuses],
        }
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=i18n.get(ask_reason_key(callback_data.mode)),
            reply_markup=get_appointment_cancel_reason_kb(
                i18n=i18n,
                appointment_id=appointment.id,
                source=callback_data.source,
                mode=callback_data.mode,
                reminder_kind=callback_data.reminder_kind,
            ),
        )
    await callback.answer()


@appointment_cancel_router.callback_query(
    AppointmentCancelCallback.filter(F.action == "skip_reason"),
)
async def process_cancel_skip_reason(
    callback: CallbackQuery,
    callback_data: AppointmentCancelCallback,
    bot: Bot,
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
) -> None:
    statuses = default_allowed_statuses(callback_data.source)
    appointment = await load_usable_appointment(
        callback=callback,
        repos=repos,
        user=user,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
        allowed_statuses=statuses,
        source=callback_data.source,
        bot_timezone=bot_timezone,
        translations=translations,
        state=state,
    )
    if appointment is None or user is None:
        await clear_cancel_state(state)
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
        source=callback_data.source,
        mode=callback_data.mode,
        callback=callback,
        reminder_kind=callback_data.reminder_kind,
    )
    if callback_data.source not in MASTER_SOURCES:
        await callback.answer()


@appointment_cancel_router.message(StateFilter(AppointmentCancelSG.reason), F.text)
async def process_cancel_reason_text(
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
        await clear_cancel_state(state)
        return

    raw = (message.text or "").strip()
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    appointment_id = data.get(APPT_KEY)
    prompt_id = data.get(PROMPT_ID_KEY)
    source = str(data.get(SOURCE_KEY) or SOURCE_REMINDER)
    mode = str(data.get(MODE_KEY) or "cancel")
    reminder_kind = str(data.get(KIND_KEY) or "")
    statuses = statuses_from_state(data.get(STATUSES_KEY))
    if not isinstance(appointment_id, int) or not isinstance(prompt_id, int):
        await clear_cancel_state(state)
        return

    if len(raw) > REASON_MAX_LEN:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=(f"{i18n.get('cancel_reason_too_long')}\n\n{i18n.get(ask_reason_key(mode))}"),
                reply_markup=get_appointment_cancel_reason_kb(
                    i18n=i18n,
                    appointment_id=appointment_id,
                    source=source,
                    mode=mode,
                    reminder_kind=reminder_kind,
                ),
            )
        return

    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if (
        appointment is None
        or not is_party(user=user, appointment=appointment)
        or appointment.status not in statuses
        or is_appointment_past(appointment, source=source)
    ):
        await clear_cancel_state(state)
        await dispatch_resume(
            source,
            "unavailable",
            resume_ctx(
                bot=bot,
                chat_id=message.chat.id,
                message_id=prompt_id,
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
                reminder_kind=reminder_kind,
                notice_key="cancel_unavailable",
            ),
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
        source=source,
        mode=mode,
        reminder_kind=reminder_kind,
    )
