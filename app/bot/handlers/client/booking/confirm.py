"""Confirm, cancel, back, and text catch-all for client booking."""

from datetime import datetime

from aiogram import Bot, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.client.booking.router import booking_router
from app.bot.handlers.common.booking_nav import handle_booking_back
from app.bot.keyboards.booking import BookingNavCallback
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.states.states import BookingSG
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub
from app.bot.utils.notify import notify_appointment
from app.domain.exceptions import (
    ServiceInactive,
    ServiceNotFound,
    TimeConflict,
    WindowNotAvailable,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


@booking_router.message(StateFilter(BookingSG), F.text)
async def process_booking_text(
    message: Message,
    i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("book_use_buttons"))


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "confirm"),
    StateFilter(BookingSG.confirming),
)
async def process_confirm(
    callback: CallbackQuery,
    bot: Bot,
    translations: dict,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        await clear_state_keep_hub(state)
        return

    fsm_data = await state.get_data()
    booking = BookingService(repos)
    try:
        appointment = await booking.book_window(
            client_user_id=user.user_id,
            service_id=fsm_data["service_id"],
            starts_at=datetime.fromisoformat(fsm_data["starts_at"]),
            schedule_mode=schedule_mode,
        )
    except (TimeConflict, WindowNotAvailable):
        await callback.answer(text=i18n.get("book_window_taken"), show_alert=True)
        return
    except ServiceInactive:
        await callback.answer(
            text=i18n.get("book_service_inactive"),
            show_alert=True,
        )
        return
    except ServiceNotFound:
        await callback.answer(
            text=i18n.get("book_service_not_found"),
            show_alert=True,
        )
        return

    notify_msg_id = await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.master_user_id,
        translations=translations,
        text_key="master_new_booking",
        with_master_actions=True,
        bot_timezone=bot_timezone,
    )
    if notify_msg_id is not None:
        await repos.appointments.set_master_notify_message_id(
            appointment_id=appointment.id,
            message_id=notify_msg_id,
        )
    await clear_state_keep_hub(state)
    await callback.message.edit_text(
        text=i18n.get("book_ok"),
        reply_markup=get_hub_dismiss_kb(i18n),
    )
    await callback.answer()


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "cancel"),
    StateFilter(BookingSG),
)
async def process_cancel(
    callback: CallbackQuery,
    i18n: dict[str, str],
    state: FSMContext,
    user: User | None,
) -> None:
    await clear_state_keep_hub(state)
    await show_hub(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "back"),
    StateFilter(BookingSG),
)
async def process_back(
    callback: CallbackQuery,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await handle_booking_back(
        callback=callback,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=BookingSG,
    )
