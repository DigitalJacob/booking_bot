from app.domain.enums import AppointmentStatus


_STATUS_KEYS = {
    AppointmentStatus.PENDING: "status_pending",
    AppointmentStatus.CONFIRMED: "status_confirmed",
    AppointmentStatus.CANCELLED: "status_cancelled",
}


def status_label(status: AppointmentStatus, i18n: dict[str, str]) -> str:
    return i18n.get(_STATUS_KEYS[status])
