from contextlib import suppress
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

from app.bot.i18n.translator import resolve_i18n
from app.bot.keyboards.bookings import get_appointment_actions_kb
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.reminders import get_reminder_kb
from app.bot.utils.format import client_contact, format_dt
from app.domain.enums import ReminderKind
from app.domain.models import Appointment
from app.infrastructure.database.repositories import Repositories


async def appointment_notice_parts(
        *,
        repos: Repositories,
        appointment: Appointment,
        translations: dict,
        text_key: str,
        bot_timezone: str,
        recipient_user_id: int,
        reason: str | None = None,
) -> tuple[dict[str, str], str]:
    recipient = await repos.users.get_user_by_id(user_id=recipient_user_id)
    i18n = resolve_i18n(
        language=recipient.language if recipient else None,
        translations=translations,
    )
    service = await repos.services.get_service(service_id=appointment.service_id)
    client = await repos.users.get_user_by_id(user_id=appointment.client_user_id)
    client_name, client_phone = client_contact(client)
    text = i18n.get(text_key).format(
        title=service.title if service else "?",
        when=format_dt(appointment.starts_at, bot_timezone),
        client_name=client_name,
        client_phone=client_phone,
    )
    if reason:
        text += i18n.get("cancel_reason_block").format(reason=reason)
    return i18n, text


# Backward-compatible alias for existing call sites.
_appointment_notify_parts = appointment_notice_parts


async def notify_appointment(
        *,
        bot: Bot,
        repos: Repositories,
        appointment: Appointment,
        recipient_user_id: int,
        translations: dict,
        text_key: str,
        bot_timezone: str,
        with_master_actions: bool = False,
        with_dismiss: bool = False,
        with_reminder_actions: bool = False,
        reminder_kind: ReminderKind | None = None,
        reason: str | None = None,
) -> int | None:
    """
    Send an appointment status notification.
    Returns Telegram message_id when the message was sent, else None.
    """
    i18n, text = await appointment_notice_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key=text_key,
        bot_timezone=bot_timezone,
        recipient_user_id=recipient_user_id,
        reason=reason,
    )

    reply_markup: InlineKeyboardMarkup | None = None
    if with_master_actions:
        reply_markup = get_appointment_actions_kb(
            appointment=appointment,
            i18n=i18n,
            now=datetime.now(timezone.utc),
            slot_ends_at=appointment.ends_at,
        )
    elif with_reminder_actions:
        if reminder_kind is None:
            raise ValueError("reminder_kind is required with with_reminder_actions")
        reply_markup = get_reminder_kb(
            i18n=i18n,
            appointment_id=appointment.id,
            kind=reminder_kind,
        )
    elif with_dismiss:
        reply_markup = get_hub_dismiss_kb(i18n)

    with suppress(TelegramBadRequest, TelegramForbiddenError):
        sent = await bot.send_message(
            chat_id=recipient_user_id,
            text=text,
            reply_markup=reply_markup,
        )
        return sent.message_id
    return None


async def supersede_master_action_push(
        *,
        bot: Bot,
        repos: Repositories,
        appointment: Appointment,
        translations: dict,
        text_key: str,
        bot_timezone: str,
        reason: str | None = None,
) -> bool:
    """
    Replace the master's confirm/cancel push with a status message + OK.
    Returns True if the stored push text was edited.
    """
    message_id = appointment.master_notify_message_id
    if message_id is None:
        return False

    i18n, text = await appointment_notice_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key=text_key,
        bot_timezone=bot_timezone,
        recipient_user_id=appointment.master_user_id,
        reason=reason,
    )

    edited = False
    with suppress(TelegramBadRequest, TelegramForbiddenError):
        await bot.edit_message_text(
            chat_id=appointment.master_user_id,
            message_id=message_id,
            text=text,
            reply_markup=get_hub_dismiss_kb(i18n),
        )
        edited = True

    if not edited:
        with suppress(TelegramBadRequest, TelegramForbiddenError):
            await bot.edit_message_reply_markup(
                chat_id=appointment.master_user_id,
                message_id=message_id,
                reply_markup=None,
            )

    await repos.appointments.set_master_notify_message_id(
        appointment_id=appointment.id,
        message_id=None,
    )
    return edited
