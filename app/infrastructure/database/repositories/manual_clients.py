import logging

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app.domain.exceptions import ManualClientPhoneTaken
from app.domain.models.manual_client import ManualClient

logger = logging.getLogger(__name__)

_SELECT_COLUMNS = """
    id,
    master_user_id,
    name,
    phone,
    phone_digits,
    created_at
"""


class ManualClientsRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        master_user_id: int,
        name: str,
        phone: str,
        phone_digits: str,
    ) -> ManualClient:
        # Nested transaction → savepoint when middleware already opened one,
        # so UniqueViolation does not poison the outer handler transaction.
        try:
            async with (
                self._conn.transaction(),
                self._conn.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(
                    query=f"""
                        INSERT INTO manual_clients (
                            master_user_id,
                            name,
                            phone,
                            phone_digits
                        )
                        VALUES (
                            %(master_user_id)s,
                            %(name)s,
                            %(phone)s,
                            %(phone_digits)s
                        )
                        RETURNING {_SELECT_COLUMNS};
                    """,
                    params={
                        "master_user_id": master_user_id,
                        "name": name,
                        "phone": phone,
                        "phone_digits": phone_digits,
                    },
                )
                row = await cursor.fetchone()
        except UniqueViolation as exc:
            raise ManualClientPhoneTaken from exc
        logger.info(
            "Manual client added. master_user_id=%d, phone_digits=%s",
            master_user_id,
            phone_digits,
        )
        return ManualClient.from_db_row(row)

    async def get(
        self,
        *,
        manual_client_id: int,
        master_user_id: int,
    ) -> ManualClient | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT {_SELECT_COLUMNS}
                    FROM manual_clients
                    WHERE id = %(manual_client_id)s
                      AND master_user_id = %(master_user_id)s;
                """,
                params={
                    "manual_client_id": manual_client_id,
                    "master_user_id": master_user_id,
                },
            )
            row = await cursor.fetchone()
        return ManualClient.from_db_row(row) if row else None

    async def find_by_phone(
        self,
        *,
        master_user_id: int,
        phone_digits: str,
    ) -> ManualClient | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT {_SELECT_COLUMNS}
                    FROM manual_clients
                    WHERE master_user_id = %(master_user_id)s
                      AND phone_digits = %(phone_digits)s;
                """,
                params={
                    "master_user_id": master_user_id,
                    "phone_digits": phone_digits,
                },
            )
            row = await cursor.fetchone()
        return ManualClient.from_db_row(row) if row else None

    async def search(
        self,
        *,
        master_user_id: int,
        query: str,
        limit: int = 8,
    ) -> list[ManualClient]:
        """Match name (ILIKE) and/or phone digit substring for this master."""
        if limit <= 0:
            return []
        needle = query.strip()
        digits = "".join(ch for ch in needle if ch.isdigit())
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT {_SELECT_COLUMNS}
                    FROM manual_clients
                    WHERE master_user_id = %(master_user_id)s
                      AND (
                        (
                            %(needle)s <> ''
                            AND name ILIKE ('%%' || %(needle)s || '%%')
                        )
                        OR (
                            %(digits)s <> ''
                            AND phone_digits LIKE ('%%' || %(digits)s || '%%')
                        )
                      )
                    ORDER BY name ASC, id ASC
                    LIMIT %(limit)s;
                """,
                params={
                    "master_user_id": master_user_id,
                    "needle": needle,
                    "digits": digits,
                    "limit": limit,
                },
            )
            rows = await cursor.fetchall()
        return [ManualClient.from_db_row(row) for row in rows]
