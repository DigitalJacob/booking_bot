import logging
from typing import cast, LiteralString

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.models.master_settings import MasterSettings


logger = logging.getLogger(__name__)

_SELECT_COLUMNS = """
    master_user_id,
    timezone,
    slot_step_minutes,
    gap_minutes,
    min_lead_minutes,
    booking_horizon_days,
    created_at,
    updated_at
"""


class MasterSettingsRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_master(
            self,
            *,
            master_user_id: int,
    ) -> MasterSettings | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=cast(
                    LiteralString,
                    f"""
                        SELECT {_SELECT_COLUMNS}
                        FROM master_settings
                        WHERE master_user_id = %s;
                    """,
                ),
                params=(master_user_id, ),
            )
            row = await cursor.fetchone()
        return MasterSettings.from_db_row(row) if row else None

    async def ensure_defaults(
            self,
            *,
            master_user_id: int,
            timezone: str = "Europe/Moscow",
    ) -> MasterSettings:
        """Insert default settings if missing; return current row."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=cast(
                    LiteralString,
                    f"""
                        INSERT INTO master_settings (master_user_id, timezone)
                        VALUES (%(master_user_id)s, %(timezone)s)
                        ON CONFLICT (master_user_id) DO NOTHING
                        RETURNING {_SELECT_COLUMNS};
                    """,
                ),
                params={
                    "master_user_id": master_user_id,
                    "timezone": timezone,
                },
            )
            row = await cursor.fetchone()
            if row is None:
                await cursor.execute(
                    query=cast(
                        LiteralString,
                        f"""
                            SELECT {_SELECT_COLUMNS}
                            FROM master_settings
                            WHERE master_user_id = %s;
                        """,
                    ),
                    params=(master_user_id,),
                )
                row = await cursor.fetchone()
        logger.info(
            "Ensured master_settings for master_user_id=%d",
            master_user_id,
        )
        return MasterSettings.from_db_row(row)

    async def update_gap_minutes(
            self,
            *,
            master_user_id: int,
            gap_minutes: int,
    ) -> MasterSettings | None:
        """Update gap_minutes; returns None if the master has no settings row."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=cast(
                    LiteralString,
                    f"""
                        UPDATE master_settings
                        SET
                            gap_minutes = %(gap_minutes)s,
                            updated_at = NOW()
                        WHERE master_user_id = %(master_user_id)s
                        RETURNING {_SELECT_COLUMNS};
                    """,
                ),
                params={
                    "master_user_id": master_user_id,
                    "gap_minutes": gap_minutes,
                },
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        logger.info(
            "Master gap_minutes updated. master_user_id=%d, gap_minutes=%d",
            master_user_id,
            gap_minutes,
        )
        return MasterSettings.from_db_row(row)
