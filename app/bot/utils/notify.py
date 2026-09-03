from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.domain.models import Appointment
from app.infrastructure.database.repositories import Repositories
from app.bot.i18n.translator import resolve_i18n


async def notify_appointment(
        *,
        bot: Bot,
        repos: Repositories,
        appointment: Appointment,
        recipient_user_id: int,
        translations: dict,
        text_key: str,
) -> None:
    recipient = await repos.users.get_user(user_id=recipient_user_id)
    i18n = resolve_i18n(
        language=recipient.language if recipient else None,
        translations=translations,
    )

    service = await repos.services.get_service(service_id=appointment.service_id)
    slot = await repos.slots.get_slot(slot_id=appointment.slot_id)

    with suppress(TelegramBadRequest, TelegramForbiddenError):
        await bot.send_message(
            chat_id=recipient_user_id,
            text=i18n.get(text_key).format(
                title=service.title if service else "?",
                when=slot.starts_at.strftime("%d.%m.%Y %H:%M") if slot else "?",
                client_id=appointment.client_user_id,
            ),
        )
