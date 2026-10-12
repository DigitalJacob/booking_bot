"""Shared helpers for admin user moderation prompts and lookup."""

from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards.admin import get_admin_cancel_kb
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.utils.format import format_dt
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub, show_hub
from app.bot.utils.telegram import is_not_modified
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def show_admin_prompt(
    *,
    message: Message,
    state: FSMContext,
    text: str,
    i18n: dict[str, str],
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Show FSM prompt on the sticky hub message when possible."""
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    kb = reply_markup if reply_markup is not None else get_admin_cancel_kb(i18n)

    if sticky_id is not None:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=sticky_id,
                text=text,
                reply_markup=kb,
            )
            return
        except TelegramBadRequest as exc:
            if is_not_modified(exc):
                return

    await message.answer(text=text, reply_markup=kb)


async def finish_admin_flow(
    *,
    message: Message,
    state: FSMContext,
    user: User,
    i18n: dict[str, str],
    result_text: str,
) -> None:
    """Restore sticky hub, then send a dismissible result notice."""
    await clear_state_keep_hub(state)
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await message.answer(
        text=result_text,
        reply_markup=get_hub_dismiss_kb(i18n),
    )


async def cancel_admin_flow(
    *,
    message: Message,
    state: FSMContext,
    user: User,
    i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
    )


async def lookup_user_ref(
    *,
    repos: Repositories,
    raw: str,
) -> User | None:
    raw = raw.strip()
    if not raw:
        return None
    if raw.isdigit():
        return await repos.users.get_user_by_id(user_id=int(raw))
    return await repos.users.get_user_by_username(username=raw)


def user_card(target: User, i18n: dict[str, str], bot_timezone: str) -> str:
    return i18n.get("admin_user_card").format(
        user_id=target.user_id,
        username=f"@{target.username}" if target.username else i18n.get("admin_no_username"),
        first_name=target.first_name or "-",
        last_name=target.last_name or "-",
        phone=target.phone or "-",
        role=target.role,
        language=target.language,
        banned=i18n.get("admin_yes") if target.banned else i18n.get("admin_no"),
        created_at=format_dt(target.created_at, bot_timezone),
    )
