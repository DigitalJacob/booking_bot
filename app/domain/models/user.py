from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.bot.enums.roles import UserRole


@dataclass(frozen=True, slots=True)
class User:
    id: int
    user_id: int
    username: str | None
    language: str
    role: UserRole
    banned: bool
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "User":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            language=row["language"],
            role=UserRole(row["role"]),
            banned=row["banned"],
            created_at=row["created_at"]
        )
