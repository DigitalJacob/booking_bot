from datetime import date
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.booking import (
    BookingNavCallback,
    DayCallback,
    ServiceCallback,
    SlotCallback,
    get_confirm_kb,
    get_days_kb,
    get_services_kb,
    get_slots_kb,
)
from app.bot.states.states import BookingSG
from app.domain.exceptions import (
    ServiceInactive,
    ServiceNotFound,
    SlotInThePast,
    SlotMasterMismatch,
    SlotNotFound,
    SlotTaken,
)
from app.domain.models import Service, Slot, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


booking_router = Router(name="client_booking")


def _format_price(price: Decimal | None, i18n: dict[str, str]) -> str:
    if price is None:
        return i18n.get("book_price_empty")
    return f"{price:.2f}"


def _unique_days(slots: list[Slot]) -> list[date]:
    return sorted({slot.starts_at.date() for slot in slots})


def _slots_on_day(slots: list[Slot], day: date) -> list[Slot]:
    return [slot for slot in slots if slot.starts_at.date() == day]


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


async def _show_slots(
        *,
        message: Message,
        slots: list[Slot],
        i18n: dict[str, str],
) -> None:
    await message.edit_text(
        text=i18n.get("book_choose_slot"),
        reply_markup=get_slots_kb(slots=slots, i18n=i18n),
    )


async def _show_confirm(
        *,
        message: Message,
        service: Service,
        slot: Slot,
        i18n: dict[str, str],
) -> None:
    text = i18n.get("book_confirm").format(
        title=service.title,
        when=slot.starts_at.strftime("%d.%m.%Y %H:%M"),
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
    slots = await booking.list_available_slots(master_user_id=master_user_id)
    days = _unique_days(slots)
    if not days:
        await callback.answer()
        await callback.message.edit_text(text=i18n.get("book_no_slots"))
        await state.clear()
        return

    await state.update_data(service_id=service.id)
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
) -> None:
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    day = date.fromisoformat(callback_data.value)

    booking = BookingService(repos)
    slots = _slots_on_day(
        await booking.list_available_slots(master_user_id=master_user_id),
        day,
    )
    if not slots:
        await callback.answer(
            text=i18n.get("book_no_slots"),
            show_alert=True,
        )
        return

    await state.update_data(day=day.isoformat())
    await state.set_state(BookingSG.choosing_slot)
    await _show_slots(message=callback.message, slots=slots, i18n=i18n)
    await callback.answer()


@booking_router.callback_query(
    SlotCallback.filter(),
    StateFilter(BookingSG.choosing_slot),
)
async def process_slot_choice(
        callback: CallbackQuery,
        callback_data: SlotCallback,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
) -> None:
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_id = fsm_data["service_id"]
    day = date.fromisoformat(fsm_data["day"])

    service = await repos.services.get_service(service_id=service_id)
    slot = await repos.slots.get_slot(slot_id=callback_data.slot_id)
    if service is None:
        await callback.answer(
            text=i18n.get("book_service_not found"),
            show_alert=True,
        )
        return
    if (
        slot is None
        or slot.master_user_id != master_user_id
        or slot.starts_at.date() != day
    ):
        await callback.answer(
            text=i18n.get("book_slot_not_found"),
            show_alert=True,
        )
        return

    await state.update_data(slot_id=slot.id)
    await state.set_state(BookingSG.confirming)
    await _show_confirm(
        message=callback.message,
        service=service,
        slot=slot,
        i18n=i18n,
    )
    await callback.answer()


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "confirm"),
    StateFilter(BookingSG.confirming),
)
async def process_confirm(
        callback: CallbackQuery,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        user: User | None,
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
        await booking.book(
            client_user_id=user.user_id,
            service_id=fsm_data["service_id"],
            slot_id=fsm_data["slot_id"],
        )
    except SlotTaken:
        await callback.answer(
            text=i18n.get("book_slot_taken"),
            show_alert=True
        )
        return
    except SlotInThePast:
        await callback.answer(
            text=i18n.get("book_slot_past"),
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
    except SlotNotFound:
        await callback.answer(
            text=i18n.get("book_slot_not_found"),
            show_alert=True,
        )
        return
    except SlotMasterMismatch:
        await callback.answer(
            text=i18n.get("book_mismatch"),
            show_alert=True,
        )
        return

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
) -> None:
    current = await state.get_state()
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    booking = BookingService(repos)

    if current == BookingSG.choosing_day.state:
        services = await booking.list_services(master_user_id=master_user_id)
        await state.set_state(BookingSG.choosing_service)
        await state.update_data(service_id=None, day=None, slot_id=None)
        await _show_services(
            message=callback.message,
            services=services,
            i18n=i18n,
            edit=True,
        )
        await callback.answer()
        return

    if current == BookingSG.choosing_slot.state:
        slots = await booking.list_available_slots(master_user_id=master_user_id)
        days = _unique_days(slots)
        await state.set_state(BookingSG.choosing_day)
        await state.update_data(day=None, slot_id=None)
        if not days:
            await callback.message.edit_text(text=i18n.get("book_no_slots"))
            await state.clear()
        else:
            await _show_days(message=callback.message, days=days, i18n=i18n)
        await callback.answer()
        return

    if current == BookingSG.confirming.state:
        day = date.fromisoformat(fsm_data["day"])
        slots = _slots_on_day(
            await booking.list_available_slots(master_user_id=master_user_id),
            day,
        )
        await state.set_state(BookingSG.choosing_slot)
        await state.update_data(slot_id=None)
        if not slots:
            await callback.answer(text=i18n.get("book_no_slots"), show_alert=True)
            return
        await _show_slots(message=callback.message, slots=slots, i18n=i18n)
        await callback.answer()
        return

    await callback.answer()
