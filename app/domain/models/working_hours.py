from dataclasses import dataclass
from datetime import datetime, time
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkingHours:
    id: int
    master_user_id: int
    weekday: int # ISO 1=Mon ... 7=Sun
    starts_time: time
    ends_time: time
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "WorkingHours":
        return cls(
            id=row["id"],
            master_user_id=row["master_user_id"],
            weekday=row["weekday"],
            starts_time=row["starts_time"],
            ends_time=row["ends_time"],
            created_at=row["created_at"],
        )
