from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest

from app.bot.handlers.master.bookings.actions import (
    build_master_booking_card,
    build_master_new_booking_push,
    disarm_stale_master_push,
    resume_master_after_cancel,
)
from app.bot.handlers.master.bookings.common import DAY_KEY, back_to_from_state
from app.bot.handlers.master.bookings.list import build_master_bookings_day
from app.bot.utils.cancel_registry import (
    SOURCE_MASTER_BOOKINGS,
    SOURCE_MASTER_PUSH,
    CancelResumeCtx,
    CancelSourceHooks,
)
from app.bot.utils.cancel_registry import (
    register as register_cancel_source,
)
from app.bot.utils.format import to_local


def _cancel_appointment_id(ctx: CancelResumeCtx) -> int | None:
    if ctx.appointment is not None:
        return ctx.appointment.id
    return ctx.appointment_id


async def _cancel_edit_day(ctx: CancelResumeCtx) -> None:
    if ctx.appointment is None or ctx.state is None:
        return
    day = to_local(ctx.appointment.starts_at, ctx.bot_timezone).date()
    back_to = await back_to_from_state(ctx.state)
    await ctx.state.update_data({DAY_KEY: day.isoformat()})
    text, kb = await build_master_bookings_day(
        repos=ctx.repos,
        user=ctx.user,
        i18n=ctx.i18n,
        bot_timezone=ctx.bot_timezone,
        day=day,
        back_to=back_to,
    )
    with suppress(TelegramBadRequest):
        await ctx.bot.edit_message_text(
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            text=text,
            reply_markup=kb,
        )


async def _cancel_bookings_on_abort(ctx: CancelResumeCtx) -> None:
    if ctx.appointment is None:
        return
    text, kb = await build_master_booking_card(
        appointment=ctx.appointment,
        repos=ctx.repos,
        i18n=ctx.i18n,
        bot_timezone=ctx.bot_timezone,
    )
    with suppress(TelegramBadRequest):
        await ctx.bot.edit_message_text(
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            text=text,
            reply_markup=kb,
        )


async def _cancel_push_on_abort(ctx: CancelResumeCtx) -> None:
    if ctx.appointment is None or ctx.callback is None:
        return
    _, text, kb = await build_master_new_booking_push(
        appointment=ctx.appointment,
        repos=ctx.repos,
        translations=ctx.translations,
        bot_timezone=ctx.bot_timezone,
    )
    with suppress(TelegramBadRequest):
        await ctx.callback.message.edit_text(text=text, reply_markup=kb)


async def _cancel_master_on_success(ctx: CancelResumeCtx) -> None:
    if ctx.appointment is None or ctx.state is None:
        return
    await resume_master_after_cancel(
        bot=ctx.bot,
        chat_id=ctx.chat_id,
        message_id=ctx.message_id,
        state=ctx.state,
        repos=ctx.repos,
        user=ctx.user,
        i18n=ctx.i18n,
        bot_timezone=ctx.bot_timezone,
        appointment=ctx.appointment,
        source=ctx.source,
    )
    if ctx.callback is not None:
        if ctx.mode == "cancel":
            ack = ctx.i18n.get("master_cancelled").format(id=ctx.appointment.id)
        else:
            ack = ctx.i18n.get("decline_done")
        await ctx.callback.answer(text=ack)


async def _cancel_push_on_unavailable(ctx: CancelResumeCtx) -> None:
    if ctx.callback is None:
        return
    appointment_id = _cancel_appointment_id(ctx)
    if appointment_id is None:
        return
    await disarm_stale_master_push(
        callback=ctx.callback,
        bot=ctx.bot,
        repos=ctx.repos,
        appointment_id=appointment_id,
        translations=ctx.translations,
        bot_timezone=ctx.bot_timezone,
    )


register_cancel_source(
    SOURCE_MASTER_BOOKINGS,
    CancelSourceHooks(
        on_abort=_cancel_bookings_on_abort,
        on_success=_cancel_master_on_success,
        on_unavailable=_cancel_edit_day,
    ),
)
register_cancel_source(
    SOURCE_MASTER_PUSH,
    CancelSourceHooks(
        on_abort=_cancel_push_on_abort,
        on_success=_cancel_master_on_success,
        on_unavailable=_cancel_push_on_unavailable,
    ),
)
