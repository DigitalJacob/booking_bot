from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.enums import AppointmentStatus


@dataclass(frozen=True, slots=True)
class Appointment:
    id: int
    client_user_id: int
    master_user_id: int
    service_id: int
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Appointment":
        return cls(
            id=row["id"],
            client_user_id=row["client_user_id"],
            master_user_id=row["master_user_id"],
            service_id=row["service_id"],
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            status=AppointmentStatus(row["status"]),
            created_at=row["created_at"]
        )
