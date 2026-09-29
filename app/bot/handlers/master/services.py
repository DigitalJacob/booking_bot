from contextlib import suppress
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.services import (
    MasterServiceCallback,
    MasterServiceNavCallback,
    get_services_list_kb,
    get_service_card_kb,
    get_service_fsm_cancel_kb,
    get_service_description_kb,
    get_service_photo_kb,
)
from app.bot.states.states import (
    AddServiceSG,
    EditServiceSG,
    ServiceDescriptionSG,
    ServicePhotoSG,
)
from app.bot.utils.hub_nav import (
    HUB_MESSAGE_ID_KEY,
    clear_state_keep_hub,
    show_hub_prompt,
)
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import Service, User
from app.infrastructure.database.repositories import Repositories


services_router = Router(name="master_services")
services_router.message.filter(UserRoleFilter(UserRole.MASTER))
services_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

_DESCRIPTION_MAX = 1000
_CAPTION_MAX = 1024


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _delete_user_input(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()


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


def _card_description(service: Service, i18n: dict[str, str]) -> str:
    if service.description:
        return service.description
    return i18n.get("services_description_empty")


def _card_photo(service: Service, i18n: dict[str, str]) -> str:
    if service.photo_file_id:
        return i18n.get("services_photo_yes")
    return i18n.get("services_photo_no")


def _truncate_caption(text: str) -> str:
    if len(text) <= _CAPTION_MAX:
        return text
    return text[: _CAPTION_MAX - 3] + "..."


def _service_card_text(service: Service, i18n: dict[str, str]) -> str:
    status = (
        i18n.get("services_status_active")
        if service.is_active
        else i18n.get("services_status_inactive")
    )
    if service.photo_file_id:
        text = i18n.get("services_card_media").format(
            title=service.title,
            duration=service.duration_minutes,
            price=_format_price(service.price, i18n),
            status=status,
            description=_card_description(service, i18n),
        )
    else:
        text = i18n.get("services_card").format(
            title=service.title,
            duration=service.duration_minutes,
            price=_format_price(service.price, i18n),
            status=status,
            description=_card_description(service, i18n),
            photo=_card_photo(service, i18n),
        )
    return _truncate_caption(text)


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
        body = "\n".join(_format_service_line(s, i18n) for s in services)
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
        try:
            await message.edit_text(text=text, reply_markup=kb)
        except TelegramBadRequest:
            await message.answer(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def _dismiss_photo_preview(
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


async def _dismiss_aux_message(
        message: Message,
        state: FSMContext,
) -> None:
    """Delete a card/preview that is not the sticky hub message."""
    await _dismiss_photo_preview(message, state)
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    if sticky_id is not None and message.message_id != int(sticky_id):
        with suppress(TelegramBadRequest):
            await message.delete()


async def _send_service_card(
        *,
        message: Message,
        service: Service,
        i18n: dict[str, str],
) -> None:
    """Open service card as a new message (with photo when set)."""
    text = _service_card_text(service, i18n)
    kb = get_service_card_kb(service=service, i18n=i18n)
    if service.photo_file_id:
        await message.answer_photo(
            photo=service.photo_file_id,
            caption=text,
            reply_markup=kb,
        )
    else:
        await message.answer(text=text, reply_markup=kb)


async def _refresh_service_card(
        *,
        message: Message,
        service: Service,
        i18n: dict[str, str],
) -> None:
    """Update an existing card message after toggle / clear."""
    text = _service_card_text(service, i18n)
    kb = get_service_card_kb(service=service, i18n=i18n)
    if message.photo:
        if service.photo_file_id:
            try:
                await message.edit_caption(caption=text, reply_markup=kb)
                return
            except TelegramBadRequest as exc:
                if _is_not_modified(exc):
                    return
        with suppress(TelegramBadRequest):
            await message.delete()
        await _send_service_card(message=message, service=service, i18n=i18n)
        return

    if service.photo_file_id:
        with suppress(TelegramBadRequest):
            await message.delete()
        await _send_service_card(message=message, service=service, i18n=i18n)
        return

    try:
        await message.edit_text(text=text, reply_markup=kb)
    except TelegramBadRequest as exc:
        if _is_not_modified(exc):
            return
        await _send_service_card(message=message, service=service, i18n=i18n)


async def _prompt_on_sticky(
        *,
        message: Message,
        state: FSMContext,
        text: str,
        reply_markup,
) -> None:
    """Show an FSM prompt on the sticky hub; drop a non-sticky card first."""
    await _dismiss_aux_message(message, state)
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
            if _is_not_modified(exc):
                return
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=reply_markup,
    )


async def _finish_media_edit(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        service: Service,
        notice: str,
) -> None:
    """After description/photo save: restore list, show card, dismissable OK."""
    await show_services_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
        state=state,
        prefer_sticky=True,
    )
    await _send_service_card(message=message, service=service, i18n=i18n)
    await message.answer(text=notice, reply_markup=get_hub_dismiss_kb(i18n))


async def _load_owned_service(
        *,
        repos: Repositories,
        user: User,
        service_id: int,
) -> Service | None:
    service = await repos.services.get_service(service_id=service_id)
    if service is None or service.master_user_id != user.user_id:
        return None
    return service


@services_router.callback_query(MasterServiceCallback.filter())
async def process_service_open(
        callback: CallbackQuery,
        callback_data: MasterServiceCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await _load_owned_service(
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
    await _send_service_card(
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
    await _dismiss_aux_message(callback.message, state)
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
    service = await _load_owned_service(
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
    await _refresh_service_card(
        message=callback.message,
        service=updated,
        i18n=i18n,
    )


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
    await _dismiss_aux_message(callback.message, state)
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
        service = await _load_owned_service(
            repos=repos,
            user=user,
            service_id=int(service_id),
        )
        if service is not None:
            await _send_service_card(
                message=callback.message,
                service=service,
                i18n=i18n,
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


@services_router.callback_query(MasterServiceNavCallback.filter(F.action == "edit"))
async def process_service_edit(
        callback: CallbackQuery,
        callback_data: MasterServiceNavCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await _load_owned_service(
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
    await _prompt_on_sticky(
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
    if not title or len(title) > 100:
        await message.answer(
            text=i18n.get("add_service_invalid_title"),
            reply_markup=get_service_fsm_cancel_kb(i18n),
        )
        return

    await state.update_data(title=title)

    data = await state.get_data()
    service = await _load_owned_service(
        repos=repos,
        user=user,
        service_id=data["service_id"],
    )
    if service is None:
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
    service = await _load_owned_service(
        repos=repos,
        user=user,
        service_id=data["service_id"],
    )
    if service is None:
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


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "description"),
)
async def process_service_description(
        callback: CallbackQuery,
        callback_data: MasterServiceNavCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await _load_owned_service(
        repos=repos,
        user=user,
        service_id=callback_data.service_id,
    )
    if service is None:
        await callback.answer(text=i18n.get("services_not_found"), show_alert=True)
        return

    await clear_state_keep_hub(state)
    await state.update_data(service_id=service.id)
    await state.set_state(ServiceDescriptionSG.value)
    await _prompt_on_sticky(
        message=callback.message,
        state=state,
        text=i18n.get("services_enter_description").format(
            max=_DESCRIPTION_MAX,
            description=_card_description(service, i18n),
        ),
        reply_markup=get_service_description_kb(i18n),
    )
    await callback.answer()


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "clear_description"),
    StateFilter(ServiceDescriptionSG),
)
async def process_service_clear_description(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    service = await repos.services.update_description(
        service_id=data["service_id"],
        master_user_id=user.user_id,
        description=None,
    )
    await clear_state_keep_hub(state)
    if service is None:
        await callback.answer(text=i18n.get("services_not_found"), show_alert=True)
        return
    await callback.answer()
    await _finish_media_edit(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        service=service,
        notice=i18n.get("services_description_cleared"),
    )


@services_router.message(StateFilter(ServiceDescriptionSG.value))
async def process_service_description_value(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    text = (message.text or "").strip()
    await _delete_user_input(message)
    if not text or len(text) > _DESCRIPTION_MAX:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("services_invalid_description").format(
                max=_DESCRIPTION_MAX,
            ),
            reply_markup=get_service_description_kb(i18n),
        )
        return

    data = await state.get_data()
    service = await repos.services.update_description(
        service_id=data["service_id"],
        master_user_id=user.user_id,
        description=text,
    )
    await clear_state_keep_hub(state)
    if service is None:
        await message.answer(
            text=i18n.get("services_not_found"),
            reply_markup=get_hub_dismiss_kb(i18n),
        )
        return

    await _finish_media_edit(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        service=service,
        notice=i18n.get("services_description_saved"),
    )


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "photo"),
)
async def process_service_photo(
        callback: CallbackQuery,
        callback_data: MasterServiceNavCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    service = await _load_owned_service(
        repos=repos,
        user=user,
        service_id=callback_data.service_id,
    )
    if service is None:
        await callback.answer(text=i18n.get("services_not_found"), show_alert=True)
        return

    await clear_state_keep_hub(state)
    await state.update_data(service_id=service.id)
    await state.set_state(ServicePhotoSG.value)
    await _dismiss_aux_message(callback.message, state)

    prompt = i18n.get("services_enter_photo").format(
        photo=_card_photo(service, i18n),
    )
    kb = get_service_photo_kb(i18n)
    if service.photo_file_id:
        # Preview current photo while waiting for a replacement.
        sent = await callback.message.answer_photo(
            photo=service.photo_file_id,
            caption=prompt,
            reply_markup=kb,
        )
        await state.update_data(service_photo_preview_id=sent.message_id)
    else:
        await _prompt_on_sticky(
            message=callback.message,
            state=state,
            text=prompt,
            reply_markup=kb,
        )
    await callback.answer()


@services_router.callback_query(
    MasterServiceNavCallback.filter(F.action == "clear_photo"),
    StateFilter(ServicePhotoSG),
)
async def process_service_clear_photo(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    service = await repos.services.update_photo_file_id(
        service_id=data["service_id"],
        master_user_id=user.user_id,
        photo_file_id=None,
    )
    await _dismiss_aux_message(callback.message, state)
    await clear_state_keep_hub(state)
    if service is None:
        await callback.answer(text=i18n.get("services_not_found"), show_alert=True)
        return
    await callback.answer()
    await _finish_media_edit(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        service=service,
        notice=i18n.get("services_photo_cleared"),
    )


@services_router.message(StateFilter(ServicePhotoSG.value), F.photo)
async def process_service_photo_value(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    photo_file_id = message.photo[-1].file_id
    data = await state.get_data()
    service = await repos.services.update_photo_file_id(
        service_id=data["service_id"],
        master_user_id=user.user_id,
        photo_file_id=photo_file_id,
    )
    await _delete_user_input(message)
    await _dismiss_photo_preview(message, state)
    await clear_state_keep_hub(state)
    if service is None:
        await message.answer(
            text=i18n.get("services_not_found"),
            reply_markup=get_hub_dismiss_kb(i18n),
        )
        return

    await _finish_media_edit(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        service=service,
        notice=i18n.get("services_photo_saved"),
    )


@services_router.message(StateFilter(ServicePhotoSG.value))
async def process_service_photo_invalid(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await _delete_user_input(message)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("services_invalid_photo"),
        reply_markup=get_service_photo_kb(i18n),
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
