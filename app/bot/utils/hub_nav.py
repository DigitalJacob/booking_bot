from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.hub import get_hub_root_kb
from app.domain.enums import UserRole
from app.domain.models import User


HUB_MESSAGE_ID_KEY = "hub_message_id"


def _role(user: User | None) -> UserRole:
    return user.role if user else UserRole.CLIENT


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def clear_state_keep_hub(state: FSMContext) -> None:
    """Clear FSM but keep the sticky hub message id."""
    data = await state.get_data()
    hub_id = data.get(HUB_MESSAGE_ID_KEY)
    await state.clear()
    if hub_id is not None:
        await state.update_data({HUB_MESSAGE_ID_KEY: hub_id})


async def show_hub(
        *,
        message: Message,
        user: User | None,
        i18n: dict[str, str],
        state: FSMContext,
        force_new: bool = False,
) -> int:
    """
    Show root hub on a single sticky message when possible.
    Returns the hub message_id in use.

    force_new=True: always send a new message (for /start so the user sees
    a reply at the bottom of the chat) and point sticky at it.
    """
    await state.update_data(hub_screen="root", hub_back="root", list_return="root")
    text = i18n.get("hub_title")
    kb = get_hub_root_kb(role=_role(user), i18n=i18n)

    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    bot = message.bot
    chat_id = message.chat.id

    if not force_new and sticky_id is not None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=sticky_id,
                text=text,
                reply_markup=kb,
            )
            return int(sticky_id)
        except TelegramBadRequest as exc:
            if _is_not_modified(exc):
                return int(sticky_id)
            # Sticky gone or not editable — fall through.

    if not force_new:
        try:
            await message.edit_text(text=text, reply_markup=kb)
            await state.update_data({HUB_MESSAGE_ID_KEY: message.message_id})
            return message.message_id
        except TelegramBadRequest as exc:
            if _is_not_modified(exc):
                await state.update_data({HUB_MESSAGE_ID_KEY: message.message_id})
                return message.message_id

    # Drop keyboard on the previous sticky so old menus are inert.
    if sticky_id is not None:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=sticky_id,
                reply_markup=None,
            )
        except TelegramBadRequest:
            pass

    sent = await message.answer(text=text, reply_markup=kb)
    await state.update_data({HUB_MESSAGE_ID_KEY: sent.message_id})
    return sent.message_id
