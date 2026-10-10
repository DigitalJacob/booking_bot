import asyncio
import logging
from contextlib import suppress

import psycopg_pool
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from config.config import Config
from redis.asyncio import Redis

from app.bot.handlers.admin import admin_router
from app.bot.handlers.client import client_router
from app.bot.handlers.common.appointment_cancel import appointment_cancel_router
from app.bot.handlers.common.hub import hub_router
from app.bot.handlers.common.reminders import reminder_router
from app.bot.handlers.common.settings import settings_router
from app.bot.handlers.common.start import start_router
from app.bot.handlers.common.unsupported import unsupported_router
from app.bot.handlers.master import master_router
from app.bot.i18n.translator import get_translations
from app.bot.middlewares.banned import BannedMiddleware
from app.bot.middlewares.database import DataBaseMiddleware
from app.bot.middlewares.i18n import TranslatorMiddleware
from app.bot.middlewares.lang_settings import LangSettingsMiddleware
from app.bot.middlewares.user_context import UserContextMiddleware
from app.bot.reminders import reminder_worker
from app.infrastructure.database.connection import get_pg_pool

logger = logging.getLogger(__name__)


async def main(config: Config) -> None:
    logger.info("Starting bot...")

    storage = RedisStorage(
        redis=Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            username=config.redis.username,
        )
    )

    session: AiohttpSession | None = None
    if config.proxy:
        session = AiohttpSession(proxy=config.proxy.url)
        logger.info(
            "proxy enabled: %s://%s:%s",
            config.proxy.type,
            config.proxy.ip,
            config.proxy.port,
        )

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher(storage=storage)

    db_pool: psycopg_pool.AsyncConnectionPool = await get_pg_pool(
        db_name=config.db.name,
        host=config.db.host,
        port=config.db.port,
        user=config.db.user,
        password=config.db.password,
    )

    translations = get_translations()
    locales = list(translations.keys())

    logger.info("Including routers...")
    dp.include_routers(
        settings_router,
        start_router,
        hub_router,
        reminder_router,
        appointment_cancel_router,
        admin_router,
        client_router,
        master_router,
        unsupported_router,
    )

    logger.info("Including middlewares...")
    dp.update.middleware(DataBaseMiddleware())
    dp.update.middleware(UserContextMiddleware())
    dp.update.middleware(BannedMiddleware())
    dp.update.middleware(LangSettingsMiddleware())
    dp.update.middleware(TranslatorMiddleware())

    reminder_task = asyncio.create_task(
        reminder_worker(
            bot=bot,
            db_pool=db_pool,
            translations=translations,
            bot_timezone=config.bot.timezone,
            lead_minutes=config.bot.reminder_lead_minutes,
            evening_hour_start=config.bot.reminder_evening_hour_start,
            evening_hour_end=config.bot.reminder_evening_hour_end,
        ),
        name="reminder_worker",
    )

    try:
        await dp.start_polling(
            bot,
            db_pool=db_pool,
            translations=translations,
            locales=locales,
            admin_ids=config.bot.admin_ids,
            master_user_id=config.bot.master_user_id,
            bot_timezone=config.bot.timezone,
            schedule_mode=config.bot.schedule_mode,
            pdn_consent_version=config.bot.pdn_consent_version,
            pdn_operator_name=config.bot.pdn_operator_name,
            pdn_operator_contacts=config.bot.pdn_operator_contacts,
            pdn_policy_url=config.bot.pdn_policy_url,
            reminder_lead_minutes=config.bot.reminder_lead_minutes,
            reminder_evening_hour_start=config.bot.reminder_evening_hour_start,
            reminder_evening_hour_end=config.bot.reminder_evening_hour_end,
        )
    except Exception:
        logger.exception("Bot polling failed")
    finally:
        reminder_task.cancel()
        with suppress(asyncio.CancelledError):
            await reminder_task
        await db_pool.close()
        logger.info("Connection to Postgres closed")
        if session:
            await session.close()
            logger.info("Proxy session closed")
