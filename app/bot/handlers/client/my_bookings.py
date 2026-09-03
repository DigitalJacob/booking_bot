from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.client import (
    ClientAppointmentCallback,
    get_my_booking_actions_kb,
)
from app.bot.utils.format import status_label
from app.bot.utils.notify import notify_appointment
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


my_bookings_router = Router(name="client_my_bookings")


@my_bookings_router.message(Command(commands="my_bookings"))
async def process_my_bookings_command(
        message: Message,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return

    booking = BookingService(repos)
    appointments = await booking.list_client_appointments(
        client_user_id=user.user_id,
    )
    if not appointments:
        await message.answer(text=i18n.get("my_bookings_empty"))
        return

    await message.answer(text=i18n.get("my_bookings_header"))
    for appointment in appointments:
        service = await repos.services.get_service(
            service_id=appointment.service_id,
        )
        slot = await repos.slots.get_slot(slot_id=appointment.slot_id)
        text = i18n.get("my_bookings_item").format(
            when=slot.starts_at.strftime("%d.%m.%Y %H:%M") if slot else "?",
            title=service.title if service else "?",
            status=status_label(appointment.status, i18n),
        )
        await message.answer(
            text=text,
            reply_markup=get_my_booking_actions_kb(
                appointment=appointment,
                i18n=i18n,
            ),
        )


@my_bookings_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "cancel"),
)
async def process_client_cancel(
        bot: Bot,
        translations: dict,
        callback: CallbackQuery,
        callback_data: ClientAppointmentCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
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
            text=i18n.get("my_bookings_action_failed"),
            show_alert=True,
        )
        return

    await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.master_user_id,
        translations=translations,
        text_key="master_booking_cancelled_by_client",
    )
    await callback.message.edit_text(
        text=i18n.get("my_bookings_cancelled"),
        reply_markup=None,
    )
    await callback.answer()


@my_bookings_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "close"),
)
async def process_client_close(
        callback: CallbackQuery,
) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
