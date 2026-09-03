from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.domain.enums import AppointmentStatus, UserRole
from app.bot.filters.filters import UserRoleFilter
from app.bot.keyboards.master import MasterAppointmentCallback, get_appointment_actions_kb
from app.bot.utils.notify import notify_appointment
from app.bot.utils.format import status_label
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


def _today_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


async def _send_today(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    from_dt, to_dt = _today_bounds()
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
        slot = await repos.slots.get_slot(slot_id=appointment.slot_id)
        title = service.title if service else "?"
        when = slot.starts_at.strftime("%H:%M") if slot else "?"
        text = i18n.get("master_today_item").format(
            time=when,
            title=title,
            status=status_label(appointment.status, i18n),
            client_id=appointment.client_user_id,
        )
        await message.answer(
            text=text,
            reply_markup=get_appointment_actions_kb(
                appointment=appointment,
                i18n=i18n,
            ),
        )


@today_router.message(Command(commands="today"))
async def process_today_command(
        message: Message,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        return
    await _send_today(message=message, repos=repos, user=user, i18n=i18n)


@today_router.callback_query(MasterAppointmentCallback.filter(F.action == "confirm"))
async def process_confirm(
        bot: Bot,
        translations: dict,
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
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
    )
    await callback.message.edit_text(
        text=i18n.get("master_confirmed").format(id=appointment.id),
        reply_markup=None,
    )
    await callback.answer()


@today_router.callback_query(MasterAppointmentCallback.filter(F.action == "cancel"))
async def process_cancel(
        bot: Bot,
        translations: dict,
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
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
