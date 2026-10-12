from __future__ import annotations

from decimal import InvalidOperation

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.services.common import format_price, parse_price
from app.bot.handlers.master.services.list import show_services_list
from app.bot.handlers.master.services.router import services_router
from app.bot.keyboards.services import (
    MasterServiceNavCallback,
    get_service_fsm_cancel_kb,
)
from app.bot.states.states import AddServiceSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


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
        price = parse_price(message.text or "")
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
            price=format_price(service.price, i18n),
        ),
    )
    await show_services_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
    )
