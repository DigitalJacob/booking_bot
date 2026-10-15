from __future__ import annotations

from decimal import InvalidOperation

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.services.common import (
    format_price,
    load_owned_service,
    parse_price,
    prompt_on_sticky,
)
from app.bot.handlers.master.services.list import show_services_list
from app.bot.handlers.master.services.router import services_router
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.services import (
    MasterServiceNavCallback,
    get_service_fsm_cancel_kb,
)
from app.bot.states.states import EditServiceSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.telegram import delete_user_input
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "edit"))
async def process_service_edit(
    callback: CallbackQuery,
    callback_data: MasterServiceNavCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    service = await load_owned_service(
        repos=repos,
        user=user,
        service_id=callback_data.service_id,
    )
    if service is None:
        await callback.answer(text=i18n.get("services_not_found"), show_alert=True)
        return

    await clear_state_keep_hub(state)
    await state.update_data(service_id=service.id)
    await state.set_state(EditServiceSG.title)
    await prompt_on_sticky(
        message=callback.message,
        state=state,
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
    await delete_user_input(message)
    if not title or len(title) > 100:
        await prompt_on_sticky(
            message=message,
            state=state,
            text=i18n.get("add_service_invalid_title"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(title=title)

    data = await state.get_data()
    service = await load_owned_service(
        repos=repos,
        user=user,
        service_id=data["service_id"],
    )
    if service is None:
        await clear_state_keep_hub(state)
        await prompt_on_sticky(
            message=message,
            state=state,
            text=i18n.get("services_not_found"),
            reply_markup=get_hub_dismiss_kb(i18n),
        )
        return

    await state.set_state(EditServiceSG.duration)
    await prompt_on_sticky(
        message=message,
        state=state,
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
    await delete_user_input(message)
    if not text.isdigit() or int(text) <= 0:
        await prompt_on_sticky(
            message=message,
            state=state,
            text=i18n.get("add_service_invalid_duration"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(duration_minutes=int(text))

    data = await state.get_data()
    service = await load_owned_service(
        repos=repos,
        user=user,
        service_id=data["service_id"],
    )
    if service is None:
        await clear_state_keep_hub(state)
        await prompt_on_sticky(
            message=message,
            state=state,
            text=i18n.get("services_not_found"),
            reply_markup=get_hub_dismiss_kb(i18n),
        )
        return

    await state.set_state(EditServiceSG.price)
    await prompt_on_sticky(
        message=message,
        state=state,
        text=i18n.get("edit_service_enter_price").format(
            price=format_price(service.price, i18n),
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
    raw = message.text or ""
    await delete_user_input(message)
    try:
        price = parse_price(raw)
    except InvalidOperation:
        await prompt_on_sticky(
            message=message,
            state=state,
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
        await clear_state_keep_hub(state)
        await prompt_on_sticky(
            message=message,
            state=state,
            text=i18n.get("services_not_found"),
            reply_markup=get_hub_dismiss_kb(i18n),
        )
        return

    await clear_state_keep_hub(state)
    await show_services_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
        state=state,
        prefer_sticky=True,
    )
    await message.answer(
        text=i18n.get("edit_service_ok").format(
            title=service.title,
            duration=service.duration_minutes,
            price=format_price(service.price, i18n),
        ),
        reply_markup=get_hub_dismiss_kb(i18n),
    )
