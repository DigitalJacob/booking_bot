from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.domain.enums import UserRole
from app.bot.filters.filters import UserRoleFilter
from app.bot.states.states import AddServiceSG
from app.domain.models import Service, User
from app.infrastructure.database.repositories import Repositories


services_router = Router(name="master_services")
services_router.message.filter(UserRoleFilter(UserRole.MASTER))


def _format_price(price: Decimal | None, i18n: dict[str, str]) -> str:
    if price is None:
        return i18n.get("services_price_empty")
    return f"{price:.2f}"


def _format_service_line(service: Service, i18n: dict[str, str]) -> str:
    status = (
        i18n.get("services_status_active")
        if service.is_active
        else i18n.get("services_status_inactive")
    )
    return i18n.get("services_list_item").format(
        title=service.title,
        duration=service.duration_minutes,
        price=_format_price(service.price, i18n),
        status=status,
    )


def _parse_price(value: str) -> Decimal | None:
    value = value.strip()
    if value in ("", "-", "—"):
        return None
    normalized = value.replace(",", ".")
    return Decimal(normalized)


@services_router.message(Command(commands="services"))
async def process_services_command(
        message: Message,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        return

    services = await repos.services.list_by_master(
        master_user_id=user.user_id,
        active_only=False,
    )
    if not services:
        await message.answer(text=i18n.get("services_empty"))
        return

    lines = [_format_service_line(service, i18n) for service in services]
    text = i18n.get("services_list_header") + "\n\n" + "\n".join(lines)
    text += "\n\n" + i18n.get("services_add_hint")
    await message.answer(text=text)


@services_router.message(Command(commands="add_service"))
async def process_add_service_command(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        user: User | None,
) -> None:
    if user is None:
        return

    await state.clear()
    await state.set_state(AddServiceSG.title)
    await message.answer(text=i18n.get("add_service_enter_title"))


@services_router.message(Command(commands="cancel"), StateFilter(AddServiceSG))
async def process_add_service_cancel(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.clear()
    await message.answer(text=i18n.get("add_service_cancelled"))


@services_router.message(StateFilter(AddServiceSG.title))
async def process_add_service_title(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 100:
        await message.answer(text=i18n.get("add_service_invalid_title"))
        return

    await state.update_data(title=title)
    await state.set_state(AddServiceSG.duration)
    await message.answer(text=i18n.get("add_service_enter_duration"))


@services_router.message(StateFilter(AddServiceSG.duration))
async def process_add_service_duration(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(text=i18n.get("add_service_invalid_duration"))
        return

    duration_minutes = int(text)
    if duration_minutes <= 0:
        await message.answer(text=i18n.get("add_service_invalid_duration"))
        return

    await state.update_data(duration_minutes=duration_minutes)
    await state.set_state(AddServiceSG.price)
    await message.answer(text=i18n.get("add_service_enter_price"))


@services_router.message(StateFilter(AddServiceSG.price))
async def process_add_service_price(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await state.clear()
        return

    try:
        price = _parse_price(message.text or "")
    except InvalidOperation:
        await message.answer(text=i18n.get("add_service_invalid_price"))
        return

    data = await state.get_data()
    service = await repos.services.add_service(
        master_user_id=user.user_id,
        title=data["title"],
        duration_minutes=data["duration_minutes"],
        price=price,
    )

    await state.clear()
    await message.answer(
        text=i18n.get("add_service_ok").format(
            title=service.title,
            duration=service.duration_minutes,
            price=_format_price(service.price, i18n),
        ),
    )
