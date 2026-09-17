from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.keyboards.schedule import (
    ScheduleNavCallback,
    format_interval_line,
    get_schedule_list_kb,
)
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


schedule_router = Router(name="master_schedule")
schedule_router.message.filter(UserRoleFilter(UserRole.MASTER))
schedule_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))


async def _show_schedule(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        edit: bool,
) -> None:
    rows = await repos.working_hours.list_by_master(
        master_user_id=user.user_id,
    )
    if rows:
        body = "\n".join(format_interval_line(row, i18n) for row in rows)
        text = i18n.get("schedule_header") + "\n\n" + body
    else:
        text = i18n.get("schedule_empty")

    kb = get_schedule_list_kb(i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@schedule_router.message(Command(commands="schedule"))
async def process_schedule_command(
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    await _show_schedule(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        edit=False,
    )


@schedule_router.callback_query(
    ScheduleNavCallback.filter(F.action == "close"),
)
async def process_schedule_close(
        callback: CallbackQuery,
        i18n: dict[str, str],
) -> None:
    await callback.message.edit_text(text=i18n.get("schedule_closed"))
    await callback.answer()
