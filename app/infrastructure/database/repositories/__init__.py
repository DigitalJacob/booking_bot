from dataclasses import dataclass

from psycopg import AsyncConnection

from app.infrastructure.database.repositories.users import UsersRepository


@dataclass
class Repositories:
    users: UsersRepository

    @classmethod
    def from_connection(cls, conn: AsyncConnection) -> "Repositories":
        return cls(users=UsersRepository(conn))


__all__ = ["Repositories", "UsersRepository"]
