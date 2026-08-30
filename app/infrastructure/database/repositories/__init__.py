from dataclasses import dataclass

from psycopg import AsyncConnection

from app.infrastructure.database.repositories.appointments import AppointmentsRepository
from app.infrastructure.database.repositories.services import ServicesRepository
from app.infrastructure.database.repositories.slots import SlotsRepository
from app.infrastructure.database.repositories.users import UsersRepository


@dataclass
class Repositories:
    users: UsersRepository
    services: ServicesRepository
    slots: SlotsRepository
    appointments: AppointmentsRepository

    @classmethod
    def from_connection(cls, conn: AsyncConnection) -> "Repositories":
        return cls(
            users=UsersRepository(conn),
            services=ServicesRepository(conn),
            slots=SlotsRepository(conn),
            appointments=AppointmentsRepository(conn),
        )


__all__ = [
    "AppointmentsRepository",
    "Repositories",
    "ServicesRepository",
    "SlotsRepository",
    "UsersRepository",
]
