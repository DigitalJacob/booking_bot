import asyncio
import logging
import os
import sys

from app.infrastructure.database.connection import get_pg_connection
from config.config import Config, load_config
from psycopg import AsyncConnection, Error


config: Config = load_config()

logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

logger = logging.getLogger(__name__)

if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main() -> None:
    connection: AsyncConnection | None = None

    try:
        connection = await get_pg_connection(
            db_name=config.db.name,
            host=config.db.host,
            port=config.db.port,
            user=config.db.user,
            password=config.db.password,
        )

        async with connection:
            async with connection.transaction():
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        query="""
                            CREATE TABLE IF NOT EXISTS users(
                                id SERIAL PRIMARY KEY,
                                user_id BIGINT NOT NULL UNIQUE,
                                username VARCHAR(50),
                                language VARCHAR(10) NOT NULL,
                                role VARCHAR(30) NOT NULL,
                                banned BOOLEAN NOT NULL DEFAULT FALSE,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            
                            CREATE TABLE IF NOT EXISTS services(
                                id SERIAL PRIMARY KEY,
                                master_user_id BIGINT NOT NULL
                                    REFERENCES users(user_id) ON DELETE CASCADE,
                                title VARCHAR(100) NOT NULL,
                                duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
                                price NUMERIC(10, 2),
                                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            
                            CREATE TABLE IF NOT EXISTS slots(
                                id SERIAL PRIMARY KEY,
                                master_user_id BIGINT NOT NULL
                                    REFERENCES users(user_id) ON DELETE CASCADE,
                                starts_at TIMESTAMPTZ NOT NULL,
                                ends_at TIMESTAMPTZ NOT NULL,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                CHECK (ends_at > starts_at),
                                UNIQUE (master_user_id, starts_at)
                            );
                            
                            CREATE TABLE IF NOT EXISTS appointments(
                                id SERIAL PRIMARY KEY,
                                client_user_id BIGINT NOT NULL
                                    REFERENCES users(user_id) ON DELETE CASCADE,
                                master_user_id BIGINT NOT NULL
                                    REFERENCES users(user_id) ON DELETE CASCADE,
                                service_id INT NOT NULL
                                    REFERENCES services(id) ON DELETE RESTRICT,
                                slot_id INT NOT NULL
                                    REFERENCES slots(id) ON DELETE RESTRICT,
                                status VARCHAR(30) NOT NULL,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                CHECK (status IN ('pending', 'confirmed', 'cancelled'))
                            );
                            
                            CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_active_slot
                                ON appointments(slot_id)
                                WHERE status IN ('pending', 'confirmed');                                
                        """
                    )
                logger.info("Tables `users`, `services`, `slots`, and `appointments` was successfully created")
    except Error as db_error:
        logger.exception("Database-specific error: %s", db_error)
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
    finally:
        if connection:
            await connection.close()
            logger.info("Connection to Postgres closed")


asyncio.run(main())
