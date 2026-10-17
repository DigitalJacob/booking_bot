from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime

from aiogram import Bot, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.handlers.common.appointment_cancel import start_appointment_cancel
from app.bot.handlers.master.bookings.common import (
    DAY_KEY,
    MONTH_KEY,
    WEEK_START_KEY,
    back_to_from_state,
    parse_iso_date,
)
from app.bot.handlers.master.bookings.list import (
    build_master_bookings_day,
    show_master_bookings_day,
    show_master_bookings_month,
    show_master_bookings_overview,
    show_master_bookings_week,
)
from app.bot.handlers.master.bookings.router import bookings_router
from app.bot.keyboards.bookings import (
    MasterAppointmentCallback,
    get_appointment_actions_kb,
    get_master_booking_card_kb,
    is_slot_past,
)
from app.bot.keyboards.hub import get_hub_root_kb
from app.bot.utils.cancel_registry import SOURCE_MASTER_BOOKINGS, SOURCE_MASTER_PUSH
from app.bot.utils.dates import format_year_month
from app.bot.utils.format import (
    appointment_client_contact,
    format_dt,
    local_month_bounds,
    local_week_bounds,
    status_label,
    to_local,
)
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, show_hub
from app.bot.utils.hub_registry import register
from app.bot.utils.notify import (
    appointment_notice_parts,
    notify_appointment,
    supersede_master_action_push,
)
from app.domain.enums import AppointmentStatus, UserRole
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.models import Appointment, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


async def build_master_booking_card(
    *,
    appointment: Appointment,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
) -> tuple[str, InlineKeyboardMarkup]:
    service = await repos.services.get_service(service_id=appointment.service_id)
    title = service.title if service else "?"
    client_name, client_phone = await appointment_client_contact(repos, appointment)
    now = datetime.now(UTC)
    past = is_slot_past(slot_ends_at=appointment.ends_at, now=now)
    text_key = "master_bookings_card_past" if past else "master_bookings_card"
    text = i18n.get(text_key).format(
        when=format_dt(appointment.starts_at, bot_timezone),
        title=title,
        status=status_label(appointment.status, i18n),
        client_name=client_name,
        client_phone=client_phone,
    )
    return text, get_master_booking_card_kb(
        appointment=appointment,
        i18n=i18n,
        now=now,
    )


async def build_master_new_booking_push(
    *,
    appointment: Appointment,
    repos: Repositories,
    translations: dict,
    bot_timezone: str,
) -> tuple[dict[str, str], str, InlineKeyboardMarkup | None]:
    i18n, text = await appointment_notice_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key="master_new_booking",
        bot_timezone=bot_timezone,
        recipient_user_id=appointment.master_user_id,
    )
    kb = get_appointment_actions_kb(
        appointment=appointment,
        i18n=i18n,
        now=datetime.now(UTC),
        slot_ends_at=appointment.ends_at,
    )
    return i18n, text, kb


async def _show_booking_card(
    *,
    message: Message,
    state: FSMContext,
    appointment: Appointment,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    day = to_local(appointment.starts_at, bot_timezone).date()
    await state.update_data({DAY_KEY: day.isoformat()})
    text, kb = await build_master_booking_card(
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await message.edit_text(text=text, reply_markup=kb)


async def _reject_if_slot_past(
    *,
    callback: CallbackQuery,
    repos: Repositories,
    appointment_id: int,
    i18n: dict[str, str],
) -> bool:
    """Return True if the handler should stop"""
    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return True

    if is_slot_past(
        slot_ends_at=appointment.ends_at,
        now=datetime.now(UTC),
    ):
        await callback.answer(
            text=i18n.get("master_action_past"),
            show_alert=True,
        )
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
        return True
    return False


async def disarm_stale_master_push(
    *,
    callback: CallbackQuery,
    bot: Bot,
    repos: Repositories,
    appointment_id: int,
    translations: dict,
    bot_timezone: str,
) -> None:
    """Turn a stale confirm/cancel push into status+OK or strip its keyboard."""
    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if (
        appointment is not None
        and appointment.status == AppointmentStatus.CANCELLED
        and await supersede_master_action_push(
            bot=bot,
            repos=repos,
            appointment=appointment,
            translations=translations,
            text_key="master_booking_cancelled_by_client",
            bot_timezone=bot_timezone,
        )
    ):
        return

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    if appointment is not None and appointment.master_notify_message_id is not None:
        await repos.appointments.set_master_notify_message_id(
            appointment_id=appointment.id,
            message_id=None,
        )


async def resume_master_after_cancel(
    *,
    bot: Bot,
    chat_id: int,
    message_id: int,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    appointment: Appointment,
    source: str,
) -> None:
    """Sticky day list, or hub restore + delete push — after master cancel/decline."""
    await repos.appointments.set_master_notify_message_id(
        appointment_id=appointment.id,
        message_id=None,
    )

    if source == SOURCE_MASTER_BOOKINGS:
        day = to_local(appointment.starts_at, bot_timezone).date()
        back_to = await back_to_from_state(state)
        await state.update_data(
            {
                "hub_screen": "bookings",
                "hub_back": "root",
                "list_return": "root",
                DAY_KEY: day.isoformat(),
            }
        )
        text, kb = await build_master_bookings_day(
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            day=day,
            back_to=back_to,
        )
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=kb,
            )
        return

    # Push: restore sticky hub, then delete the push message.
    await state.update_data(
        hub_screen="root",
        hub_back="root",
        list_return="root",
    )
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    hub_text = i18n.get("hub_title")
    hub_kb = get_hub_root_kb(role=UserRole.MASTER, i18n=i18n)
    if sticky_id is not None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=int(sticky_id),
                text=hub_text,
                reply_markup=hub_kb,
            )
    if sticky_id is None or int(sticky_id) != message_id:
        with suppress(TelegramBadRequest):
            await bot.delete_message(chat_id=chat_id, message_id=message_id)


async def _finish_master_decision(
    *,
    callback: CallbackQuery,
    user: User,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    appointment_id: int,
    bot_timezone: str,
    ack_text: str,
    schedule_mode: str = "weekly",
) -> None:
    """
    Sticky card: refresh the day list in place.
    Push notification: restore hub and delete the push.
    """
    await repos.appointments.set_master_notify_message_id(
        appointment_id=appointment_id,
        message_id=None,
    )
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    on_sticky = (
        sticky_id is not None
        and callback.message is not None
        and callback.message.message_id == sticky_id
    )
    if on_sticky:
        day = parse_iso_date(data.get(DAY_KEY))
        if day is not None:
            await show_master_bookings_day(
                message=callback.message,
                state=state,
                repos=repos,
                user=user,
                i18n=i18n,
                bot_timezone=bot_timezone,
                day=day,
                edit=True,
                schedule_mode=schedule_mode,
            )
        else:
            await show_master_bookings_overview(
                message=callback.message,
                state=state,
                repos=repos,
                user=user,
                i18n=i18n,
                bot_timezone=bot_timezone,
                schedule_mode=schedule_mode,
                edit=True,
            )
        await callback.answer(text=ack_text)
        return

    await show_hub(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    if sticky_id is None or callback.message.message_id != sticky_id:
        with suppress(TelegramBadRequest):
            await callback.message.delete()
    await callback.answer(text=ack_text)


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "open"))
async def process_open(
    callback: CallbackQuery,
    callback_data: MasterAppointmentCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    appointment = await repos.appointments.get_appointment(
        appointment_id=callback_data.appointment_id,
    )
    if appointment is None or appointment.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await _show_booking_card(
        message=callback.message,
        state=state,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "confirm"))
async def process_confirm(
    callback: CallbackQuery,
    callback_data: MasterAppointmentCallback,
    bot: Bot,
    translations: dict,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    state: FSMContext,
    schedule_mode: str,
) -> None:
    if await _reject_if_slot_past(
        callback=callback,
        repos=repos,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    ):
        return

    booking = BookingService(repos)
    try:
        appointment = await booking.confirm(
            appointment_id=callback_data.appointment_id,
            master_user_id=user.user_id,
        )
    except (AppointmentNotFound, ForbiddenBookingAction, InvalidAppointmentStatus):
        await disarm_stale_master_push(
            callback=callback,
            bot=bot,
            repos=repos,
            appointment_id=callback_data.appointment_id,
            translations=translations,
            bot_timezone=bot_timezone,
        )
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    if appointment.client_user_id is not None:
        await notify_appointment(
            bot=bot,
            repos=repos,
            appointment=appointment,
            recipient_user_id=appointment.client_user_id,
            translations=translations,
            text_key="client_booking_confirmed",
            bot_timezone=bot_timezone,
            with_dismiss=True,
        )
    await _finish_master_decision(
        callback=callback,
        user=user,
        i18n=i18n,
        state=state,
        repos=repos,
        appointment_id=appointment.id,
        bot_timezone=bot_timezone,
        ack_text=i18n.get("master_confirmed").format(id=appointment.id),
        schedule_mode=schedule_mode,
    )


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "cancel"))
async def process_cancel(
    callback: CallbackQuery,
    callback_data: MasterAppointmentCallback,
    translations: dict,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    state: FSMContext,
) -> None:
    appointment = await repos.appointments.get_appointment(
        appointment_id=callback_data.appointment_id,
    )
    if appointment is None or appointment.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    if appointment.status == AppointmentStatus.PENDING:
        mode = "decline"
    elif appointment.status == AppointmentStatus.CONFIRMED:
        mode = "cancel"
    else:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    on_sticky = (
        sticky_id is not None
        and callback.message is not None
        and callback.message.message_id == sticky_id
    )
    source = SOURCE_MASTER_BOOKINGS if on_sticky else SOURCE_MASTER_PUSH

    await start_appointment_cancel(
        callback=callback,
        repos=repos,
        user=user,
        i18n=i18n,
        translations=translations,
        bot_timezone=bot_timezone,
        appointment_id=appointment.id,
        source=source,
        mode=mode,
        allowed_statuses=frozenset(
            {
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            }
        ),
        state=state,
    )


async def _hub_bookings(
    *,
    message: Message,
    user: User,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories | None = None,
    bot_timezone: str | None = None,
    schedule_mode: str = "weekly",
    **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None or bot_timezone is None:
        return
    if schedule_mode == "monthly":
        _, _, year, month = local_month_bounds(bot_timezone)
        await state.update_data(
            hub_screen="bookings",
            hub_back="root",
            list_return="root",
            **{
                MONTH_KEY: format_year_month(year, month),
                WEEK_START_KEY: None,
                DAY_KEY: None,
            },
        )
        await show_master_bookings_month(
            message=message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            edit=True,
        )
        return

    _, _, week_start = local_week_bounds(bot_timezone)
    await state.update_data(
        hub_screen="bookings",
        hub_back="root",
        list_return="root",
        **{
            WEEK_START_KEY: week_start.isoformat(),
            MONTH_KEY: None,
            DAY_KEY: None,
        },
    )
    await show_master_bookings_week(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )


register("bookings", _hub_bookings)
