from decimal import InvalidOperation

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.services.common import (
    DESCRIPTION_MAX,
    card_description,
    card_photo,
    dismiss_aux_message,
    dismiss_photo_preview,
    format_price,
    load_owned_service,
    parse_price,
    prompt_on_sticky,
    send_service_card,
)
from app.bot.handlers.master.services.list import show_services_list
from app.bot.handlers.master.services.router import services_router
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.services import (
    MasterServiceNavCallback,
    get_service_description_kb,
    get_service_fsm_cancel_kb,
    get_service_photo_kb,
)
from app.bot.states.states import (
    AddServiceSG,
    EditServiceSG,
    ServiceDescriptionSG,
    ServicePhotoSG,
)
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub_prompt
from app.bot.utils.telegram import delete_user_input
from app.domain.models import Service, User
from app.infrastructure.database.repositories import Repositories


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
    await send_service_card(message=message, service=service, i18n=i18n)
    await message.answer(text=notice, reply_markup=get_hub_dismiss_kb(i18n))


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
    if not title or len(title) > 100:
        await message.answer(
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
    service = await load_owned_service(
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
    try:
        price = parse_price(message.text or "")
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
    await state.set_state(ServiceDescriptionSG.value)
    await prompt_on_sticky(
        message=callback.message,
        state=state,
        text=i18n.get("services_enter_description").format(
            max=DESCRIPTION_MAX,
            description=card_description(service, i18n),
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
    await delete_user_input(message)
    if not text or len(text) > DESCRIPTION_MAX:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("services_invalid_description").format(
                max=DESCRIPTION_MAX,
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
    await state.set_state(ServicePhotoSG.value)
    await dismiss_aux_message(callback.message, state)

    prompt = i18n.get("services_enter_photo").format(
        photo=card_photo(service, i18n),
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
        await prompt_on_sticky(
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
    await dismiss_aux_message(callback.message, state)
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
    await delete_user_input(message)
    await dismiss_photo_preview(message, state)
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
    await delete_user_input(message)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("services_invalid_photo"),
        reply_markup=get_service_photo_kb(i18n),
    )
