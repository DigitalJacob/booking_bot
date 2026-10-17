from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ManualClient:
    id: int
    master_user_id: int
    name: str
    phone: str
    phone_digits: str
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "ManualClient":
        return cls(
            id=row["id"],
            master_user_id=row["master_user_id"],
            name=row["name"],
            phone=row["phone"],
            phone_digits=row["phone_digits"],
            created_at=row["created_at"],
        )
