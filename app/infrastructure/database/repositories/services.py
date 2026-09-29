import logging
from decimal import Decimal

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.models.service import Service


logger = logging.getLogger(__name__)

_SELECT_COLUMNS = """
    id,
    master_user_id,
    title,
    duration_minutes,
    price,
    is_active,
    description,
    photo_file_id,
    created_at
"""


class ServicesRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add_service(
            self,
            *,
            master_user_id: int,
            title: str,
            duration_minutes: int,
            price: Decimal | None = None,
            is_active: bool = True,
    ) -> Service:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    INSERT INTO services(
                        master_user_id,
                        title,
                        duration_minutes,
                        price,
                        is_active
                    )
                    VALUES(
                        %(master_user_id)s,
                        %(title)s,
                        %(duration_minutes)s,
                        %(price)s,
                        %(is_active)s
                    )
                    RETURNING {_SELECT_COLUMNS};
                """,
                params={
                    "master_user_id": master_user_id,
                    "title": title,
                    "duration_minutes": duration_minutes,
                    "price": price,
                    "is_active": is_active,
                },
            )
            row = await cursor.fetchone()
        logger.info(
            "Service added. master_user_id=%d, title='%s', duration=%d",
            master_user_id,
            title,
            duration_minutes,
        )
        return Service.from_db_row(row)

    async def get_service(
            self,
            *,
            service_id: int,
    ) -> Service | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT {_SELECT_COLUMNS}
                    FROM services
                    WHERE id = %s;
                """,
                params=(service_id, ),
            )
            row = await cursor.fetchone()
        return Service.from_db_row(row) if row else None

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            active_only: bool = True,
    ) -> list[Service]:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT {_SELECT_COLUMNS}
                    FROM services
                    WHERE master_user_id = %(master_user_id)s
                      AND (%(active_only)s = FALSE OR is_active = TRUE)
                    ORDER BY id;
                """,
                params={
                    "master_user_id": master_user_id,
                    "active_only": active_only,
                },
            )
            rows = await cursor.fetchall()
        return [Service.from_db_row(row) for row in rows]

    async def update(
            self,
            *,
            service_id: int,
            master_user_id: int,
            title: str,
            duration_minutes: int,
            price: Decimal | None,
    ) -> Service | None:
        """Update only if the service belongs to this master. Returns None if missing."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    UPDATE services
                    SET
                        title = %(title)s,
                        duration_minutes = %(duration_minutes)s,
                        price = %(price)s
                    WHERE id = %(service_id)s
                        AND master_user_id = %(master_user_id)s
                    RETURNING {_SELECT_COLUMNS};
                """,
                params={
                    "service_id": service_id,
                    "master_user_id": master_user_id,
                    "title": title,
                    "duration_minutes": duration_minutes,
                    "price": price,
                },
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        logger.info(
            "Service updated. id=%d, master_user_id=%d, title='%s'",
            service_id,
            master_user_id,
            title,
        )
        return Service.from_db_row(row)

    async def update_description(
            self,
            *,
            service_id: int,
            master_user_id: int,
            description: str | None,
    ) -> Service | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    UPDATE services
                    SET description = %(description)s
                    WHERE id = %(service_id)s
                        AND master_user_id = %(master_user_id)s
                    RETURNING {_SELECT_COLUMNS};
                """,
                params={
                    "service_id": service_id,
                    "master_user_id": master_user_id,
                    "description": description,
                },
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        logger.info(
            "Service description updated. id=%d, master_user_id=%d",
            service_id,
            master_user_id,
        )
        return Service.from_db_row(row)

    async def update_photo_file_id(
            self,
            *,
            service_id: int,
            master_user_id: int,
            photo_file_id: str | None,
    ) -> Service | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    UPDATE services
                    SET photo_file_id = %(photo_file_id)s
                    WHERE id = %(service_id)s
                        AND master_user_id = %(master_user_id)s
                    RETURNING {_SELECT_COLUMNS};
                """,
                params={
                    "service_id": service_id,
                    "master_user_id": master_user_id,
                    "photo_file_id": photo_file_id,
                },
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        logger.info(
            "Service photo_file_id updated. id=%d, master_user_id=%d",
            service_id,
            master_user_id,
        )
        return Service.from_db_row(row)

    async def set_active(
            self,
            *,
            service_id: int,
            master_user_id: int,
            is_active: bool,
    ) -> Service | None:
        """Toggle is_active only if the service belongs to this master."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    UPDATE services
                    SET is_active = %(is_active)s
                    WHERE id = %(service_id)s
                        AND master_user_id = %(master_user_id)s
                    RETURNING {_SELECT_COLUMNS};
                """,
                params={
                    "service_id": service_id,
                    "master_user_id": master_user_id,
                    "is_active": is_active,
                },
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        logger.info(
            "Service set_active=%s. id=%d, master_user_id=%d",
            is_active,
            service_id,
            master_user_id,
        )
        return Service.from_db_row(row)
