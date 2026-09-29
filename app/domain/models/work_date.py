from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkDate:
    id: int
    master_user_id: int
    work_date: date
    starts_time: time
    ends_time: time
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "WorkDate":
        return cls(
            id=row["id"],
            master_user_id=row["master_user_id"],
            work_date=row["work_date"],
            starts_time=row["starts_time"],
            ends_time=row["ends_time"],
            created_at=row["created_at"],
        )
