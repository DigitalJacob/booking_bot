import logging
from datetime import datetime

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.models.time_off import TimeOff


logger = logging.getLogger(__name__)


class TimeOffRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add(
            self,
            *,
            master_user_id: int,
            starts_at: datetime,
            ends_at: datetime,
            note: str | None = None,
    ) -> TimeOff:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    INSERT INTO time_off (
                        master_user_id,
                        starts_at,
                        ends_at,
                        note
                    )
                    VALUES (
                        %(master_user_id)s,
                        %(starts_at)s,
                        %(ends_at)s,
                        %(note)s
                    )
                    RETURNING
                        id,
                        master_user_id,
                        starts_at,
                        ends_at,
                        note,
                        created_at;
                """,
                params={
                    "master_user_id": master_user_id,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "note": note,
                },
            )
            row = await cursor.fetchone()
        logger.info(
            "Time off added. master_user_id=%d, %s-%s",
            master_user_id,
            starts_at,
            ends_at,
        )
        return TimeOff.from_db_row(row)

    async def get(
            self,
            *,
            time_off_id: int,
    ) -> TimeOff | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        id,
                        master_user_id,
                        starts_at,
                        ends_at,
                        note,
                        created_at
                    FROM time_off
                    WHERE id = %s;
                """,
                params=(time_off_id, ),
            )
            row = await cursor.fetchone()
        return TimeOff.from_db_row(row) if row else None

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[TimeOff]:
        """
        If from_dt/to_dt are set, return blocks that overlap [from_dt, to_dt).
        Overlap: starts_at < to_dt AND ends_at > from_dt.
        """
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        id,
                        master_user_id,
                        starts_at,
                        ends_at,
                        note,
                        created_at
                    FROM time_off
                    WHERE master_user_id = %(master_user_id)s
                        AND (
                            %(from_dt)s::timestamptz IS NULL
                            OR ends_at > %(from_dt)s
                        )
                        AND (
                            %(to_dt)s::timestamptz IS NULL
                            OR starts_at < %(to_dt)s
                        )
                        ORDER BY starts_at;
                """,
                params={
                    "master_user_id": master_user_id,
                    "from_dt": from_dt,
                    "to_dt": to_dt,
                },
            )
            rows = await cursor.fetchall()
        return [TimeOff.from_db_row(row) for row in rows]

    async def delete(
            self,
            *,
            time_off_id: int,
            master_user_id: int,
    ) -> bool:
        """Delete only if the row belongs to this master. Returns True if deleted."""
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                query="""
                    DELETE FROM time_off
                    WHERE id = %(time_off_id)s
                        AND master_user_id = %(master_user_id)s;
                """,
                params={
                    "time_off_id": time_off_id,
                    "master_user_id": master_user_id,
                },
            )
            deleted = cursor.rowcount > 0
        if deleted:
            logger.info(
                "Time off deleted. id=%d, master_user_id=%d",
                time_off_id,
                master_user_id,
            )
        return deleted
