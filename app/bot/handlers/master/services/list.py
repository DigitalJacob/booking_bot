from __future__ import annotations

from contextlib import suppress

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.hub import return_from_list
from app.bot.handlers.master.services.common import (
    dismiss_aux_message,
    format_service_line,
    load_owned_service,
    refresh_service_card,
    send_service_card,
)
from app.bot.handlers.master.services.router import services_router
from app.bot.keyboards.services import (
    MasterServiceCallback,
    MasterServiceNavCallback,
    get_services_list_kb,
)
from app.bot.states.states import (
    AddServiceSG,
    EditServiceSG,
    ServiceDescriptionSG,
    ServicePhotoSG,
)
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.bot.utils.telegram import is_not_modified
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def show_services_list(
    *,
    message: Message,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    edit: bool,
    state: FSMContext | None = None,
    prefer_sticky: bool = False,
) -> None:
    services = await repos.services.list_by_master(
        master_user_id=user.user_id,
        active_only=False,
    )
    if services:
        body = "\n".join(format_service_line(s, i18n) for s in services)
        text = i18n.get("services_list_header") + "\n\n" + body
    else:
        text = i18n.get("services_empty")

    kb = get_services_list_kb(services=services, i18n=i18n)

    if prefer_sticky and state is not None:
        data = await state.get_data()
        sticky_id = data.get(HUB_MESSAGE_ID_KEY)
        if sticky_id is not None:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=int(sticky_id),
                    text=text,
                    reply_markup=kb,
                )
                return
            except TelegramBadRequest as exc:
                if is_not_modified(exc):
                    return
                with suppress(TelegramBadRequest):
                    await message.bot.edit_message_reply_markup(
                        chat_id=message.chat.id,
                        message_id=int(sticky_id),
                        reply_markup=None,
                    )
        sent = await message.answer(text=text, reply_markup=kb)
        await state.update_data({HUB_MESSAGE_ID_KEY: sent.message_id})
        return

    if edit:
        try:
            await message.edit_text(text=text, reply_markup=kb)
        except TelegramBadRequest:
            await message.answer(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@services_router.callback_query(MasterServiceCallback.filter())
async def process_service_open(
    callback: CallbackQuery,
    callback_data: MasterServiceCallback,
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
        await callback.answer(
            text=i18n.get("services_not_found"),
            show_alert=True,
        )
        return
    await send_service_card(
        message=callback.message,
        service=service,
        i18n=i18n,
    )
    await callback.answer()


@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "back"))
async def process_services_back(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    await dismiss_aux_message(callback.message, state)
    await show_services_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
        state=state,
        prefer_sticky=True,
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
    service = await load_owned_service(
        repos=repos,
        user=user,
        service_id=callback_data.service_id,
    )
    if service is None:
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
    await refresh_service_card(
        message=callback.message,
        service=updated,
        i18n=i18n,
    )


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


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "cancel"),
    StateFilter(ServiceDescriptionSG, ServicePhotoSG),
)
async def process_service_media_fsm_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    service_id = data.get("service_id")
    await dismiss_aux_message(callback.message, state)
    await clear_state_keep_hub(state)
    await show_services_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
        state=state,
        prefer_sticky=True,
    )
    if service_id is not None:
        service = await load_owned_service(
            repos=repos,
            user=user,
            service_id=int(service_id),
        )
        if service is not None:
            await send_service_card(
                message=callback.message,
                service=service,
                i18n=i18n,
            )
    await callback.answer()


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
