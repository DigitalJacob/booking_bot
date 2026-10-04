from enum import StrEnum


class ReminderKind(StrEnum):
    CLIENT_EVENING = "client_evening"
    CLIENT_HOUR = "client_hour"
    MASTER_EVENING = "master_evening"
    MASTER_HOUR = "master_hour"
