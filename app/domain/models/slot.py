from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Slot:
    id: int
    master_user_id: int
    starts_at: datetime
    ends_at: datetime
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Slot":
        return cls(
            id=row["id"],
            master_user_id=row["master_user_id"],
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            created_at=row["created_at"]
        )
