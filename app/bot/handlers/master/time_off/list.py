from __future__ import annotations

from contextlib import suppress

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.hub import return_from_list
from app.bot.handlers.master.time_off.common import (
    is_breaks_mode,
    list_from_dt,
)
from app.bot.handlers.master.time_off.router import time_off_router
from app.bot.keyboards.time_off import (
    TimeOffConfirmCallback,
    TimeOffDeleteCallback,
    TimeOffNavCallback,
    format_time_off_line,
    get_time_off_confirm_delete_kb,
    get_time_off_edit_kb,
)
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY
from app.bot.utils.hub_registry import register
from app.bot.utils.telegram import is_not_modified
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def show_time_off_list(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
        state: FSMContext | None = None,
        prefer_sticky: bool = False,
        schedule_mode: str = "weekly",
) -> None:
    rows = await repos.time_off.list_by_master(
        master_user_id=user.user_id,
        from_dt=list_from_dt(bot_timezone),
    )
    if is_breaks_mode(schedule_mode):
        header_key = "time_off_breaks_header"
        empty_key = "time_off_breaks_empty"
    else:
        header_key = "time_off_header"
        empty_key = "time_off_empty"
    if rows:
        body = "\n".join(
            format_time_off_line(row, i18n, bot_timezone) for row in rows
        )
        text = i18n.get(header_key) + "\n\n" + body
    else:
        text = i18n.get(empty_key)

    kb = get_time_off_edit_kb(
        rows=rows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )

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
                # Sticky gone or not editable — fall through and re-point.
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


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "close"))
async def process_time_off_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
        schedule_mode: str,
) -> None:
    """Back → hub schedule section."""
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffDeleteCallback.filter())
async def process_time_off_delete(
        callback: CallbackQuery,
        callback_data: TimeOffDeleteCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    row = await repos.time_off.get(
        time_off_id=callback_data.time_off_id,
    )
    if row is None or row.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("time_off_delete_not_found"),
            show_alert=True,
        )
        return

    item = format_time_off_line(row, i18n, bot_timezone).lstrip("• ").strip()
    confirm_key = (
        "time_off_breaks_confirm_delete"
        if is_breaks_mode(schedule_mode)
        else "time_off_confirm_delete"
    )
    await callback.message.edit_text(
        text=i18n.get(confirm_key).format(item=item),
        reply_markup=get_time_off_confirm_delete_kb(
            time_off_id=row.id,
            i18n=i18n,
        ),
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffConfirmCallback.filter(F.action == "yes"),
)
async def process_time_off_delete_yes(
        callback: CallbackQuery,
        callback_data: TimeOffConfirmCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    deleted = await repos.time_off.delete(
        time_off_id=callback_data.time_off_id,
        master_user_id=user.user_id,
    )
    if not deleted:
        await callback.answer(
            text=i18n.get("time_off_delete_not_found"),
            show_alert=True,
        )
        return
    deleted_key = (
        "time_off_breaks_deleted"
        if is_breaks_mode(schedule_mode)
        else "time_off_deleted"
    )
    await callback.answer(text=i18n.get(deleted_key))
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        schedule_mode=schedule_mode,
    )


@time_off_router.callback_query(
    TimeOffConfirmCallback.filter(F.action == "no"),
)
async def process_time_off_delete_no(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


async def _hub_time_off(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        schedule_mode: str = "weekly",
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None or bot_timezone is None:
        return
    await state.update_data(
        hub_screen="time_off",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_time_off_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        state=state,
        schedule_mode=schedule_mode,
    )


register("time_off", _hub_time_off)
