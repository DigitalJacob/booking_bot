from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.services import (
    MasterServiceCallback,
    MasterServiceNavCallback,
    get_services_list_kb,
    get_service_card_kb,
    get_service_fsm_cancel_kb,
)
from app.bot.states.states import AddServiceSG, EditServiceSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import Service, User
from app.infrastructure.database.repositories import Repositories


services_router = Router(name="master_services")
services_router.message.filter(UserRoleFilter(UserRole.MASTER))
services_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


async def show_services_list(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        edit: bool,
) -> None:
    services = await repos.services.list_by_master(
        master_user_id=user.user_id,
        active_only=False,
    )
    if services:
        body = "\n".join(_format_service_line(s, i18n) for s in services)
        text = i18n.get("services_list_header") + "\n\n" + body
    else:
        text = i18n.get("services_empty")

    kb = get_services_list_kb(services=services, i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def _show_service_card(
        *,
        message: Message,
        service: Service,
        i18n: dict[str, str],
) -> None:
    status = (
        i18n.get("services_status_active")
        if service.is_active
        else i18n.get("services_status_inactive")
    )
    text = i18n.get("services_card").format(
        title=service.title,
        duration=service.duration_minutes,
        price=_format_price(service.price, i18n),
        status=status,
    )
    await message.edit_text(
        text=text,
        reply_markup=get_service_card_kb(service=service, i18n=i18n),
    )


# ---------------------------------------------------------------------------
# List / card UI
# ---------------------------------------------------------------------------

@services_router.callback_query(MasterServiceCallback.filter())
async def process_service_open(
        callback: CallbackQuery,
        callback_data: MasterServiceCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await repos.services.get_service(
        service_id=callback_data.service_id
    )
    if service is None or service.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("services_not_found"),
            show_alert=True
        )
        return
    await _show_service_card(
        message=callback.message,
        service=service,
        i18n=i18n,
    )
    await callback.answer()


@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "back"))
async def process_services_back(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    await show_services_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=True,
    )
    await callback.answer()


@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "close"))
async def process_services_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
) -> None:
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "toggle"),
)
async def process_service_toggle(
        callback: CallbackQuery,
        callback_data: MasterServiceNavCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await repos.services.get_service(
        service_id=callback_data.service_id,
    )
    if service is None or service.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("services_not_found"),
            show_alert=True,
        )
        return

    updated = await repos.services.set_active(
        service_id=service.id,
        master_user_id=user.user_id,
        is_active=not service.is_active,
    )
    if updated is None:
        await callback.answer(
            text=i18n.get("services_not_found"),
            show_alert=True,
        )
        return

    await callback.answer(
        text=(
            i18n.get("services_activated")
            if updated.is_active
            else i18n.get("services_deactivated")
        ),
    )
    await _show_service_card(
        message=callback.message,
        service=updated,
        i18n=i18n,
    )


# ---------------------------------------------------------------------------
# Add service FSM
# ---------------------------------------------------------------------------

@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "add"))
async def process_services_add_button(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await state.set_state(AddServiceSG.title)
    await callback.message.edit_text(
        text=i18n.get("add_service_enter_title"),
        reply_markup=get_service_fsm_cancel_kb(i18n),
    )
    await callback.answer()


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "cancel"),
    StateFilter(AddServiceSG, EditServiceSG),
)
async def process_service_fsm_cancel(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await show_services_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=True,
    )
    await callback.answer()


@services_router.message(StateFilter(AddServiceSG.title))
async def process_add_service_title(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 100:
        await message.answer(
            text=i18n.get("add_service_invalid_title"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(title=title)
    await state.set_state(AddServiceSG.duration)
    await message.answer(
        text=i18n.get("add_service_enter_duration"),
        reply_markup=get_service_fsm_cancel_kb(i18n),
    )


@services_router.message(StateFilter(AddServiceSG.duration))
async def process_add_service_duration(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            text=i18n.get("add_service_invalid_duration"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    duration_minutes = int(text)
    if duration_minutes <= 0:
        await message.answer(
            text=i18n.get("add_service_invalid_duration"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(duration_minutes=duration_minutes)
    await state.set_state(AddServiceSG.price)
    await message.answer(
        text=i18n.get("add_service_enter_price"),
        reply_markup=get_service_fsm_cancel_kb(i18n),
    )


@services_router.message(StateFilter(AddServiceSG.price))
async def process_add_service_price(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    try:
        price = _parse_price(message.text or "")
    except InvalidOperation:
        await message.answer(
            text=i18n.get("add_service_invalid_price"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    data = await state.get_data()
    service = await repos.services.add_service(
        master_user_id=user.user_id,
        title=data["title"],
        duration_minutes=data["duration_minutes"],
        price=price,
    )

    await clear_state_keep_hub(state)
    await message.answer(
        text=i18n.get("add_service_ok").format(
            title=service.title,
            duration=service.duration_minutes,
            price=_format_price(service.price, i18n),
        ),
    )
    await show_services_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
    )


# ---------------------------------------------------------------------------
# Edit service FSM
# ---------------------------------------------------------------------------

@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "edit"))
async def process_service_edit(
        callback: CallbackQuery,
        callback_data: MasterServiceNavCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await repos.services.get_service(service_id=callback_data.service_id)
    if service is None or service.master_user_id != user.user_id:
        await callback.answer(text=i18n.get("services_not_found"), show_alert=True)
        return

    await clear_state_keep_hub(state)
    await state.update_data(service_id=service.id)
    await state.set_state(EditServiceSG.title)
    await callback.message.edit_text(
        text=i18n.get("edit_service_enter_title").format(title=service.title),
        reply_markup=get_service_fsm_cancel_kb(i18n),
    )
    await callback.answer()


@services_router.message(StateFilter(EditServiceSG.title))
async def process_edit_service_title(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 100:
        await message.answer(
            text=i18n.get("add_service_invalid_title"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(title=title)

    data = await state.get_data()
    service = await repos.services.get_service(service_id=data["service_id"])
    if service is None or service.master_user_id != user.user_id:
        await message.answer(text=i18n.get("services_not_found"))
        await clear_state_keep_hub(state)
        return

    await state.set_state(EditServiceSG.duration)
    await message.answer(
        text=i18n.get("edit_service_enter_duration").format(
            duration=service.duration_minutes,
        ),
        reply_markup=get_service_fsm_cancel_kb(i18n),
    )


@services_router.message(StateFilter(EditServiceSG.duration))
async def process_edit_service_duration(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            text=i18n.get("add_service_invalid_duration"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    duration_minutes = int(text)
    if duration_minutes <= 0:
        await message.answer(
            text=i18n.get("add_service_invalid_duration"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(duration_minutes=duration_minutes)

    data = await state.get_data()
    service = await repos.services.get_service(service_id=data["service_id"])
    if service is None or service.master_user_id != user.user_id:
        await message.answer(text=i18n.get("services_not_found"))
        await clear_state_keep_hub(state)
        return

    await state.set_state(EditServiceSG.price)
    await message.answer(
        text=i18n.get("edit_service_enter_price").format(
            price=_format_price(service.price, i18n),
        ),
        reply_markup=get_service_fsm_cancel_kb(i18n),
    )


@services_router.message(StateFilter(EditServiceSG.price))
async def process_edit_service_price(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    try:
        price = _parse_price(message.text or "")
    except InvalidOperation:
        await message.answer(
            text=i18n.get("add_service_invalid_price"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    data = await state.get_data()
    service = await repos.services.update(
        service_id=data["service_id"],
        master_user_id=user.user_id,
        title=data["title"],
        duration_minutes=data["duration_minutes"],
        price=price,
    )
    if service is None:
        await message.answer(text=i18n.get("services_not_found"))
        await clear_state_keep_hub(state)
        return

    await clear_state_keep_hub(state)
    await message.answer(
        text=i18n.get("edit_service_ok").format(
            title=service.title,
            duration=service.duration_minutes,
            price=_format_price(service.price, i18n),
        ),
    )
    await show_services_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
    )


async def _hub_services(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None:
        return
    await state.update_data(
        hub_screen="services",
        hub_back="root",
        list_return="root",
    )
    await show_services_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=True,
    )


register("services", _hub_services)
