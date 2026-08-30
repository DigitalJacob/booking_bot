import logging
from decimal import Decimal

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.models.service import Service


logger = logging.getLogger(__name__)


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
                query="""
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
                    RETURNING
                        id,
                        master_user_id,
                        title,
                        duration_minutes,
                        price,
                        is_active,
                        created_at;
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
                query="""
                    SELECT
                        id,
                        master_user_id,
                        title,
                        duration_minutes,
                        price,
                        is_active,
                        created_at
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
                query="""
                    SELECT
                        id,
                        master_user_id,
                        title,
                        duration_minutes,
                        price,
                        is_active,
                        created_at
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
