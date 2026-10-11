from contextlib import suppress
from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.appointment_cancel import (
    AppointmentCancelCallback,
    get_appointment_cancel_confirm_kb,
    get_appointment_cancel_reason_kb,
)
from app.bot.states.states import AppointmentCancelSG
from app.bot.utils.cancel_registry import (
    MASTER_SOURCES as _MASTER_SOURCES,
)
from app.bot.utils.cancel_registry import (
    SOURCE_REMINDER,
    CancelPhase,
    CancelResumeCtx,
    dispatch,
)
from app.bot.utils.hub_nav import clear_state_keep_hub
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
from app.domain.models import Appointment, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories

appointment_cancel_router = Router(name="appointment_cancel")

_BOOKINGS_NAV_KEYS = ("bookings_week_start", "bookings_month", "bookings_day")

_REASON_MAX_LEN = 200
_APPT_KEY = "cancel_appointment_id"
_SOURCE_KEY = "cancel_source"
_MODE_KEY = "cancel_mode"
_KIND_KEY = "cancel_reminder_kind"
_PROMPT_ID_KEY = "cancel_prompt_message_id"
_STATUSES_KEY = "cancel_allowed_statuses"


def _confirm_text_key(mode: str) -> str:
    return "decline_confirm" if mode == "decline" else "cancel_confirm"


def _ask_reason_key(mode: str) -> str:
    return "decline_ask_reason" if mode == "decline" else "cancel_ask_reason"


async def _clear_cancel_state(state: FSMContext) -> None:
    """Clear cancel FSM but keep sticky hub nav and master Bookings nav keys."""
    data = await state.get_data()
    bookings_keep = {
        key: data[key]
        for key in _BOOKINGS_NAV_KEYS
        if key in data and data[key] is not None
    }
    await clear_state_keep_hub(state)
    if bookings_keep:
        await state.update_data(bookings_keep)


def _is_appointment_past(appointment: Appointment, *, source: str) -> bool:
    """Master actions stay open until slot end; others until start."""
    now = datetime.now(UTC)
    if source in _MASTER_SOURCES:
        ends = appointment.ends_at
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=UTC)
        return ends <= now
    return _is_past(appointment)


def _is_party(*, user: User, appointment: Appointment) -> bool:
    return user.user_id in (
        appointment.client_user_id,
        appointment.master_user_id,
    )


def _is_past(appointment: Appointment) -> bool:
    now = datetime.now(UTC)
    starts = appointment.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    return now >= starts


def _default_allowed_statuses(source: str) -> frozenset[AppointmentStatus]:
    if source == SOURCE_REMINDER:
        return frozenset({AppointmentStatus.CONFIRMED})
    return frozenset(
        {
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED,
        }
    )


def _statuses_from_state(raw: object) -> frozenset[AppointmentStatus]:
    if not isinstance(raw, list):
        return frozenset({AppointmentStatus.CONFIRMED})
    out: set[AppointmentStatus] = set()
    for item in raw:
        try:
            out.add(AppointmentStatus(item))
        except ValueError:
            continue
    return frozenset(out) or frozenset({AppointmentStatus.CONFIRMED})


def _resume_ctx(
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


async def _dispatch_resume(
        source: str,
        phase: CancelPhase,
        ctx: CancelResumeCtx,
) -> None:
    await dispatch(source, phase, ctx)


async def _disarm_stale(
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
    await _dispatch_resume(
        source,
        "unavailable",
        _resume_ctx(
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


async def _load_usable_appointment(
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
    if appointment is None or not _is_party(user=user, appointment=appointment):
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
        await _disarm_stale(
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

    if _is_appointment_past(appointment, source=source):
        await callback.answer(
            text=i18n.get("cancel_past"),
            show_alert=True,
        )
        await _disarm_stale(
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
        await _clear_cancel_state(state)
        failed = await repos.appointments.get_appointment(
            appointment_id=appointment_id,
        )
        await _dispatch_resume(
            source,
            "unavailable",
            _resume_ctx(
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

    await _clear_cancel_state(state)
    await _dispatch_resume(
        source,
        "success",
        _resume_ctx(
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
    statuses = allowed_statuses or _default_allowed_statuses(source)
    appointment = await _load_usable_appointment(
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
        text_key=_confirm_text_key(mode),
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
    statuses = _default_allowed_statuses(callback_data.source)
    appointment = await _load_usable_appointment(
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
        await _clear_cancel_state(state)
        return

    await _clear_cancel_state(state)

    if (
            callback_data.source == SOURCE_REMINDER
            and parse_reminder_kind(callback_data.reminder_kind) is None
    ):
        await callback.answer(
            text=i18n.get("cancel_failed"),
            show_alert=True,
        )
        return

    await _dispatch_resume(
        callback_data.source,
        "abort",
        _resume_ctx(
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
    statuses = _default_allowed_statuses(callback_data.source)
    appointment = await _load_usable_appointment(
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
            _APPT_KEY: appointment.id,
            _SOURCE_KEY: callback_data.source,
            _MODE_KEY: callback_data.mode,
            _KIND_KEY: callback_data.reminder_kind,
            _PROMPT_ID_KEY: callback.message.message_id,
            _STATUSES_KEY: [status.value for status in statuses],
        }
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=i18n.get(_ask_reason_key(callback_data.mode)),
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
    statuses = _default_allowed_statuses(callback_data.source)
    appointment = await _load_usable_appointment(
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
        await _clear_cancel_state(state)
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
    if callback_data.source not in _MASTER_SOURCES:
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
        await _clear_cancel_state(state)
        return

    raw = (message.text or "").strip()
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    appointment_id = data.get(_APPT_KEY)
    prompt_id = data.get(_PROMPT_ID_KEY)
    source = str(data.get(_SOURCE_KEY) or SOURCE_REMINDER)
    mode = str(data.get(_MODE_KEY) or "cancel")
    reminder_kind = str(data.get(_KIND_KEY) or "")
    statuses = _statuses_from_state(data.get(_STATUSES_KEY))
    if not isinstance(appointment_id, int) or not isinstance(prompt_id, int):
        await _clear_cancel_state(state)
        return

    if len(raw) > _REASON_MAX_LEN:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=(
                    f"{i18n.get('cancel_reason_too_long')}\n\n"
                    f"{i18n.get(_ask_reason_key(mode))}"
                ),
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
        or not _is_party(user=user, appointment=appointment)
        or appointment.status not in statuses
        or _is_appointment_past(appointment, source=source)
    ):
        await _clear_cancel_state(state)
        await _dispatch_resume(
            source,
            "unavailable",
            _resume_ctx(
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
