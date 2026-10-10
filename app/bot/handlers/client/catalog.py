from contextlib import suppress
from decimal import Decimal

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.catalog import (
    CatalogNavCallback,
    CatalogServiceCallback,
    get_catalog_card_kb,
    get_catalog_list_kb,
)
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import Service, User
from app.infrastructure.database.repositories import Repositories

catalog_router = Router(name="client_catalog")

_CAPTION_MAX = 1024


def _format_price(price: Decimal | None, i18n: dict[str, str]) -> str:
    if price is None:
        return i18n.get("catalog_price_empty")
    return f"{price:.2f}"


def _card_body(service: Service, i18n: dict[str, str]) -> str:
    lines = [
        service.title,
        i18n.get("catalog_card_duration").format(
            duration=service.duration_minutes,
        ),
        i18n.get("catalog_card_price").format(
            price=_format_price(service.price, i18n),
        ),
    ]
    if service.description:
        lines.extend(["", service.description])
    text = "\n".join(lines)
    if len(text) > _CAPTION_MAX:
        return text[: _CAPTION_MAX - 3] + "..."
    return text


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def show_catalog_list(
        *,
        message: Message,
        repos: Repositories,
        master_user_id: int,
        i18n: dict[str, str],
        edit: bool,
        state: FSMContext | None = None,
        prefer_sticky: bool = False,
) -> None:
    services = await repos.services.list_by_master(
        master_user_id=master_user_id,
        active_only=True,
    )
    if services:
        text = i18n.get("catalog_header")
        kb = get_catalog_list_kb(services=services, i18n=i18n)
    else:
        text = i18n.get("catalog_empty")
        kb = get_catalog_list_kb(services=[], i18n=i18n)

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
                if _is_not_modified(exc):
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
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@catalog_router.callback_query(CatalogNavCallback.filter(F.action == "close"))
async def process_catalog_close(
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


@catalog_router.callback_query(CatalogServiceCallback.filter())
async def process_catalog_open(
        callback: CallbackQuery,
        callback_data: CatalogServiceCallback,
        repos: Repositories,
        master_user_id: int,
        i18n: dict[str, str],
) -> None:
    service = await repos.services.get_service(
        service_id=callback_data.service_id,
    )
    if (
            service is None
            or service.master_user_id != master_user_id
            or not service.is_active
    ):
        await callback.answer(
            text=i18n.get("catalog_not_found"),
            show_alert=True,
        )
        return

    body = _card_body(service, i18n)
    kb = get_catalog_card_kb(i18n)
    if service.photo_file_id:
        await callback.message.answer_photo(
            photo=service.photo_file_id,
            caption=body,
            reply_markup=kb,
        )
    else:
        await callback.message.answer(text=body, reply_markup=kb)
    await callback.answer()


@catalog_router.callback_query(CatalogNavCallback.filter(F.action == "back_list"))
async def process_catalog_back_list(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        master_user_id: int,
        i18n: dict[str, str],
) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.delete()
    await show_catalog_list(
        message=callback.message,
        repos=repos,
        master_user_id=master_user_id,
        i18n=i18n,
        edit=False,
        state=state,
        prefer_sticky=True,
    )
    await callback.answer()


async def _hub_catalog(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        master_user_id: int | None = None,
        **_,
) -> None:
    if (
            user.role != UserRole.CLIENT
            or repos is None
            or master_user_id is None
    ):
        return
    await state.update_data(
        hub_screen="catalog",
        hub_back="root",
        list_return="root",
    )
    await show_catalog_list(
        message=message,
        repos=repos,
        master_user_id=master_user_id,
        i18n=i18n,
        edit=True,
    )


register("catalog", _hub_catalog)
