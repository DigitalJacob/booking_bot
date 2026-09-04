import logging
from contextlib import suppress

from aiogram import Bot, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BotCommandScopeChat

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories
from app.bot.i18n.translator import resolve_i18n
from app.bot.keyboards.menu_button import get_main_menu_commands


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


def _parse_role(command: CommandObject) -> UserRole | None:
    if command.args is None:
        return None
    parts = command.args.split()
    if len(parts) < 2:
        return None
    try:
        return UserRole(parts[1].lower())
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


@admin_users_router.message(Command(commands="set_role"))
async def process_set_role_command(
        message: Message,
        command: CommandObject,
        bot: Bot,
        translations: dict,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    target = await _get_target(
        message=message,
        command=command,
        repos=repos,
        i18n=i18n,
        usage_key="admin_usage_set_role",
    )
    if target is None:
        return

    role = _parse_role(command)
    if role is None:
        await message.answer(
            text=i18n.get("admin_invalid_role").format(
                roles=", ".join(item.value for item in UserRole),
            ),
        )
        return

    if target.user_id == user.user_id and role != UserRole.ADMIN:
        await message.answer(text=i18n.get("admin_demote_self"))
        return

    if target.role == role:
        await message.answer(
            text=i18n.get("admin_role_unchanged").format(
                user_id=target.user_id,
                role=role.value,
            ),
        )
        return

    await repos.users.change_user_role(user_id=target.user_id, role=role)
    logger.info(
        "Admin %d changed role of user %d to '%s'",
        user.user_id,
        target.user_id,
        role,
    )

    target_i18n = resolve_i18n(
        language=target.language,
        translations=translations,
    )
    with suppress(TelegramBadRequest, TelegramForbiddenError):
        await bot.set_my_commands(
            commands=get_main_menu_commands(i18n=target_i18n, role=role),
            scope=BotCommandScopeChat(
                type=BotCommandScopeType.CHAT,
                chat_id=target.user_id,
            ),
        )
        await bot.send_message(
            chat_id=target.user_id,
            text=target_i18n.get("admin_role_changed_notice").format(
                role=role.value,
            ),
        )

    await message.answer(
        text=i18n.get("admin_role_set").format(
            user_id=target.user_id,
            role=role.value,
        ),
    )
