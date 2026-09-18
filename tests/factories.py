from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import cast

from psycopg.errors import ExclusionViolation

from app.domain.enums import AppointmentStatus
from app.domain.models import (
    Appointment,
    Service,
    MasterSettings,
    WorkingHours,
    TimeOff,
)
from app.infrastructure.database.repositories import (
    AppointmentsRepository,
    Repositories,
    ServicesRepository,
    UsersRepository,
    MasterSettingsRepository,
    WorkingHoursRepository,
    TimeOffRepository,
)


MASTER_ID = 100
CLIENT_ID = 200
OTHER_ID = 300

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def make_service(
        *,
        service_id: int = 1,
        master_user_id: int = MASTER_ID,
        duration_minutes: int = 60,
        is_active: bool = True,
) -> Service:
    return Service(
        id=service_id,
        master_user_id=master_user_id,
        title=f"Service {service_id}",
        duration_minutes=duration_minutes,
        price=Decimal("1500"),
        is_active=is_active,
        created_at=NOW,
    )


def make_appointment(
        *,
        appointment_id: int = 1,
        client_user_id: int = CLIENT_ID,
        master_user_id: int = MASTER_ID,
        service_id: int = 1,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        status: AppointmentStatus = AppointmentStatus.PENDING,
) -> Appointment:
    if starts_at is None:
        starts_at = NOW + timedelta(hours=2)
    if ends_at is None:
        ends_at = starts_at + timedelta(minutes=60)
    return Appointment(
        id=appointment_id,
        client_user_id=client_user_id,
        master_user_id=master_user_id,
        service_id=service_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
        created_at=NOW,
    )


class FakeServicesRepository:
    def __init__(self, services: list[Service]) -> None:
        self._services = {service.id: service for service in services}

    async def get_service(self, *, service_id: int) -> Service | None:
        return self._services.get(service_id)

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            active_only: bool = False,
    ) -> list[Service]:
        return [
            service for service in self._services.values()
            if service.master_user_id == master_user_id
            and (not active_only or service.is_active)
        ]


class FakeMasterSettingsRepository:
    def __init__(self, settings: MasterSettings | None) -> None:
        self._settings = settings

    async def get_by_master(self, *, master_user_id: int) -> MasterSettings | None:
        if self._settings and self._settings.master_user_id == master_user_id:
            return self._settings
        return None


class FakeWorkingHoursRepository:
    def __init__(self, rows: list[WorkingHours]) -> None:
        self._rows = rows

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            weekday: int | None = None,
    ) -> list[WorkingHours]:
        result = [
            row for row in self._rows
            if row.master_user_id == master_user_id
            and (weekday is None or row.weekday == weekday)
        ]
        return sorted(result, key=lambda row: (row.weekday, row.starts_time))


class FakeTimeOffRepository:
    def __init__(self, rows: list[TimeOff]) -> None:
        self._rows = rows

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[TimeOff]:
        result = []
        for row in self._rows:
            if row.master_user_id != master_user_id:
                continue
            if from_dt is not None and row.ends_at <= from_dt:
                continue
            if to_dt is not None and row.starts_at >= to_dt:
                continue
            result.append(row)
        return sorted(result, key=lambda row: row.starts_at)


class FakeAppointmentsRepository:
    def __init__(
            self,
            appointments: list[Appointment],
    ) -> None:
        self._appointments = {item.id: item for item in appointments}
        self._next_id = max(self._appointments, default=0) + 1

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
        for existing in self._appointments.values():
            if existing.master_user_id != master_user_id:
                continue
            if existing.status not in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            ):
                continue
            if starts_at < existing.ends_at and ends_at > existing.starts_at:
                raise ExclusionViolation("Overlapping appointment")

        appointment = make_appointment(
            appointment_id=self._next_id,
            client_user_id=client_user_id,
            master_user_id=master_user_id,
            service_id=service_id,
            starts_at=starts_at,
            ends_at=ends_at,
            status=status,
        )
        self._appointments[appointment.id] = appointment
        self._next_id += 1
        return appointment

    async def get_appointment(
            self,
            *,
            appointment_id: int,
    ) -> Appointment | None:
        return self._appointments.get(appointment_id)

    async def list_by_client(
            self,
            *,
            client_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]:
        result = []
        for appointment in self._appointments.values():
            if appointment.client_user_id != client_user_id:
                continue
            if from_dt is not None and appointment.starts_at < from_dt:
                continue
            if to_dt is not None and appointment.starts_at >= to_dt:
                continue
            result.append(appointment)
        return sorted(
            result,
            key=lambda item: item.starts_at,
        )

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]:
        result = []
        for appointment in self._appointments.values():
            if appointment.master_user_id != master_user_id:
                continue
            if from_dt is not None and appointment.starts_at < from_dt:
                continue
            if to_dt is not None and appointment.starts_at >= to_dt:
                continue
            result.append(appointment)
        return sorted(result, key=lambda item: item.starts_at)

    async def change_status(
            self,
            *,
            appointment_id: int,
            status: AppointmentStatus,
    ) -> Appointment | None:
        appointment = self._appointments.get(appointment_id)
        if appointment is None:
            return None
        updated = replace(appointment, status=status)
        self._appointments[appointment_id] = updated
        return updated


def make_repos(
        *,
        services: list[Service] | None = None,
        appointments: list[Appointment] | None = None,
        settings: MasterSettings | None = None,
        working_hours: list[WorkingHours] | None = None,
        time_offs: list[TimeOff] | None = None,
) -> Repositories:
    return Repositories(
        users=cast(UsersRepository, None),
        services=cast(
            ServicesRepository,
            FakeServicesRepository(services or []),
        ),
        appointments=cast(
            AppointmentsRepository,
            FakeAppointmentsRepository(appointments or []),
        ),
        master_settings=cast(
            MasterSettingsRepository,
            FakeMasterSettingsRepository(settings),
        ),
        working_hours=cast(
            WorkingHoursRepository,
            FakeWorkingHoursRepository(working_hours or []),
        ),
        time_off=cast(
            TimeOffRepository,
            FakeTimeOffRepository(time_offs or []),
        ),
    )
