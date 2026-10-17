class DomainError(Exception):
    pass


class ServiceNotFound(DomainError):
    pass


class ServiceInactive(DomainError):
    pass


class AppointmentNotFound(DomainError):
    pass


class InvalidAppointmentStatus(DomainError):
    pass


class ForbiddenBookingAction(DomainError):
    pass


class WindowNotAvailable(DomainError):
    pass


class TimeConflict(DomainError):
    pass


class InvalidAppointmentClient(DomainError):
    """Exactly one of client_user_id / manual_client_id must be set."""


class ManualClientNotFound(DomainError):
    pass
