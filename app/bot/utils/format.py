from app.domain.enums import AppointmentStatus
from app.domain.models import User


_STATUS_KEYS = {
    AppointmentStatus.PENDING: "status_pending",
    AppointmentStatus.CONFIRMED: "status_confirmed",
    AppointmentStatus.CANCELLED: "status_cancelled",
}


def status_label(status: AppointmentStatus, i18n: dict[str, str]) -> str:
    return i18n.get(_STATUS_KEYS[status])


def client_contact(user: User | None) -> tuple[str, str]:
    if user is None:
        return "?", "-"
    phone = user.phone or "-"
    return user.display_name, phone
