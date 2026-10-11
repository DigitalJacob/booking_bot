from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app.bot.handlers.common.appointment_cancel import start_appointment_cancel
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.reminders import ReminderCallback, get_reminder_kb
from app.bot.reminders import REMINDER_TEXT_KEY_BY_KIND
from app.bot.utils.cancel_registry import (
    SOURCE_REMINDER,
    CancelResumeCtx,
    CancelSourceHooks,
)
from app.bot.utils.cancel_registry import (
    register as register_cancel_source,
)
from app.bot.utils.notify import appointment_notice_parts
from app.domain.enums import AppointmentStatus, parse_reminder_kind
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories

reminder_router = Router(name="reminders")


def _done_key(mode: str) -> str:
    return "decline_done" if mode == "decline" else "cancel_done"


async def _edit_dismissable(ctx: CancelResumeCtx, *, text: str) -> None:
    with suppress(TelegramBadRequest):
        await ctx.bot.edit_message_text(
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            text=text,
            reply_markup=get_hub_dismiss_kb(ctx.i18n),
        )


async def _cancel_on_abort(ctx: CancelResumeCtx) -> None:
    if ctx.appointment is None or ctx.callback is None:
        return
    kind = parse_reminder_kind(ctx.reminder_kind)
    if kind is None:
        return
    text_key = REMINDER_TEXT_KEY_BY_KIND[kind]
    i18n, text = await appointment_notice_parts(
        repos=ctx.repos,
        appointment=ctx.appointment,
        translations=ctx.translations,
        text_key=text_key,
        bot_timezone=ctx.bot_timezone,
        recipient_user_id=ctx.user.user_id,
    )
    with suppress(TelegramBadRequest):
        await ctx.callback.message.edit_text(
            text=text,
            reply_markup=get_reminder_kb(
                i18n=i18n,
                appointment_id=ctx.appointment.id,
                kind=kind,
            ),
        )


async def _cancel_on_success(ctx: CancelResumeCtx) -> None:
    await _edit_dismissable(ctx, text=ctx.i18n.get(_done_key(ctx.mode)))


async def _cancel_on_unavailable(ctx: CancelResumeCtx) -> None:
    text_key = ctx.notice_key or "cancel_unavailable"
    await _edit_dismissable(ctx, text=ctx.i18n.get(text_key))


@reminder_router.callback_query(ReminderCallback.filter(F.action == "cancel"))
async def process_reminder_cancel(
    callback: CallbackQuery,
    callback_data: ReminderCallback,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    translations: dict,
    bot_timezone: str,
) -> None:
    kind = parse_reminder_kind(callback_data.kind)
    if kind is None:
        await callback.answer(
            text=i18n.get("cancel_failed"),
            show_alert=True,
        )
        return

    await start_appointment_cancel(
        callback=callback,
        repos=repos,
        user=user,
        i18n=i18n,
        translations=translations,
        bot_timezone=bot_timezone,
        appointment_id=callback_data.appointment_id,
        source=SOURCE_REMINDER,
        mode="cancel",
        reminder_kind=kind,
        allowed_statuses=frozenset({AppointmentStatus.CONFIRMED}),
    )


register_cancel_source(
    SOURCE_REMINDER,
    CancelSourceHooks(
        on_abort=_cancel_on_abort,
        on_success=_cancel_on_success,
        on_unavailable=_cancel_on_unavailable,
    ),
)
