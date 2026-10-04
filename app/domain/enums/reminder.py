from enum import StrEnum


class ReminderKind(StrEnum):
    CLIENT_EVENING = "client_evening"
    CLIENT_HOUR = "client_hour"
    MASTER_EVENING = "master_evening"
    MASTER_HOUR = "master_hour"


_REMINDED_AT_ATTR: dict[ReminderKind, str] = {
    ReminderKind.CLIENT_EVENING: "client_evening_reminded_at",
    ReminderKind.CLIENT_HOUR: "client_hour_reminded_at",
    ReminderKind.MASTER_EVENING: "master_evening_reminded_at",
    ReminderKind.MASTER_HOUR: "master_hour_reminded_at",
}


def reminded_at_attr(kind: ReminderKind) -> str:
    """DB / model field name for the sent-at timestamp of this kind."""
    return _REMINDED_AT_ATTR[kind]
