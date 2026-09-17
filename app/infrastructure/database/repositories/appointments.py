import logging
from datetime import datetime

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.domain.enums import AppointmentStatus
from app.domain.models.appointment import Appointment


logger = logging.getLogger(__name__)


class AppointmentsRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def add_appointment(
            self,
            *,
            client_user_id: int,
            master_user_id: int,
            service_id: int,
            slot_id: int | None,
            starts_at: datetime,
            ends_at: datetime,
            status: AppointmentStatus = AppointmentStatus.PENDING,
    ) -> Appointment:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    INSERT INTO appointments(
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status
                    )
                    VALUES(
                        %(client_user_id)s,
                        %(master_user_id)s,
                        %(service_id)s,
                        %(slot_id)s,
                        %(starts_at)s,
                        %(ends_at)s,
                        %(status)s
                    )
                    RETURNING
                        id,
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status,
                        created_at;
                """,
                params={
                    "client_user_id": client_user_id,
                    "master_user_id": master_user_id,
                    "service_id": service_id,
                    "slot_id": slot_id,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "status": status,
                },
            )
            row = await cursor.fetchone()
        logger.info(
            "Appointment added. client=%d, master=%d, service=%d, slot_id=%s, status=%s",
            client_user_id,
            master_user_id,
            service_id,
            slot_id,
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
                query="""
                    SELECT
                        id,
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status,
                        created_at
                    FROM appointments
                    WHERE id = %s;
                """,
                params=(appointment_id, ),
            )
            row = await cursor.fetchone()
        return Appointment.from_db_row(row) if row else None


    async def get_active_by_slot(
            self,
            *,
            slot_id: int,
    ) -> Appointment | None:
        async with self._conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                query="""
                    SELECT
                        id,
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status,
                        created_at
                    FROM appointments
                    WHERE slot_id = %s
                        AND status IN (%s, %s);
                """,
                params=(
                    slot_id,
                    AppointmentStatus.PENDING,
                    AppointmentStatus.CONFIRMED,
                ),
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
                query="""
                    SELECT
                        id,
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status,
                        created_at
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
                query="""
                    SELECT
                        id,
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status,
                        created_at
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
                query="""
                    UPDATE appointments
                    SET status = %(status)s
                    WHERE id = %(appointment_id)s
                    RETURNING
                        id,
                        client_user_id,
                        master_user_id,
                        service_id,
                        slot_id,
                        starts_at,
                        ends_at,
                        status,
                        created_at;
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
