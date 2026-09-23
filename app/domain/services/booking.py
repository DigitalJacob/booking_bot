import logging
from datetime import datetime, timezone

from app.domain.enums import AppointmentStatus
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
    ServiceInactive,
    ServiceNotFound,
    WindowNotAvailable,
)
from app.domain.models import Appointment, Service, TimeWindow
from app.infrastructure.database.repositories import Repositories
from app.domain.services.availability import AvailabilityService


logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, repos: Repositories) -> None:
        self._repos = repos

    async def list_services(self, *, master_user_id: int) -> list[Service]:
        return await self._repos.services.list_by_master(
            master_user_id=master_user_id,
            active_only=True,
        )

    async def list_available_windows(
            self,
            *,
            master_user_id: int,
            duration_minutes: int,
            now: datetime | None = None,
    ) -> list[TimeWindow]:
        return await AvailabilityService(self._repos).list_windows(
            master_user_id=master_user_id,
            duration_minutes=duration_minutes,
            now=now,
        )

    async def book_window(
            self,
            *,
            client_user_id: int,
            service_id: int,
            starts_at: datetime,
            now: datetime | None = None
    ) -> Appointment:
        if now is None:
            now = datetime.now(timezone.utc)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        else:
            starts_at = starts_at.astimezone(timezone.utc)

        service = await self._repos.services.get_service(service_id=service_id)
        if service is None:
            raise ServiceNotFound
        if not service.is_active:
            raise ServiceInactive

        windows = await self.list_available_windows(
            master_user_id=service.master_user_id,
            duration_minutes=service.duration_minutes,
            now=now,
        )
        match = next(
            (
                window for window in windows
                if window.starts_at.astimezone(timezone.utc) == starts_at
            ),
            None,
        )
        if match is None:
            raise WindowNotAvailable

        appointment = await self._repos.appointments.add_appointment(
            client_user_id=client_user_id,
            master_user_id=service.master_user_id,
            service_id=service_id,
            starts_at=match.starts_at,
            ends_at=match.ends_at,
            status=AppointmentStatus.PENDING,
        )

        logger.info(
            "Booked appointment %d via window: client=%d, master=%d, starts_at=%s",
            appointment.id,
            client_user_id,
            service.master_user_id,
            match.starts_at,
        )
        return appointment

    async def list_client_appointments(
            self,
            *,
            client_user_id: int,
            now: datetime | None = None,
    ) -> list[Appointment]:
        if now is None:
            now = datetime.now(timezone.utc)

        appointments = await self._repos.appointments.list_by_client(
            client_user_id=client_user_id,
            from_dt=now,
        )
        return [
            appointment for appointment in appointments
            if appointment.status in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            )
        ]

    async def confirm(
            self,
            *,
            appointment_id: int,
            master_user_id: int,
    ) -> Appointment:
        appointment = await self._repos.appointments.get_appointment(
            appointment_id=appointment_id,
        )
        if appointment is None:
            raise AppointmentNotFound
        if appointment.master_user_id != master_user_id:
            raise ForbiddenBookingAction
        if appointment.status != AppointmentStatus.PENDING:
            raise InvalidAppointmentStatus

        updated = await self._repos.appointments.change_status(
            appointment_id=appointment_id,
            status=AppointmentStatus.CONFIRMED,
        )
        if updated is None:
            raise AppointmentNotFound
        return updated

    async def cancel(
            self,
            *,
            appointment_id: int,
            actor_user_id: int,
    ) -> Appointment:
        appointment = await self._repos.appointments.get_appointment(
            appointment_id=appointment_id,
        )
        if appointment is None:
            raise AppointmentNotFound
        if actor_user_id not in (
            appointment.client_user_id,
            appointment.master_user_id,
        ):
            raise ForbiddenBookingAction
        if appointment.status == AppointmentStatus.CANCELLED:
            raise InvalidAppointmentStatus

        updated = await self._repos.appointments.change_status(
            appointment_id=appointment_id,
            status=AppointmentStatus.CANCELLED,
        )
        if updated is None:
            raise AppointmentNotFound
        return updated
