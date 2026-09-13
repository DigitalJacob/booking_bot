from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class MasterSettings:
    master_user_id: int
    timezone: str
    slot_step_minutes: int | None
    gap_minutes: int
    min_lead_minutes: int
    booking_horizon_days: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "MasterSettings":
        return cls(
            master_user_id=row["master_user_id"],
            timezone=row["timezone"],
            slot_step_minutes=row["slot_step_minutes"],
            gap_minutes=row["gap_minutes"],
            min_lead_minutes=row["min_lead_minutes"],
            booking_horizon_days=row["booking_horizon_days"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
