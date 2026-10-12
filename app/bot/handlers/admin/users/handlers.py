import logging
from contextlib import suppress

from aiogram import Bot, F
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, CallbackQuery, Message

from app.bot.bot_commands import get_main_menu_commands
from app.bot.handlers.admin.users.common import (
    cancel_admin_flow,
    finish_admin_flow,
    lookup_user_ref,
    show_admin_prompt,
    user_card,
)
from app.bot.handlers.admin.users.router import admin_users_router
from app.bot.i18n.translator import resolve_i18n
from app.bot.keyboards.admin import (
    AdminNavCallback,
    AdminRoleCallback,
    get_admin_role_kb,
)
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.states.states import AdminModSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.bot.utils.telegram import delete_user_input
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories

logger = logging.getLogger(__name__)


async def _apply_ban(
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


async def _apply_unban(
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


async def _apply_set_role(
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


async def start_admin_mod_flow(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
    action: str,
) -> None:
    """Start guided moderation FSM from hub (action: user|ban|unban|set_role)."""
    await clear_state_keep_hub(state)
    await state.set_state(AdminModSG.target)
    await state.update_data(admin_action=action)
    await show_admin_prompt(
        message=message,
        state=state,
        text=i18n.get("admin_hub_ask_target"),
        i18n=i18n,
    )


@admin_users_router.callback_query(
    AdminNavCallback.filter(F.action == "cancel"),
    StateFilter(AdminModSG),
)
async def process_admin_mod_cancel_cb(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    i18n: dict[str, str],
) -> None:
    await callback.answer()
    await cancel_admin_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
    )


@admin_users_router.message(StateFilter(AdminModSG.target))
async def process_admin_mod_target(
    message: Message,
    state: FSMContext,
    bot: Bot,
    translations: dict,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    raw = (message.text or "").strip()
    await delete_user_input(message)

    if not raw:
        await show_admin_prompt(
            message=message,
            state=state,
            text=i18n.get("admin_hub_ask_target"),
            i18n=i18n,
        )
        return

    target = await lookup_user_ref(repos=repos, raw=raw)
    if target is None:
        await show_admin_prompt(
            message=message,
            state=state,
            text=i18n.get("admin_user_not_found").format(target=raw),
            i18n=i18n,
        )
        return

    data = await state.get_data()
    action = data.get("admin_action")

    if action == "user":
        await finish_admin_flow(
            message=message,
            state=state,
            user=user,
            i18n=i18n,
            result_text=user_card(target, i18n, bot_timezone),
        )
        return

    if action == "ban":
        ok, text = await _apply_ban(
            repos=repos,
            actor=user,
            target=target,
            i18n=i18n,
        )
        if ok:
            await finish_admin_flow(
                message=message,
                state=state,
                user=user,
                i18n=i18n,
                result_text=text,
            )
        else:
            await show_admin_prompt(
                message=message,
                state=state,
                text=text,
                i18n=i18n,
            )
        return

    if action == "unban":
        ok, text = await _apply_unban(
            repos=repos,
            actor=user,
            target=target,
            i18n=i18n,
        )
        if ok:
            await finish_admin_flow(
                message=message,
                state=state,
                user=user,
                i18n=i18n,
                result_text=text,
            )
        else:
            await show_admin_prompt(
                message=message,
                state=state,
                text=text,
                i18n=i18n,
            )
        return

    if action == "set_role":
        await state.update_data(target_user_id=target.user_id)
        await state.set_state(AdminModSG.role)
        await show_admin_prompt(
            message=message,
            state=state,
            text=i18n.get("admin_hub_ask_role").format(
                user_id=target.user_id,
            ),
            i18n=i18n,
            reply_markup=get_admin_role_kb(i18n),
        )
        return

    await cancel_admin_flow(
        message=message,
        state=state,
        user=user,
        i18n=i18n,
    )


@admin_users_router.callback_query(
    AdminRoleCallback.filter(),
    StateFilter(AdminModSG.role),
)
async def process_admin_mod_role(
    callback: CallbackQuery,
    callback_data: AdminRoleCallback,
    state: FSMContext,
    bot: Bot,
    translations: dict,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    try:
        role = UserRole(callback_data.role)
    except ValueError:
        await callback.answer(
            text=i18n.get("admin_invalid_role").format(
                roles=", ".join(UserRole),
            ),
            show_alert=True,
        )
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if target_user_id is None:
        await callback.answer()
        await cancel_admin_flow(
            message=callback.message,
            state=state,
            user=user,
            i18n=i18n,
        )
        return

    target = await repos.users.get_user_by_id(user_id=int(target_user_id))
    if target is None:
        await state.set_state(AdminModSG.target)
        await show_admin_prompt(
            message=callback.message,
            state=state,
            text=i18n.get("admin_user_not_found").format(target=target_user_id),
            i18n=i18n,
        )
        await callback.answer()
        return

    ok, text = await _apply_set_role(
        bot=bot,
        translations=translations,
        repos=repos,
        actor=user,
        target=target,
        role=role,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    if ok:
        await finish_admin_flow(
            message=callback.message,
            state=state,
            user=user,
            i18n=i18n,
            result_text=text,
        )
    else:
        await callback.answer(text=text, show_alert=True)
        return
    await callback.answer()


def _register_admin_leaf(hub_action: str, mod_action: str) -> None:
    async def _hub(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        **_,
    ) -> None:
        if user.role != UserRole.ADMIN:
            return
        await start_admin_mod_flow(
            message=message,
            state=state,
            i18n=i18n,
            action=mod_action,
        )

    register(hub_action, _hub)


_register_admin_leaf("admin_user", "user")
_register_admin_leaf("admin_ban", "ban")
_register_admin_leaf("admin_unban", "unban")
_register_admin_leaf("admin_set_role", "set_role")
