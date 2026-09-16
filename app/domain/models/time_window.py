from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TimeWindow:
    starts_at: datetime
    ends_at: datetime
