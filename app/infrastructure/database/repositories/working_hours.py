import logging
from datetime import time

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.models.working_hours import WorkingHours


logger = logging.getLogger(__name__)


class WorkingHoursRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add(
            self,
            *,
            master_user_id: int,
            weekday: int,
            starts_time: time,
            ends_time: time,
    ) -> WorkingHours:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    INSERT INTO working_hours (
                        master_user_id,
                        weekday,
                        starts_time,
                        ends_time
                    )
                    VALUES (
                        %(master_user_id)s,
                        %(weekday)s,
                        %(starts_time)s,
                        %(ends_time)s
                    )
                    RETURNING
                        id,
                        master_user_id,
                        weekday,
                        starts_time,
                        ends_time,
                        created_at;
                """,
                params={
                    "master_user_id": master_user_id,
                    "weekday": weekday,
                    "starts_time": starts_time,
                    "ends_time": ends_time,
                },
            )
            row = await cursor.fetchone()
        logger.info(
            "Working hours added. master_user_id=%d, weekday=%d, %s-%s",
            master_user_id,
            weekday,
            starts_time,
            ends_time,
        )
        return WorkingHours.from_db_row(row)

    async def get(
            self,
            *,
            working_hours_id: int,
    ) -> WorkingHours | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        id,
                        master_user_id,
                        weekday,
                        starts_time,
                        ends_time,
                        created_at
                    FROM working_hours
                    WHERE id = %s;
                """,
                params=(working_hours_id, ),
            )
            row = await cursor.fetchone()
        return WorkingHours.from_db_row(row) if row else None

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            weekday: int | None = None,
    ) -> list[WorkingHours]:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        id,
                        master_user_id,
                        weekday,
                        starts_time,
                        ends_time,
                        created_at
                    FROM working_hours
                    WHERE master_user_id = %(master_user_id)s
                        AND (
                            %(weekday)s::smallint IS NULL
                            OR weekday = %(weekday)s
                        )
                    ORDER BY weekday, starts_time;
                """,
                params={
                    "master_user_id": master_user_id,
                    "weekday": weekday,
                },
            )
            rows = await cursor.fetchall()
        return [WorkingHours.from_db_row(row) for row in rows]

    async def delete(
            self,
            *,
            working_hours_id: int,
            master_user_id: int,
    ) -> bool:
        """Delete only if the row belongs to this master. Returns True if deleted."""
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                query="""
                    DELETE FROM working_hours
                    WHERE id = %(working_hours_id)s
                        AND master_user_id = %(master_user_id)s;
                """,
                params={
                    "working_hours_id": working_hours_id,
                    "master_user_id": master_user_id,
                },
            )
            deleted = cursor.rowcount > 0
        if deleted:
            logger.info(
                "Working hours deleted. id=%d, master_user_id=%d",
                working_hours_id,
                master_user_id,
            )
        return deleted
