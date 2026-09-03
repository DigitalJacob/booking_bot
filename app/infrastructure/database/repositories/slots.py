import logging
from datetime import datetime

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.enums import AppointmentStatus
from app.domain.models.slot import Slot


logger = logging.getLogger(__name__)


class SlotsRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add_slot(
            self,
            *,
            master_user_id: int,
            starts_at: datetime,
            ends_at: datetime,
    ) -> Slot:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    INSERT INTO slots(
                        master_user_id,
                        starts_at,
                        ends_at
                    )
                    VALUES(
                        %(master_user_id)s,
                        %(starts_at)s,
                        %(ends_at)s
                    )
                    RETURNING
                        id,
                        master_user_id,
                        starts_at,
                        ends_at,
                        created_at;
                """,
                params={
                    "master_user_id": master_user_id,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                },
            )
            row = await cursor.fetchone()
        logger.info(
            "Slot added. master_user_id=%d, starts_at=%s, ends_at=%s",
            master_user_id,
            starts_at,
            ends_at,
        )
        return Slot.from_db_row(row)


    async def get_slot(
            self,
            *,
            slot_id: int,
    ) -> Slot | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        id,
                        master_user_id,
                        starts_at,
                        ends_at,
                        created_at
                    FROM slots
                    WHERE id = %s;
                """,
                params=(slot_id, ),
            )
            row = await cursor.fetchone()
        return Slot.from_db_row(row) if row else None


    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            available_only: bool = False,
    ) -> list[Slot]:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        s.id,
                        s.master_user_id,
                        s.starts_at,
                        s.ends_at,
                        s.created_at
                    FROM slots s
                    WHERE s.master_user_id = %(master_user_id)s
                      AND (%(from_dt)s IS NULL OR s.starts_at >= %(from_dt)s)
                      AND (
                          %(available_only)s = FALSE
                          OR NOT EXISTS (
                              SELECT 1
                              FROM appointments a
                              WHERE a.slot_id = s.id
                                AND a.status IN (%(pending)s, %(confirmed)s)
                          )
                      )
                    ORDER BY s.starts_at;
                """,
                params={
                    "master_user_id": master_user_id,
                    "from_dt": from_dt,
                    "available_only": available_only,
                    "pending": AppointmentStatus.PENDING,
                    "confirmed": AppointmentStatus.CONFIRMED,
                },
            )
            rows = await cursor.fetchall()
        return [Slot.from_db_row(row) for row in rows]
