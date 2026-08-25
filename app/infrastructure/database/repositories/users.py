import logging
from typing import Any

from app.bot.enums.roles import UserRole
from psycopg import AsyncConnection


logger = logging.getLogger(__name__)


async def add_user(
        conn: AsyncConnection,
        *,
        user_id: int,
        username: str | None = None,
        language: str = "ru",
        role: UserRole = UserRole.CLIENT,
        banned: bool = False,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                INSERT INTO users(user_id, username, language, role, banned)
                VALUES(
                    %(user_id)s,
                    %(username)s,
                    %(language)s,
                    %(role)s,
                    %(banned)s
                )
                ON CONFLICT (user_id) DO NOTHING;
            """,
            params={
                "user_id": user_id,
                "username": username,
                "language": language,
                "role": role,
                "banned": banned,
            },
        )
        logger.info(
            "User added (or already exists). user_id=%d, language='%s', role=%s",
            user_id,
            language,
            role,
        )


async def get_user(
        conn: AsyncConnection,
        *,
        user_id: int,
) -> tuple[Any, ...] | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                SELECT
                    id,
                    user_id,
                    username,
                    language,
                    role,
                    banned,
                    created_at
                FROM users
                WHERE user_id = %s;
            """,
            params=(user_id, ),
        )
        row = await cursor.fetchone()
    return row


async def get_user_lang(
        conn: AsyncConnection,
        *,
        user_id: int,
) -> str | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="SELECT language FROM users WHERE user_id = %s;",
            params=(user_id, ),
        )
        row = await cursor.fetchone()
    return row[0] if row else None


async def change_user_lang(
        conn: AsyncConnection,
        *,
        user_id: int,
        language: str,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                UPDATE users
                SET language = %s
                WHERE user_id = %s;
            """,
            params=(language, user_id),
        )
    logger.info("Updated language to '%s' for user %d", language, user_id)


async def change_user_banned_status(
        conn: AsyncConnection,
        *,
        user_id: int,
        banned: bool,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                UPDATE users
                SET banned = %s
                WHERE user_id = %s;
            """,
            params=(banned, user_id),
        )
    logger.info("Updated banned=%s for user %d", banned, user_id)


async def get_user_role(
        conn: AsyncConnection,
        *,
        user_id: int,
) -> UserRole | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="SELECT role FROM users WHERE user_id = %s;",
            params=(user_id, ),
        )
        row = await cursor.fetchone()
    return UserRole(row[0]) if row else None
