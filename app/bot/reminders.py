"""Background loop: evening / hour reminders for confirmed appointments."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from psycopg_pool import AsyncConnectionPool

from app.bot.utils.notify import notify_appointment
from app.domain.enums import AppointmentStatus, ReminderKind
from app.domain.models import Appointment
from app.domain.services.reminders import filter_due_reminders, reminded_at_for
from app.infrastructure.database.repositories import Repositories


logger = logging.getLogger(__name__)

_TICK_SECONDS = 45

_TEXT_KEY_BY_KIND: dict[ReminderKind, str] = {
    ReminderKind.CLIENT_EVENING: "client_reminder_evening",
    ReminderKind.CLIENT_HOUR: "client_reminder_hour",
    ReminderKind.MASTER_EVENING: "master_reminder_evening",
    ReminderKind.MASTER_HOUR: "master_reminder_hour",
}


def _recipient_user_id(
        appointment: Appointment,
        kind: ReminderKind,
) -> int:
    if kind in (ReminderKind.CLIENT_EVENING, ReminderKind.CLIENT_HOUR):
        return appointment.client_user_id
    return appointment.master_user_id


def _tomorrow_local_bounds(
        *,
        now: datetime,
        timezone_name: str,
) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone_name)
    local_now = now.astimezone(tz)
    tomorrow = local_now.date() + timedelta(days=1)
    start_local = datetime.combine(tomorrow, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )


def _in_evening_clock_window(
        *,
        now: datetime,
        timezone_name: str,
        evening_hour_start: int,
        evening_hour_end: int,
) -> bool:
    local_now = now.astimezone(ZoneInfo(timezone_name))
    return evening_hour_start <= local_now.hour < evening_hour_end


async def _load_confirmed_between(
        *,
        db_pool: AsyncConnectionPool,
        from_dt: datetime,
        to_dt: datetime,
) -> list[Appointment]:
    async with db_pool.connection() as connection:
        async with connection.transaction():
            repos = Repositories.from_connection(connection)
            return await repos.appointments.list_confirmed_starting_between(
                from_dt=from_dt,
                to_dt=to_dt,
            )


async def _deliver_one(
        *,
        bot: Bot,
        db_pool: AsyncConnectionPool,
        appointment: Appointment,
        kind: ReminderKind,
        now: datetime,
        translations: dict,
        bot_timezone: str,
) -> None:
    """Send one reminder and mark it in its own transaction."""
    text_key = _TEXT_KEY_BY_KIND[kind]
    async with db_pool.connection() as connection:
        async with connection.transaction():
            repos = Repositories.from_connection(connection)
            fresh = await repos.appointments.get_appointment(
                appointment_id=appointment.id,
            )
            if fresh is None:
                return
            if fresh.status != AppointmentStatus.CONFIRMED:
                return
            if reminded_at_for(fresh, kind) is not None:
                return

            message_id = await notify_appointment(
                bot=bot,
                repos=repos,
                appointment=fresh,
                recipient_user_id=_recipient_user_id(fresh, kind),
                translations=translations,
                text_key=text_key,
                bot_timezone=bot_timezone,
                with_reminder_actions=True,
            )
            if message_id is None:
                logger.warning(
                    "Reminder %s not delivered for appointment %d",
                    kind,
                    fresh.id,
                )
                return
            await repos.appointments.mark_reminder_sent(
                appointment_id=fresh.id,
                kind=kind,
                sent_at=now,
            )


async def _process_kinds(
        *,
        bot: Bot,
        db_pool: AsyncConnectionPool,
        appointments: list[Appointment],
        kinds: tuple[ReminderKind, ...],
        now: datetime,
        translations: dict,
        bot_timezone: str,
        lead_minutes: int,
        evening_hour_start: int,
        evening_hour_end: int,
) -> None:
    for kind in kinds:
        due = filter_due_reminders(
            appointments=appointments,
            kind=kind,
            now=now,
            timezone_name=bot_timezone,
            lead_minutes=lead_minutes,
            evening_hour_start=evening_hour_start,
            evening_hour_end=evening_hour_end,
        )
        for appointment in due:
            await _deliver_one(
                bot=bot,
                db_pool=db_pool,
                appointment=appointment,
                kind=kind,
                now=now,
                translations=translations,
                bot_timezone=bot_timezone,
            )


async def run_reminder_tick(
        *,
        bot: Bot,
        db_pool: AsyncConnectionPool,
        translations: dict,
        bot_timezone: str,
        lead_minutes: int,
        evening_hour_start: int,
        evening_hour_end: int,
) -> None:
    now = datetime.now(timezone.utc)

    if _in_evening_clock_window(
        now=now,
        timezone_name=bot_timezone,
        evening_hour_start=evening_hour_start,
        evening_hour_end=evening_hour_end,
    ):
        from_dt, to_dt = _tomorrow_local_bounds(
            now=now,
            timezone_name=bot_timezone,
        )
        evening_candidates = await _load_confirmed_between(
            db_pool=db_pool,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        await _process_kinds(
            bot=bot,
            db_pool=db_pool,
            appointments=evening_candidates,
            kinds=(
                ReminderKind.CLIENT_EVENING,
                ReminderKind.MASTER_EVENING,
            ),
            now=now,
            translations=translations,
            bot_timezone=bot_timezone,
            lead_minutes=lead_minutes,
            evening_hour_start=evening_hour_start,
            evening_hour_end=evening_hour_end,
        )

    hour_to = now + timedelta(minutes=lead_minutes, seconds=1)
    hour_candidates = await _load_confirmed_between(
        db_pool=db_pool,
        from_dt=now,
        to_dt=hour_to,
    )
    await _process_kinds(
        bot=bot,
        db_pool=db_pool,
        appointments=hour_candidates,
        kinds=(ReminderKind.CLIENT_HOUR, ReminderKind.MASTER_HOUR),
        now=now,
        translations=translations,
        bot_timezone=bot_timezone,
        lead_minutes=lead_minutes,
        evening_hour_start=evening_hour_start,
        evening_hour_end=evening_hour_end,
    )


async def reminder_worker(
        *,
        bot: Bot,
        db_pool: AsyncConnectionPool,
        translations: dict,
        bot_timezone: str,
        lead_minutes: int,
        evening_hour_start: int,
        evening_hour_end: int,
) -> None:
    logger.info(
        "Reminder worker started (tick=%ss, lead=%smin, evening=[%s,%s))",
        _TICK_SECONDS,
        lead_minutes,
        evening_hour_start,
        evening_hour_end,
    )
    while True:
        try:
            await run_reminder_tick(
                bot=bot,
                db_pool=db_pool,
                translations=translations,
                bot_timezone=bot_timezone,
                lead_minutes=lead_minutes,
                evening_hour_start=evening_hour_start,
                evening_hour_end=evening_hour_end,
            )
        except asyncio.CancelledError:
            logger.info("Reminder worker cancelled")
            raise
        except Exception:
            logger.exception("Reminder tick failed")
        await asyncio.sleep(_TICK_SECONDS)
