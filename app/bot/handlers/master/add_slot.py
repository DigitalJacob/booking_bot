from datetime import datetime, date, time, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from psycopg.errors import UniqueViolation

from app.bot.enums import UserRole
from app.bot.filters.filters import UserRoleFilter
from app.bot.states.states import AddSlotSG
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


add_slot_router = Router(name="master_add_slot")
add_slot_router.message.filter(UserRoleFilter(UserRole.MASTER, UserRole.ADMIN))
add_slot_router.callback_query.filter(UserRoleFilter(UserRole.MASTER, UserRole.ADMIN))


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


@add_slot_router.message(Command(commands="add_slot"))
async def process_add_slot_command(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        user: User | None,
) -> None:
    if user is None:
        return
    await state.clear()
    await state.set_state(AddSlotSG.date)
    await message.answer(text=i18n.get("add_slot_enter_date"))


@add_slot_router.message(Command(commands="cancel"), StateFilter(AddSlotSG))
async def process_add_slot_cancel(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.clear()
    await message.answer(text=i18n.get("add_slot_cancelled"))


@add_slot_router.message(StateFilter(AddSlotSG.date))
async def process_add_slot_date(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    day = _parse_date(message.text or "")
    if day is None:
        await message.answer(text=i18n.get("add_slot_invalid_date"))
        return
    await state.update_data(day=day.isoformat())
    await state.set_state(AddSlotSG.start_time)
    await message.answer(text=i18n.get("add_slot_enter_time"))


@add_slot_router.message(StateFilter(AddSlotSG.start_time))
async def process_add_slot_time(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    time_part = _parse_time(message.text or "")
    if time_part is None:
        await message.answer(text=i18n.get("add_slot_invalid_time"))
        return
    await state.update_data(start_time=time_part.strftime("%H:%M"))
    await state.set_state(AddSlotSG.duration)
    await message.answer(text=i18n.get("add_slot_enter_duration"))


@add_slot_router.message(StateFilter(AddSlotSG.duration))
async def process_add_slot_duration(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await state.clear()
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(text=i18n.get("add_slot_invalid_duration"))
        return

    duration_minutes = int(text)
    if duration_minutes <= 0:
        await message.answer(text=i18n.get("add_slot_invalid_duration"))
        return

    data = await state.get_data()
    day = datetime.fromisoformat(data["day"]).date()
    time_part = datetime.strptime(data["start_time"], "%H:%M").time()
    starts_at = datetime.combine(day, time_part, tzinfo=timezone.utc)
    ends_at = starts_at + timedelta(minutes=duration_minutes)

    if starts_at <= datetime.now(timezone.utc):
        await message.answer(text=i18n.get("add_slot_past"))
        return

    try:
        slot = await repos.slots.add_slot(
            master_user_id=user.user_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
    except UniqueViolation:
        await message.answer(text=i18n.get("add_slot_duplicate"))
        return

    await state.clear()
    await message.answer(
        text=i18n.get("add_slot_ok").format(
            when=slot.starts_at.strftime("%d.%m.%Y %H:%M"),
            duration=duration_minutes,
        ),
    )
