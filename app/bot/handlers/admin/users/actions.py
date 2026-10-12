"""Ban / unban / set-role mutations for admin user moderation."""

from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import Bot
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BotCommandScopeChat

from app.bot.bot_commands import get_main_menu_commands
from app.bot.i18n.translator import resolve_i18n
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories

logger = logging.getLogger(__name__)


async def apply_ban(
    *,
    repos: Repositories,
    actor: User,
    target: User,
    i18n: dict[str, str],
) -> tuple[bool, str]:
    if target.user_id == actor.user_id:
        return False, i18n.get("admin_ban_self")
    if target.role in (UserRole.ADMIN, UserRole.MASTER):
        return False, i18n.get("admin_ban_staff")
    if target.banned:
        return False, i18n.get("admin_already_banned").format(
            user_id=target.user_id,
        )

    await repos.users.change_user_banned_status(
        user_id=target.user_id,
        banned=True,
    )
    logger.info("Admin %d banned user %d", actor.user_id, target.user_id)
    return True, i18n.get("admin_banned").format(user_id=target.user_id)


async def apply_unban(
    *,
    repos: Repositories,
    actor: User,
    target: User,
    i18n: dict[str, str],
) -> tuple[bool, str]:
    if not target.banned:
        return False, i18n.get("admin_not_banned").format(user_id=target.user_id)

    await repos.users.change_user_banned_status(
        user_id=target.user_id,
        banned=False,
    )
    logger.info("Admin %d unbanned user %d", actor.user_id, target.user_id)
    return True, i18n.get("admin_unbanned").format(user_id=target.user_id)


async def apply_set_role(
    *,
    bot: Bot,
    translations: dict,
    repos: Repositories,
    actor: User,
    target: User,
    role: UserRole,
    i18n: dict[str, str],
    bot_timezone: str,
) -> tuple[bool, str]:
    if target.user_id == actor.user_id and role != UserRole.ADMIN:
        return False, i18n.get("admin_demote_self")

    if target.role == role:
        return False, i18n.get("admin_role_unchanged").format(
            user_id=target.user_id,
            role=role,
        )

    await repos.users.change_user_role(user_id=target.user_id, role=role)

    if role == UserRole.MASTER:
        await repos.master_settings.ensure_defaults(
            master_user_id=target.user_id,
            timezone=bot_timezone,
        )

    logger.info(
        "Admin %d changed role of user %d to '%s'",
        actor.user_id,
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
                role=role,
            ),
            reply_markup=get_hub_dismiss_kb(target_i18n),
        )

    return True, i18n.get("admin_role_set").format(
        user_id=target.user_id,
        role=role,
    )
