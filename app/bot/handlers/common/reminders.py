from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.handlers.common.appointment_cancel import (
    SOURCE_REMINDER,
    start_appointment_cancel,
)
from app.bot.keyboards.reminders import ReminderCallback
from app.domain.enums import AppointmentStatus, ReminderKind
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


reminder_router = Router(name="reminders")


def _parse_kind(raw: str) -> ReminderKind | None:
    try:
        return ReminderKind(raw)
    except ValueError:
        return None


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
    kind = _parse_kind(callback_data.kind)
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
