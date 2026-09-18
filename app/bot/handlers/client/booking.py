from datetime import date, datetime
from decimal import Decimal

from aiogram import F, Router, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.booking import (
    BookingNavCallback,
    DayCallback,
    ServiceCallback,
    WindowCallback,
    get_confirm_kb,
    get_days_kb,
    get_services_kb,
    get_windows_kb,
)
from app.bot.states.states import BookingSG
from app.domain.exceptions import (
    ServiceInactive,
    ServiceNotFound,
    WindowNotAvailable,
    TimeConflict,
)
from app.domain.models import Service, TimeWindow, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories
from app.bot.utils.notify import notify_appointment
from app.bot.utils.format import format_dt, to_local
from app.bot.handlers.client.profile import start_profile_flow


booking_router = Router(name="client_booking")


def _format_price(price: Decimal | None, i18n: dict[str, str]) -> str:
    if price is None:
        return i18n.get("book_price_empty")
    return f"{price:.2f}"


def _unique_days(windows: list[TimeWindow], bot_timezone: str) -> list[date]:
    return sorted({
        to_local(window.starts_at, bot_timezone).date()
        for window in windows
    })


def _windows_on_day(
        windows: list[TimeWindow],
        day: date,
        bot_timezone: str,
) -> list[TimeWindow]:
    return [
        window for window in windows
        if to_local(window.starts_at, bot_timezone).date() == day
    ]


async def _show_services(
        *,
        message: Message,
        services: list[Service],
        i18n: dict[str, str],
        edit: bool,
) -> None:
    text = i18n.get("book_choose_service")
    kb = get_services_kb(services=services, i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def _show_days(
        *,
        message: Message,
        days: list[date],
        i18n: dict[str, str],
) -> None:
    await message.edit_text(
        text=i18n.get("book_choose_day"),
        reply_markup=get_days_kb(days=days, i18n=i18n),
    )


async def _show_windows(
        *,
        message: Message,
        windows: list[TimeWindow],
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await message.edit_text(
        text=i18n.get("book_choose_window"),
        reply_markup=get_windows_kb(
            windows=windows,
            i18n=i18n,
            bot_timezone=bot_timezone,
        ),
    )


async def _show_confirm(
        *,
        message: Message,
        service: Service,
        starts_at: datetime,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    text = i18n.get("book_confirm").format(
        title=service.title,
        when=format_dt(starts_at, bot_timezone),
        duration=service.duration_minutes,
        price=_format_price(service.price, i18n),
    )
    await message.edit_text(
        text=text,
        reply_markup=get_confirm_kb(i18n=i18n),
    )


@booking_router.message(Command(commands="book"))
async def process_book_command(
        message: Message,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        master_user_id: int,
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return

    if not user.profile_complete:
        await start_profile_flow(
            message=message,
            state=state,
            i18n=i18n,
            resume_book=True,
        )
        return

    await state.clear()

    booking = BookingService(repos)
    services = await booking.list_services(master_user_id=master_user_id)
    if not services:
        await message.answer(text=i18n.get("book_no_services"))
        return

    await state.set_state(BookingSG.choosing_service)
    await state.update_data(master_user_id=master_user_id)
    await _show_services(
        message=message,
        services=services,
        i18n=i18n,
        edit=False,
    )


@booking_router.message(StateFilter(BookingSG), F.text)
async def process_booking_text(
        message: Message,
        i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("book_use_buttons"))


@booking_router.callback_query(
    ServiceCallback.filter(),
    StateFilter(BookingSG.choosing_service),
)
async def process_service_choice(
        callback: CallbackQuery,
        callback_data: ServiceCallback,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        bot_timezone: str,
) -> None:
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]

    service = await repos.services.get_service(service_id=callback_data.service_id)
    if (
        service is None
        or service.master_user_id != master_user_id
        or not service.is_active
    ):
        await callback.answer(
            text=i18n.get("book_service_not_found"),
            show_alert=True,
        )
        return

    booking = BookingService(repos)
    windows = await booking.list_available_windows(
        master_user_id=master_user_id,
        duration_minutes=service.duration_minutes,
    )
    days = _unique_days(windows, bot_timezone)
    if not days:
        await callback.answer()
        await callback.message.edit_text(text=i18n.get("book_no_windows"))
        await state.clear()
        return

    await state.update_data(
        service_id=service.id,
        service_duration=service.duration_minutes,
    )
    await state.set_state(BookingSG.choosing_day)
    await _show_days(message=callback.message, days=days, i18n=i18n)
    await callback.answer()


@booking_router.callback_query(
    DayCallback.filter(),
    StateFilter(BookingSG.choosing_day),
)
async def process_day_choice(
        callback: CallbackQuery,
        callback_data: DayCallback,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        bot_timezone: str,
) -> None:
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_duration = fsm_data["service_duration"]
    day = date.fromisoformat(callback_data.value)

    booking = BookingService(repos)
    windows = _windows_on_day(
        await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=service_duration,
        ),
        day,
        bot_timezone,
    )
    if not windows:
        await callback.answer(
            text=i18n.get("book_no_windows"),
            show_alert=True,
        )
        return

    await state.update_data(day=day.isoformat())
    await state.set_state(BookingSG.choosing_window)
    await _show_windows(
        message=callback.message,
        windows=windows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@booking_router.callback_query(
    WindowCallback.filter(),
    StateFilter(BookingSG.choosing_window),
)
async def process_window_choice(
        callback: CallbackQuery,
        callback_data: WindowCallback,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        bot_timezone: str,
) -> None:
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_id = fsm_data["service_id"]
    day = date.fromisoformat(fsm_data["day"])
    starts_at = datetime.fromisoformat(callback_data.starts_at)

    service = await repos.services.get_service(service_id=service_id)
    if service is None:
        await callback.answer(
            text=i18n.get("book_service_not_found"),
            show_alert=True,
        )
        return

    booking = BookingService(repos)
    windows = _windows_on_day(
        await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=service.duration_minutes,
        ),
        day,
        bot_timezone,
    )
    match = next(
        (
            window for window in windows
            if window.starts_at == starts_at
            or window.starts_at.isoformat() == callback_data.starts_at
        ),
        None
    )
    if match is None:
        await callback.answer(
            text=i18n.get("book_window_not_found"),
            show_alert=True,
        )
        return

    await state.update_data(starts_at=match.starts_at.isoformat())
    await state.set_state(BookingSG.confirming)
    await _show_confirm(
        message=callback.message,
        service=service,
        starts_at=match.starts_at,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


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
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        await state.clear()
        return

    fsm_data = await state.get_data()
    booking = BookingService(repos)
    try:
        appointment = await booking.book_window(
            client_user_id=user.user_id,
            service_id=fsm_data["service_id"],
            starts_at=datetime.fromisoformat(fsm_data["starts_at"]),
        )
    except (TimeConflict, WindowNotAvailable):
        await callback.answer(
            text=i18n.get("book_window_taken"),
            show_alert=True
        )
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

    await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.master_user_id,
        translations=translations,
        text_key="master_new_booking",
        with_master_actions=True,
        bot_timezone=bot_timezone,
    )
    await state.clear()
    await callback.message.edit_text(text=i18n.get("book_ok"))
    await callback.answer()


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "cancel"),
    StateFilter(BookingSG),
)
async def process_cancel(
        callback: CallbackQuery,
        i18n: dict[str, str],
        state: FSMContext,
) -> None:
    await state.clear()
    await callback.message.edit_text(text=i18n.get("book_cancelled"))
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
) -> None:
    current = await state.get_state()
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    booking = BookingService(repos)

    if current == BookingSG.choosing_day.state:
        services = await booking.list_services(master_user_id=master_user_id)
        await state.set_state(BookingSG.choosing_service)
        await state.update_data(
            service_id=None,
            day=None,
            starts_at=None,
            service_duration=None,
        )
        await _show_services(
            message=callback.message,
            services=services,
            i18n=i18n,
            edit=True,
        )
        await callback.answer()
        return

    if current == BookingSG.choosing_window.state:
        windows = await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=fsm_data["service_duration"],
        )
        days = _unique_days(windows, bot_timezone)
        await state.set_state(BookingSG.choosing_day)
        await state.update_data(day=None, starts_at=None)
        if not days:
            await callback.message.edit_text(text=i18n.get("book_no_windows"))
            await state.clear()
        else:
            await _show_days(message=callback.message, days=days, i18n=i18n)
        await callback.answer()
        return

    if current == BookingSG.confirming.state:
        day = date.fromisoformat(fsm_data["day"])
        windows = _windows_on_day(
            await booking.list_available_windows(
                master_user_id=master_user_id,
                duration_minutes=fsm_data["service_duration"],
            ),
            day,
            bot_timezone,
        )
        await state.set_state(BookingSG.choosing_window)
        await state.update_data(starts_at=None)
        if not windows:
            await callback.answer(text=i18n.get("book_no_windows"), show_alert=True)
            return
        await _show_windows(
            message=callback.message,
            windows=windows,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        await callback.answer()
        return

    await callback.answer()
