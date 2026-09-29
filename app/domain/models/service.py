from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class Service:
    id: int
    master_user_id: int
    title: str
    duration_minutes: int
    price: Decimal | None
    is_active: bool
    description: str | None
    photo_file_id: str | None
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Service":
        return cls(
            id=row["id"],
            master_user_id=row["master_user_id"],
            title=row["title"],
            duration_minutes=row["duration_minutes"],
            price=row["price"],
            is_active=row["is_active"],
            description=row.get("description"),
            photo_file_id=row.get("photo_file_id"),
            created_at=row["created_at"],
        )
