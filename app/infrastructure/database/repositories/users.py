import logging

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.bot.enums.roles import UserRole
from app.domain.models.user import User


logger = logging.getLogger(__name__)


class UsersRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add_user(
            self,
            *,
            user_id: int,
            username: str | None = None,
            language: str = "ru",
            role: UserRole = UserRole.CLIENT,
            banned: bool = False,
    ) -> None:
        async with self._conn.cursor() as cursor:
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
            self,
            *,
            user_id: int,
    ) -> User | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
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
        return User.from_db_row(row) if row else None


    async def change_user_lang(
            self,
            *,
            user_id: int,
            language: str,
    ) -> None:
        async with self._conn.cursor() as cursor:
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
            self,
            *,
            user_id: int,
            banned: bool,
    ) -> None:
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                query="""
                    UPDATE users
                    SET banned = %s
                    WHERE user_id = %s;
                """,
                params=(banned, user_id),
            )
        logger.info("Updated banned=%s for user %d", banned, user_id)

