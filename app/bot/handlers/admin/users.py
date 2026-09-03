import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


logger = logging.getLogger(__name__)

admin_users_router = Router(name="admin_users")
admin_users_router.message.filter(UserRoleFilter(UserRole.ADMIN))


def _parse_user_id(command: CommandObject) -> int | None:
    if command.args is None:
        return None
    parts = command.args.split()
    if not parts:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


async def _get_target(
        *,
        message: Message,
        command: CommandObject,
        repos: Repositories,
        i18n: dict[str, str],
        usage_key: str,
) -> User | None:
    target_id = _parse_user_id(command)
    if target_id is None:
        await message.answer(text=i18n.get(usage_key))
        return None

    target = await repos.users.get_user(user_id=target_id)
    if target is None:
        await message.answer(
            text=i18n.get("admin_user_not_found").format(user_id=target_id),
        )
        return None
    return target


def _user_card(target: User, i18n: dict[str, str]) -> str:
    return i18n.get("admin_user_card").format(
        user_id=target.user_id,
        username=f"@{target.username}" if target.username
        else i18n.get("admin_no_username"),
        role=target.role.value,
        language=target.language,
        banned=i18n.get("admin_yes") if target.banned else i18n.get("admin_no"),
        created_at=target.created_at.strftime("%d.%m.%Y %H:%M"),
    )


@admin_users_router.message(Command(commands="user"))
async def process_user_command(
        message: Message,
        command: CommandObject,
        repos: Repositories,
        i18n: dict[str, str],
) -> None:
    target = await _get_target(
        message=message,
        command=command,
        repos=repos,
        i18n=i18n,
        usage_key="admin_usage_user",
    )
    if target is None:
        return

    await message.answer(text=_user_card(target, i18n))


@admin_users_router.message(Command(commands="ban"))
async def process_ban_command(
        message: Message,
        command: CommandObject,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    target = await _get_target(
        message=message,
        command=command,
        repos=repos,
        i18n=i18n,
        usage_key="admin_usage_ban",
    )
    if target is None:
        return

    if target.user_id == user.user_id:
        await message.answer(text=i18n.get("admin_ban_self"))
        return
    if target.role in (UserRole.ADMIN, UserRole.MASTER):
        await message.answer(text=i18n.get("admin_ban_staff"))
        return
    if target.banned:
        await message.answer(
            text=i18n.get("admin_already_banned").format(user_id=target.user_id),
        )
        return

    await repos.users.change_user_banned_status(
        user_id=target.user_id,
        banned=True,
    )
    logger.info("Admin %d banned user %d", user.user_id, target.user_id)
    await message.answer(
        text=i18n.get("admin_banned").format(user_id=target.user_id),
    )


@admin_users_router.message(Command(commands="unban"))
async def process_unban_command(
        message: Message,
        command: CommandObject,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    target = await _get_target(
        message=message,
        command=command,
        repos=repos,
        i18n=i18n,
        usage_key="admin_usage_unban",
    )
    if target is None:
        return

    if not target.banned:
        await message.answer(
            text=i18n.get("admin_not_banned").format(user_id=target.user_id),
        )
        return

    await repos.users.change_user_banned_status(
        user_id=target.user_id,
        banned=False,
    )
    logger.info("Admin %d unbanned user %d", user.user_id, target.user_id)
    await message.answer(
        text=i18n.get("admin_unbanned").format(user_id=target.user_id),
    )
