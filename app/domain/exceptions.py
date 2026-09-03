class DomainError(Exception):
    pass


class ServiceNotFound(DomainError):
    pass


class ServiceInactive(DomainError):
    pass


class SlotNotFound(DomainError):
    pass


class SlotInThePast(DomainError):
    pass


class SlotTaken(DomainError):
    pass


class SlotMasterMismatch(DomainError):
    pass


class SlotTooShort(DomainError):
    pass


class AppointmentNotFound(DomainError):
    pass


class InvalidAppointmentStatus(DomainError):
    pass


class ForbiddenBookingAction(DomainError):
    pass
