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


class ManualClientPhoneTaken(DomainError):
    """This master already has a manual client with the same phone_digits."""


class RescheduleTooLate(DomainError):
    """Client tried to reschedule inside the master's min_lead window."""


class RescheduleSameTime(DomainError):
    """New starts_at matches the current appointment time."""


class AppointmentAlreadyEnded(DomainError):
    """Appointment ends_at is not in the future."""
