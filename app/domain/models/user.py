from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class User:
    id: int
    user_id: int
    username: str | None
    language: str
    role: UserRole
    banned: bool
    first_name: str | None
    last_name: str | None
    phone: str | None
    created_at: datetime

    @property
    def profile_complete(self) -> bool:
        return bool(
            self.first_name
            and self.last_name
            and self.phone
        )

    @property
    def display_name(self) -> str:
        parts = [self.first_name, self.last_name]
        name = " ".join(part for part in parts if part)
        return name or (f"@{self.username}" if self.username else str(self.user_id))

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "User":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            language=row["language"],
            role=UserRole(row["role"]),
            banned=row["banned"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            created_at=row["created_at"]
        )
