from contextlib import suppress
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

from app.bot.i18n.translator import resolve_i18n
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.master import get_appointment_actions_kb
from app.bot.utils.format import client_contact, format_dt
from app.domain.models import Appointment
from app.infrastructure.database.repositories import Repositories


async def _appointment_notify_parts(
        *,
        repos: Repositories,
        appointment: Appointment,
        translations: dict,
        text_key: str,
        bot_timezone: str,
        recipient_user_id: int,
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
    return i18n, text


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
) -> int | None:
    """
    Send an appointment status notification.
    Returns Telegram message_id when the message was sent, else None.
    """
    i18n, text = await _appointment_notify_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key=text_key,
        bot_timezone=bot_timezone,
        recipient_user_id=recipient_user_id,
    )

    reply_markup: InlineKeyboardMarkup | None = None
    if with_master_actions:
        reply_markup = get_appointment_actions_kb(
            appointment=appointment,
            i18n=i18n,
            now=datetime.now(timezone.utc),
            slot_ends_at=appointment.ends_at,
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
) -> bool:
    """
    Replace the master's confirm/cancel push with a status message + OK.
    Returns True if the stored push text was edited.
    """
    message_id = appointment.master_notify_message_id
    if message_id is None:
        return False

    i18n, text = await _appointment_notify_parts(
        repos=repos,
        appointment=appointment,
        translations=translations,
        text_key=text_key,
        bot_timezone=bot_timezone,
        recipient_user_id=appointment.master_user_id,
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
