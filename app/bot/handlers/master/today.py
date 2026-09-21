from contextlib import suppress
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.domain.enums import AppointmentStatus, UserRole
from app.bot.filters.filters import UserRoleFilter
from app.bot.keyboards.hub import get_hub_home_kb
from app.bot.keyboards.master import (
    MasterAppointmentCallback,
    get_appointment_actions_kb,
    is_slot_past,
)
from app.bot.utils.hub_registry import register
from app.bot.utils.notify import notify_appointment
from app.bot.utils.format import (
    client_contact,
    format_time,
    local_today_bounds,
    status_label,
)
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


today_router = Router(name="master_today")
today_router.message.filter(UserRoleFilter(UserRole.MASTER))
today_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))


async def send_today(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    from_dt, to_dt = local_today_bounds(bot_timezone)
    now = datetime.now(timezone.utc)
    appointments = await repos.appointments.list_by_master(
        master_user_id=user.user_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    active = [
        a for a in appointments
        if a.status in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
    ]
    if not active:
        await message.answer(text=i18n.get("master_today_empty"))
        return

    await message.answer(text=i18n.get("master_today_header"))
    for appointment in active:
        service = await repos.services.get_service(
            service_id=appointment.service_id,
        )
        title = service.title if service else "?"
        when = format_time(appointment.starts_at, bot_timezone)
        client = await repos.users.get_user_by_id(user_id=appointment.client_user_id)
        client_name, client_phone = client_contact(client)

        slot_ends_at = appointment.ends_at
        past = is_slot_past(slot_ends_at=slot_ends_at, now=now)
        item_key = "master_today_item_past" if past else "master_today_item"

        text = i18n.get(item_key).format(
            time=when,
            title=title,
            status=status_label(appointment.status, i18n),
            client_name=client_name,
            client_phone=client_phone,
        )
        await message.answer(
            text=text,
            reply_markup=get_appointment_actions_kb(
                appointment=appointment,
                i18n=i18n,
                now=now,
                slot_ends_at=slot_ends_at,
            ),
        )


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
        now=datetime.now(timezone.utc),
    ):
        await callback.answer(
            text=i18n.get("master_action_past"),
            show_alert=True,
        )
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
        return True
    return False


@today_router.message(Command(commands="today"))
async def process_today_command(
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await send_today(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )


@today_router.callback_query(MasterAppointmentCallback.filter(F.action == "confirm"))
async def process_confirm(
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        bot: Bot,
        translations: dict,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
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
    except (
        AppointmentNotFound, ForbiddenBookingAction, InvalidAppointmentStatus
    ):
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.client_user_id,
        translations=translations,
        text_key="client_booking_confirmed",
        bot_timezone=bot_timezone,
        with_client_hub=True,
    )
    await callback.message.edit_text(
        text=i18n.get("master_confirmed").format(id=appointment.id),
        reply_markup=None,
    )
    await callback.answer()


@today_router.callback_query(MasterAppointmentCallback.filter(F.action == "cancel"))
async def process_cancel(
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        bot: Bot,
        translations: dict,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
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
        appointment = await booking.cancel(
            appointment_id=callback_data.appointment_id,
            actor_user_id=user.user_id,
        )
    except (
        AppointmentNotFound, ForbiddenBookingAction, InvalidAppointmentStatus
    ):
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.client_user_id,
        translations=translations,
        text_key="client_booking_cancelled_by_master",
        bot_timezone=bot_timezone,
        with_client_hub=True,
    )
    await callback.message.edit_text(
        text=i18n.get("master_cancelled").format(id=appointment.id),
        reply_markup=None,
    )
    await callback.answer()


@today_router.callback_query(MasterAppointmentCallback.filter(F.action == "close"))
async def process_close(
        callback: CallbackQuery,
) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()


async def _hub_today(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None or bot_timezone is None:
        return
    await state.update_data(hub_screen="today", hub_back="root")
    await message.edit_text(
        text=i18n.get("hub_today_opened"),
        reply_markup=get_hub_home_kb(i18n),
    )
    await send_today(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )


register("today", _hub_today)
