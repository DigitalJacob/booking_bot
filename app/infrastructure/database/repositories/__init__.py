from dataclasses import dataclass

from psycopg import AsyncConnection

from app.infrastructure.database.repositories.appointments import AppointmentsRepository
from app.infrastructure.database.repositories.master_settings import (
    MasterSettingsRepository,
)
from app.infrastructure.database.repositories.services import ServicesRepository
from app.infrastructure.database.repositories.time_off import TimeOffRepository
from app.infrastructure.database.repositories.users import UsersRepository
from app.infrastructure.database.repositories.work_dates import WorkDatesRepository
from app.infrastructure.database.repositories.working_hours import WorkingHoursRepository


@dataclass
class Repositories:
    users: UsersRepository
    services: ServicesRepository
    appointments: AppointmentsRepository
    master_settings: MasterSettingsRepository
    working_hours: WorkingHoursRepository
    work_dates: WorkDatesRepository
    time_off: TimeOffRepository

    @classmethod
    def from_connection(cls, conn: AsyncConnection) -> "Repositories":
        return cls(
            users=UsersRepository(conn),
            services=ServicesRepository(conn),
            appointments=AppointmentsRepository(conn),
            master_settings=MasterSettingsRepository(conn),
            working_hours=WorkingHoursRepository(conn),
            work_dates=WorkDatesRepository(conn),
            time_off=TimeOffRepository(conn),
        )


__all__ = [
    "AppointmentsRepository",
    "Repositories",
    "ServicesRepository",
    "UsersRepository",
    "MasterSettingsRepository",
    "WorkingHoursRepository",
    "WorkDatesRepository",
    "TimeOffRepository",
]
