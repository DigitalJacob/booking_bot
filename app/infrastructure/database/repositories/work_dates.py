import logging
from datetime import date, time

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.models.work_date import WorkDate

logger = logging.getLogger(__name__)

_SELECT_COLUMNS = """
    id,
    master_user_id,
    work_date,
    starts_time,
    ends_time,
    created_at
"""


class WorkDatesRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_date: date | None = None,
            to_date: date | None = None,
    ) -> list[WorkDate]:
        """List open days; from_date inclusive, to_date exclusive when set."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT {_SELECT_COLUMNS}
                    FROM work_dates
                    WHERE master_user_id = %(master_user_id)s
                        AND (
                            %(from_date)s::date IS NULL
                            OR work_date >= %(from_date)s
                        )
                        AND (
                            %(to_date)s::date IS NULL
                            OR work_date < %(to_date)s
                        )
                    ORDER BY work_date, starts_time;
                """,
                params={
                    "master_user_id": master_user_id,
                    "from_date": from_date,
                    "to_date": to_date,
                },
            )
            rows = await cursor.fetchall()
        return [WorkDate.from_db_row(row) for row in rows]

    async def list_month(
            self,
            *,
            master_user_id: int,
            year: int,
            month: int,
    ) -> list[WorkDate]:
        first = date(year, month, 1)
        to_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        return await self.list_by_master(
            master_user_id=master_user_id,
            from_date=first,
            to_date=to_date,
        )

    async def delete_dates(
            self,
            *,
            master_user_id: int,
            work_dates: list[date],
    ) -> int:
        """Delete specific open days. Returns number of deleted rows."""
        days = sorted(set(work_dates))
        if not days:
            return 0
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                query="""
                    DELETE FROM work_dates
                    WHERE master_user_id = %(master_user_id)s
                        AND work_date = ANY(%(work_dates)s);
                """,
                params={
                    "master_user_id": master_user_id,
                    "work_dates": days,
                },
            )
            deleted = cursor.rowcount
        logger.info(
            "Work dates deleted. master_user_id=%d, count=%d",
            master_user_id,
            deleted,
        )
        return deleted

    async def upsert_dates(
            self,
            *,
            master_user_id: int,
            work_dates: list[date],
            starts_time: time,
            ends_time: time,
    ) -> list[WorkDate]:
        """Insert or update hours for the given days only."""
        if ends_time <= starts_time:
            raise ValueError("ends_time must be after starts_time")
        days = sorted(set(work_dates))
        if not days:
            return []

        rows: list[dict] = []
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            for day in days:
                await cursor.execute(
                    query=f"""
                        INSERT INTO work_dates (
                            master_user_id,
                            work_date,
                            starts_time,
                            ends_time
                        )
                        VALUES (
                            %(master_user_id)s,
                            %(work_date)s,
                            %(starts_time)s,
                            %(ends_time)s
                        )
                        ON CONFLICT (master_user_id, work_date) DO UPDATE
                        SET
                            starts_time = EXCLUDED.starts_time,
                            ends_time = EXCLUDED.ends_time
                        RETURNING {_SELECT_COLUMNS};
                    """,
                    params={
                        "master_user_id": master_user_id,
                        "work_date": day,
                        "starts_time": starts_time,
                        "ends_time": ends_time,
                    },
                )
                row = await cursor.fetchone()
                if row is not None:
                    rows.append(row)

        logger.info(
            "Work dates upserted. master_user_id=%d, count=%d, %s-%s",
            master_user_id,
            len(days),
            starts_time,
            ends_time,
        )
        return [WorkDate.from_db_row(row) for row in rows]

    async def replace_month(
            self,
            *,
            master_user_id: int,
            year: int,
            month: int,
            work_dates: list[date],
            starts_time: time | None = None,
            ends_time: time | None = None,
    ) -> list[WorkDate]:
        """Replace all open days in the month with the given dates and hours.

        Empty work_dates clears the month (all days become days off).
        """
        if work_dates:
            if starts_time is None or ends_time is None:
                raise ValueError("starts_time and ends_time are required")
            if ends_time <= starts_time:
                raise ValueError("ends_time must be after starts_time")

        first = date(year, month, 1)
        to_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        for day in work_dates:
            if day.year != year or day.month != month:
                raise ValueError(
                    f"work_date {day.isoformat()} is outside {year}-{month:02d}"
                )

        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    DELETE FROM work_dates
                    WHERE master_user_id = %(master_user_id)s
                        AND work_date >= %(from_date)s
                        AND work_date < %(to_date)s;
                """,
                params={
                    "master_user_id": master_user_id,
                    "from_date": first,
                    "to_date": to_date,
                },
            )
            for day in sorted(set(work_dates)):
                await cursor.execute(
                    query=f"""
                        INSERT INTO work_dates (
                            master_user_id,
                            work_date,
                            starts_time,
                            ends_time
                        )
                        VALUES (
                            %(master_user_id)s,
                            %(work_date)s,
                            %(starts_time)s,
                            %(ends_time)s
                        )
                        RETURNING {_SELECT_COLUMNS};
                    """,
                    params={
                        "master_user_id": master_user_id,
                        "work_date": day,
                        "starts_time": starts_time,
                        "ends_time": ends_time,
                    },
                )

        logger.info(
            "Work dates replaced. master_user_id=%d, %04d-%02d, count=%d, %s-%s",
            master_user_id,
            year,
            month,
            len(set(work_dates)),
            starts_time,
            ends_time,
        )
        return await self.list_month(
            master_user_id=master_user_id,
            year=year,
            month=month,
        )
