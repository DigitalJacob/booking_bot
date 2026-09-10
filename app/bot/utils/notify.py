from contextlib import suppress
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

from app.domain.models import Appointment
from app.infrastructure.database.repositories import Repositories
from app.bot.i18n.translator import resolve_i18n
from app.bot.utils.format import client_contact
from app.bot.keyboards.master import get_appointment_actions_kb


async def notify_appointment(
        *,
        bot: Bot,
        repos: Repositories,
        appointment: Appointment,
        recipient_user_id: int,
        translations: dict,
        text_key: str,
        with_master_actions: bool = False,
) -> None:
    recipient = await repos.users.get_user(user_id=recipient_user_id)
    i18n = resolve_i18n(
        language=recipient.language if recipient else None,
        translations=translations,
    )

    service = await repos.services.get_service(service_id=appointment.service_id)
    slot = await repos.slots.get_slot(slot_id=appointment.slot_id)
    client = await repos.users.get_user(user_id=appointment.client_user_id)
    client_name, client_phone = client_contact(client)

    reply_markup: InlineKeyboardMarkup | None = None
    if with_master_actions:
        reply_markup = get_appointment_actions_kb(
            appointment=appointment,
            i18n=i18n,
            now=datetime.now(timezone.utc),
            slot_ends_at=slot.ends_at if slot else None,
        )

    with suppress(TelegramBadRequest, TelegramForbiddenError):
        await bot.send_message(
            chat_id=recipient_user_id,
            text=i18n.get(text_key).format(
                title=service.title if service else "?",
                when=slot.starts_at.strftime("%d.%m.%Y %H:%M") if slot else "?",
                client_name=client_name,
                client_phone=client_phone,
            ),
            reply_markup=reply_markup,
        )
