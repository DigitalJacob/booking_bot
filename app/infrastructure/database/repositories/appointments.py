import logging
from datetime import UTC, datetime

from psycopg import AsyncConnection
from psycopg.errors import ExclusionViolation, UniqueViolation
from psycopg.rows import dict_row

from app.domain.enums import AppointmentStatus, ReminderKind
from app.domain.enums.reminder import reminded_at_attr
from app.domain.exceptions import TimeConflict
from app.domain.models.appointment import Appointment

logger = logging.getLogger(__name__)

_APPOINTMENT_COLUMNS = """
    id,
    client_user_id,
    master_user_id,
    service_id,
    starts_at,
    ends_at,
    status,
    created_at,
    master_notify_message_id,
    client_evening_reminded_at,
    client_hour_reminded_at,
    master_evening_reminded_at,
    master_hour_reminded_at
"""


class AppointmentsRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add_appointment(
            self,
            *,
            client_user_id: int,
            master_user_id: int,
            service_id: int,
            starts_at: datetime,
            ends_at: datetime,
            status: AppointmentStatus = AppointmentStatus.PENDING,
    ) -> Appointment:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            try:
                await cursor.execute(
                    query=f"""
                        INSERT INTO appointments(
                            client_user_id,
                            master_user_id,
                            service_id,
                            starts_at,
                            ends_at,
                            status
                        )
                        VALUES(
                            %(client_user_id)s,
                            %(master_user_id)s,
                            %(service_id)s,
                            %(starts_at)s,
                            %(ends_at)s,
                            %(status)s
                        )
                        RETURNING
                            {_APPOINTMENT_COLUMNS};
                    """,
                    params={
                        "client_user_id": client_user_id,
                        "master_user_id": master_user_id,
                        "service_id": service_id,
                        "starts_at": starts_at,
                        "ends_at": ends_at,
                        "status": status,
                    },
                )
            except (UniqueViolation, ExclusionViolation) as e:
                raise TimeConflict from e
            row = await cursor.fetchone()
        logger.info(
            "Appointment added. client=%d, master=%d, service=%d, status=%s",
            client_user_id,
            master_user_id,
            service_id,
            status,
        )
        return Appointment.from_db_row(row)

    async def get_appointment(
            self,
            *,
            appointment_id: int,
    ) -> Appointment | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT
                        {_APPOINTMENT_COLUMNS}
                    FROM appointments
                    WHERE id = %s;
                """,
                params=(appointment_id,),
            )
            row = await cursor.fetchone()
        return Appointment.from_db_row(row) if row else None

    async def list_by_client(
            self,
            *,
            client_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT
                        {_APPOINTMENT_COLUMNS}
                    FROM appointments
                    WHERE client_user_id = %(client_user_id)s
                        AND (%(from_dt)s::timestamptz IS NULL OR starts_at >= %(from_dt)s)
                        AND (%(to_dt)s::timestamptz IS NULL OR starts_at < %(to_dt)s)
                    ORDER BY starts_at;
                """,
                params={
                    "client_user_id": client_user_id,
                    "from_dt": from_dt,
                    "to_dt": to_dt,
                },
            )
            rows = await cursor.fetchall()
        return [Appointment.from_db_row(row) for row in rows]

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT
                        {_APPOINTMENT_COLUMNS}
                    FROM appointments
                    WHERE master_user_id = %(master_user_id)s
                        AND (%(from_dt)s::timestamptz IS NULL OR starts_at >= %(from_dt)s)
                        AND (%(to_dt)s::timestamptz IS NULL OR starts_at < %(to_dt)s)
                    ORDER BY starts_at;
                """,
                params={
                    "master_user_id": master_user_id,
                    "from_dt": from_dt,
                    "to_dt": to_dt,
                },
            )
            rows = await cursor.fetchall()
        return [Appointment.from_db_row(row) for row in rows]

    async def change_status(
            self,
            *,
            appointment_id: int,
            status: AppointmentStatus,
    ) -> Appointment | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    UPDATE appointments
                    SET status = %(status)s
                    WHERE id = %(appointment_id)s
                    RETURNING
                        {_APPOINTMENT_COLUMNS};
                """,
                params={
                    "appointment_id": appointment_id,
                    "status": status,
                },
            )
            row = await cursor.fetchone()
        logger.info(
            "Updated appointment %d status to '%s'",
            appointment_id,
            status,
        )
        return Appointment.from_db_row(row) if row else None

    async def set_master_notify_message_id(
            self,
            *,
            appointment_id: int,
            message_id: int | None,
    ) -> None:
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                query="""
                    UPDATE appointments
                    SET master_notify_message_id = %(message_id)s
                    WHERE id = %(appointment_id)s;
                """,
                params={
                    "appointment_id": appointment_id,
                    "message_id": message_id,
                },
            )
        logger.info(
            "Set master_notify_message_id=%s for appointment %d",
            message_id,
            appointment_id,
        )

    async def list_confirmed_starting_between(
            self,
            *,
            from_dt: datetime,
            to_dt: datetime,
    ) -> list[Appointment]:
        """Confirmed appointments with starts_at in [from_dt, to_dt)."""
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query=f"""
                    SELECT
                        {_APPOINTMENT_COLUMNS}
                    FROM appointments
                    WHERE status = %(status)s
                        AND starts_at >= %(from_dt)s
                        AND starts_at < %(to_dt)s
                    ORDER BY starts_at;
                """,
                params={
                    "status": AppointmentStatus.CONFIRMED,
                    "from_dt": from_dt,
                    "to_dt": to_dt,
                },
            )
            rows = await cursor.fetchall()
        return [Appointment.from_db_row(row) for row in rows]

    async def mark_reminder_sent(
            self,
            *,
            appointment_id: int,
            kind: ReminderKind,
            sent_at: datetime | None = None,
    ) -> None:
        column = reminded_at_attr(kind)
        when = sent_at or datetime.now(UTC)
        async with self._conn.cursor() as cursor:
            await cursor.execute(
                query=f"""
                    UPDATE appointments
                    SET {column} = %(sent_at)s
                    WHERE id = %(appointment_id)s;
                """,
                params={
                    "appointment_id": appointment_id,
                    "sent_at": when,
                },
            )
        logger.info(
            "Marked %s for appointment %d at %s",
            column,
            appointment_id,
            when.isoformat(),
        )
