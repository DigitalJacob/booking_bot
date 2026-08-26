import logging

import psycopg_pool
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.bot.handlers.admin import admin_router
from app.bot.handlers.client import client_router
from app.bot.handlers.common.others import others_router
from app.bot.handlers.common.settings import settings_router
from app.bot.handlers.common.start import start_router
from app.bot.handlers.master import master_router
from app.bot.i18n.translator import get_translations
from app.bot.middlewares.database import DataBaseMiddleware
from app.bot.middlewares.i18n import TranslatorMiddleware
from app.bot.middlewares.lang_settings import LangSettingsMiddleware
from app.infrastructure.database.connection import get_pg_pool
from config.config import Config


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
        client_router,
        master_router,
        admin_router,
        others_router,
    )

    logger.info("Including middlewares...")
    dp.update.middleware(DataBaseMiddleware())
    dp.update.middleware(LangSettingsMiddleware())
    dp.update.middleware(TranslatorMiddleware())

    try:
        await dp.start_polling(
            bot,
            db_pool=db_pool,
            translations=translations,
            locales=locales,
            admin_ids=config.bot.admin_ids,
        )
    except Exception:
        logger.exception("Bot polling failed")
    finally:
        await db_pool.close()
        logger.info("Connection to Postgres closed")
        if session:
            await session.close()
            logger.info("Proxy session closed")
