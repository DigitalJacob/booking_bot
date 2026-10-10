"""Repository ports used by domain services (no SQL / driver imports)."""

from datetime import date, datetime
from typing import Protocol

from app.domain.enums import AppointmentStatus
from app.domain.models import (
    Appointment,
    MasterSettings,
    Service,
    TimeOff,
    WorkDate,
    WorkingHours,
)


class ServicesRepoPort(Protocol):
    async def get_service(self, *, service_id: int) -> Service | None: ...

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            active_only: bool = True,
    ) -> list[Service]: ...


class AppointmentsRepoPort(Protocol):
    async def add_appointment(
            self,
            *,
            client_user_id: int,
            master_user_id: int,
            service_id: int,
            starts_at: datetime,
            ends_at: datetime,
            status: AppointmentStatus = AppointmentStatus.PENDING,
    ) -> Appointment: ...

    async def get_appointment(
            self,
            *,
            appointment_id: int,
    ) -> Appointment | None: ...

    async def list_by_client(
            self,
            *,
            client_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]: ...

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]: ...

    async def change_status(
            self,
            *,
            appointment_id: int,
            status: AppointmentStatus,
    ) -> Appointment | None: ...


class MasterSettingsRepoPort(Protocol):
    async def get_by_master(
            self,
            *,
            master_user_id: int,
    ) -> MasterSettings | None: ...


class WorkingHoursRepoPort(Protocol):
    async def list_by_master(
            self,
            *,
            master_user_id: int,
            weekday: int | None = None,
    ) -> list[WorkingHours]: ...


class WorkDatesRepoPort(Protocol):
    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_date: date | None = None,
            to_date: date | None = None,
    ) -> list[WorkDate]: ...


class TimeOffRepoPort(Protocol):
    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[TimeOff]: ...


class RepositoriesPort(Protocol):
    """Facade of persistence ports needed by BookingService / AvailabilityService."""

    services: ServicesRepoPort
    appointments: AppointmentsRepoPort
    master_settings: MasterSettingsRepoPort
    working_hours: WorkingHoursRepoPort
    work_dates: WorkDatesRepoPort
    time_off: TimeOffRepoPort
