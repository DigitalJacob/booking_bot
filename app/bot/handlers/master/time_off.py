from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.keyboards.time_off import (
    TimeOffNavCallback,
    format_time_off_line,
    get_time_off_list_kb,
)
from app.bot.utils.format import get_zone
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


time_off_router = Router(name="master_time_off")
time_off_router.message.filter(UserRoleFilter(UserRole.MASTER))
time_off_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))


def _list_from_dt(bot_timezone: str) -> datetime:
    zone = get_zone(bot_timezone)
    now_local = datetime.now(zone)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


async def _show_time_off(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
) -> None:
    rows = await repos.time_off.list_by_master(
        master_user_id=user.user_id,
        from_dt=_list_from_dt(bot_timezone),
    )
    if rows:
        body = "\n".join(
            format_time_off_line(row, i18n, bot_timezone) for row in rows
        )
        text = i18n.get("time_off_header") + "\n\n" + body
    else:
        text = i18n.get("time_off_empty")

    kb = get_time_off_list_kb(i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@time_off_router.message(Command(commands="time_off"))
async def process_time_off_command(
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _show_time_off(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
    )


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "close"))
async def process_time_off_close(
        callback: CallbackQuery,
        i18n: dict[str, str],
) -> None:
    await callback.message.edit_text(text=i18n.get("time_off_closed"))
    await callback.answer()
