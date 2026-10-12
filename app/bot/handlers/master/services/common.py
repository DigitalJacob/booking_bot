"""Shared helpers for master services catalogue."""

from __future__ import annotations

from contextlib import suppress
from decimal import Decimal

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.services import get_service_card_kb
from app.bot.utils.format import format_price as _format_price
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, show_hub_prompt
from app.bot.utils.telegram import is_not_modified
from app.domain.models import Service, User
from app.infrastructure.database.repositories import Repositories

DESCRIPTION_MAX = 1000
CAPTION_MAX = 1024


def format_price(price: Decimal | None, i18n: dict[str, str]) -> str:
    return _format_price(price, i18n, empty_key="services_price_empty")


def format_service_line(service: Service, i18n: dict[str, str]) -> str:
    status = (
        i18n.get("services_status_active")
        if service.is_active
        else i18n.get("services_status_inactive")
    )
    return i18n.get("services_list_item").format(
        title=service.title,
        duration=service.duration_minutes,
        price=format_price(service.price, i18n),
        status=status,
    )


def parse_price(value: str) -> Decimal | None:
    value = value.strip()
    if value in ("", "-", "—"):
        return None
    normalized = value.replace(",", ".")
    return Decimal(normalized)


def card_description(service: Service, i18n: dict[str, str]) -> str:
    if service.description:
        return service.description
    return i18n.get("services_description_empty")


def card_photo(service: Service, i18n: dict[str, str]) -> str:
    if service.photo_file_id:
        return i18n.get("services_photo_yes")
    return i18n.get("services_photo_no")


def truncate_caption(text: str) -> str:
    if len(text) <= CAPTION_MAX:
        return text
    return text[: CAPTION_MAX - 3] + "..."


def service_card_text(service: Service, i18n: dict[str, str]) -> str:
    status = (
        i18n.get("services_status_active")
        if service.is_active
        else i18n.get("services_status_inactive")
    )
    if service.photo_file_id:
        text = i18n.get("services_card_media").format(
            title=service.title,
            duration=service.duration_minutes,
            price=format_price(service.price, i18n),
            status=status,
            description=card_description(service, i18n),
        )
    else:
        text = i18n.get("services_card").format(
            title=service.title,
            duration=service.duration_minutes,
            price=format_price(service.price, i18n),
            status=status,
            description=card_description(service, i18n),
            photo=card_photo(service, i18n),
        )
    return truncate_caption(text)


async def dismiss_photo_preview(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    preview_id = data.get("service_photo_preview_id")
    if preview_id is None:
        return
    with suppress(TelegramBadRequest):
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=int(preview_id),
        )
    await state.update_data(service_photo_preview_id=None)


async def dismiss_aux_message(
    message: Message,
    state: FSMContext,
) -> None:
    """Delete a card/preview that is not the sticky hub message."""
    await dismiss_photo_preview(message, state)
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    if sticky_id is not None and message.message_id != int(sticky_id):
        with suppress(TelegramBadRequest):
            await message.delete()


async def send_service_card(
    *,
    message: Message,
    service: Service,
    i18n: dict[str, str],
) -> None:
    """Open service card as a new message (with photo when set)."""
    text = service_card_text(service, i18n)
    kb = get_service_card_kb(service=service, i18n=i18n)
    if service.photo_file_id:
        await message.answer_photo(
            photo=service.photo_file_id,
            caption=text,
            reply_markup=kb,
        )
    else:
        await message.answer(text=text, reply_markup=kb)


async def refresh_service_card(
    *,
    message: Message,
    service: Service,
    i18n: dict[str, str],
) -> None:
    """Update an existing card message after toggle / clear."""
    text = service_card_text(service, i18n)
    kb = get_service_card_kb(service=service, i18n=i18n)
    if message.photo:
        if service.photo_file_id:
            try:
                await message.edit_caption(caption=text, reply_markup=kb)
                return
            except TelegramBadRequest as exc:
                if is_not_modified(exc):
                    return
        with suppress(TelegramBadRequest):
            await message.delete()
        await send_service_card(message=message, service=service, i18n=i18n)
        return

    if service.photo_file_id:
        with suppress(TelegramBadRequest):
            await message.delete()
        await send_service_card(message=message, service=service, i18n=i18n)
        return

    try:
        await message.edit_text(text=text, reply_markup=kb)
    except TelegramBadRequest as exc:
        if is_not_modified(exc):
            return
        await send_service_card(message=message, service=service, i18n=i18n)


async def prompt_on_sticky(
    *,
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup,
) -> None:
    """Show an FSM prompt on the sticky hub; drop a non-sticky card first."""
    await dismiss_aux_message(message, state)
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    if sticky_id is not None and message.message_id != int(sticky_id):
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=int(sticky_id),
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest as exc:
            if is_not_modified(exc):
                return
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=reply_markup,
    )


async def load_owned_service(
    *,
    repos: Repositories,
    user: User,
    service_id: int,
) -> Service | None:
    service = await repos.services.get_service(service_id=service_id)
    if service is None or service.master_user_id != user.user_id:
        return None
    return service
