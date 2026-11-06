import logging
from datetime import UTC, datetime, timedelta

from app.domain.enums import AppointmentStatus, RescheduleKind
from app.domain.exceptions import (
    AppointmentAlreadyEnded,
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentClient,
    InvalidAppointmentStatus,
    ManualClientNotFound,
    RescheduleSameTime,
    RescheduleTooLate,
    ServiceInactive,
    ServiceNotFound,
    WindowNotAvailable,
)
from app.domain.models import Appointment, RescheduleResult, Service, TimeWindow
from app.domain.ports import RepositoriesPort
from app.domain.services.availability import AvailabilityService

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
_MIN_SHIFT_MINUTES = 1
_MAX_SHIFT_MINUTES = 180


class BookingService:
    def __init__(self, repos: RepositoriesPort) -> None:
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
        schedule_mode: str = "weekly",
        now: datetime | None = None,
        ignore_min_lead: bool = False,
        exclude_appointment_id: int | None = None,
    ) -> list[TimeWindow]:
        return await AvailabilityService(self._repos).list_windows(
            master_user_id=master_user_id,
            duration_minutes=duration_minutes,
            schedule_mode=schedule_mode,
            now=now,
            ignore_min_lead=ignore_min_lead,
            exclude_appointment_id=exclude_appointment_id,
        )

    async def list_windows_for_master(
        self,
        *,
        master_user_id: int,
        duration_minutes: int,
        schedule_mode: str = "weekly",
        now: datetime | None = None,
        exclude_appointment_id: int | None = None,
    ) -> list[TimeWindow]:
        """Windows for master-initiated booking: min_lead ignored, horizon kept."""
        return await self.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=duration_minutes,
            schedule_mode=schedule_mode,
            now=now,
            ignore_min_lead=True,
            exclude_appointment_id=exclude_appointment_id,
        )

    async def list_open_months(
        self,
        *,
        master_user_id: int,
        schedule_mode: str = "weekly",
        now: datetime | None = None,
    ) -> list[tuple[int, int]]:
        return await AvailabilityService(self._repos).list_open_months(
            master_user_id=master_user_id,
            schedule_mode=schedule_mode,
            now=now,
        )

    async def book_window(
        self,
        *,
        client_user_id: int,
        service_id: int,
        starts_at: datetime,
        schedule_mode: str = "weekly",
        now: datetime | None = None,
    ) -> Appointment:
        service = await self._load_active_service(service_id=service_id)
        return await self._reserve_window(
            service=service,
            starts_at=starts_at,
            status=AppointmentStatus.PENDING,
            schedule_mode=schedule_mode,
            now=now,
            client_user_id=client_user_id,
        )

    async def book_for_client(
        self,
        *,
        master_user_id: int,
        service_id: int,
        starts_at: datetime,
        client_user_id: int | None = None,
        manual_client_id: int | None = None,
        schedule_mode: str = "weekly",
        now: datetime | None = None,
    ) -> Appointment:
        """Master books a client: confirmed, min_lead ignored, horizon kept.

        Pass exactly one of ``client_user_id`` (Telegram) or ``manual_client_id``.
        """
        if (client_user_id is None) == (manual_client_id is None):
            raise InvalidAppointmentClient

        service = await self._load_active_service(service_id=service_id)
        if service.master_user_id != master_user_id:
            raise ForbiddenBookingAction

        if manual_client_id is not None:
            manual = await self._repos.manual_clients.get(
                manual_client_id=manual_client_id,
                master_user_id=master_user_id,
            )
            if manual is None:
                raise ManualClientNotFound

        return await self._reserve_window(
            service=service,
            starts_at=starts_at,
            status=AppointmentStatus.CONFIRMED,
            schedule_mode=schedule_mode,
            now=now,
            for_master=True,
            client_user_id=client_user_id,
            manual_client_id=manual_client_id,
        )

    async def _load_active_service(self, *, service_id: int) -> Service:
        service = await self._repos.services.get_service(service_id=service_id)
        if service is None:
            raise ServiceNotFound
        if not service.is_active:
            raise ServiceInactive
        return service

    async def _reserve_window(
        self,
        *,
        service: Service,
        starts_at: datetime,
        status: AppointmentStatus,
        schedule_mode: str,
        now: datetime | None,
        for_master: bool = False,
        client_user_id: int | None = None,
        manual_client_id: int | None = None,
    ) -> Appointment:
        if now is None:
            now = datetime.now(UTC)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=UTC)
        else:
            starts_at = starts_at.astimezone(UTC)

        if for_master:
            windows = await self.list_windows_for_master(
                master_user_id=service.master_user_id,
                duration_minutes=service.duration_minutes,
                schedule_mode=schedule_mode,
                now=now,
            )
        else:
            windows = await self.list_available_windows(
                master_user_id=service.master_user_id,
                duration_minutes=service.duration_minutes,
                schedule_mode=schedule_mode,
                now=now,
            )
        match = next(
            (window for window in windows if window.starts_at.astimezone(UTC) == starts_at),
            None,
        )
        if match is None:
            raise WindowNotAvailable

        appointment = await self._repos.appointments.add_appointment(
            client_user_id=client_user_id,
            manual_client_id=manual_client_id,
            master_user_id=service.master_user_id,
            service_id=service.id,
            starts_at=match.starts_at,
            ends_at=match.ends_at,
            status=status,
            price_snapshot=service.price,
        )

        logger.info(
            "Booked appointment %d via window: client=%s, manual_client=%s, "
            "master=%d, status=%s, starts_at=%s",
            appointment.id,
            client_user_id,
            manual_client_id,
            service.master_user_id,
            status,
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
            now = datetime.now(UTC)

        appointments = await self._repos.appointments.list_by_client(
            client_user_id=client_user_id,
            from_dt=now,
        )
        return [
            appointment
            for appointment in appointments
            if appointment.status
            in (
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
        # Manual bookings have client_user_id=None → only the master may cancel.
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

    async def reschedule(
        self,
        *,
        appointment_id: int,
        actor_user_id: int,
        new_starts_at: datetime,
        schedule_mode: str = "weekly",
        now: datetime | None = None,
    ) -> RescheduleResult:
        if now is None:
            now = datetime.now(UTC)
        new_starts_at = self._as_utc(new_starts_at)

        appointment = await self._repos.appointments.get_appointment(
            appointment_id=appointment_id,
        )
        if appointment is None:
            raise AppointmentNotFound

        is_master = actor_user_id == appointment.master_user_id
        is_client = (
            appointment.client_user_id is not None and actor_user_id == appointment.client_user_id
        )
        if not is_master and not is_client:
            raise ForbiddenBookingAction
        if appointment.status not in _ACTIVE_STATUSES:
            raise InvalidAppointmentStatus
        if appointment.ends_at <= now:
            raise AppointmentAlreadyEnded

        if is_client and not is_master:
            min_lead = await self.client_min_lead_minutes(
                master_user_id=appointment.master_user_id,
            )
            if self.is_client_reschedule_too_late(
                starts_at=appointment.starts_at,
                min_lead_minutes=min_lead,
                now=now,
            ):
                raise RescheduleTooLate

        old_starts_at = appointment.starts_at
        old_ends_at = appointment.ends_at
        if new_starts_at == old_starts_at.astimezone(UTC):
            raise RescheduleSameTime

        duration_minutes = int((old_ends_at - old_starts_at).total_seconds() // 60)
        if is_master:
            windows = await self.list_windows_for_master(
                master_user_id=appointment.master_user_id,
                duration_minutes=duration_minutes,
                schedule_mode=schedule_mode,
                now=now,
                exclude_appointment_id=appointment_id,
            )
        else:
            windows = await self.list_available_windows(
                master_user_id=appointment.master_user_id,
                duration_minutes=duration_minutes,
                schedule_mode=schedule_mode,
                now=now,
                exclude_appointment_id=appointment_id,
            )
        match = next(
            (window for window in windows if window.starts_at.astimezone(UTC) == new_starts_at),
            None,
        )
        if match is None:
            raise WindowNotAvailable

        new_status = appointment.status if is_master else AppointmentStatus.PENDING
        updated = await self._repos.appointments.reschedule(
            appointment_id=appointment_id,
            starts_at=match.starts_at,
            ends_at=match.ends_at,
            status=new_status,
        )
        if updated is None:
            raise AppointmentNotFound

        await self._repos.appointments.add_reschedule_log(
            appointment_id=appointment_id,
            actor_user_id=actor_user_id,
            kind=RescheduleKind.MOVE,
            old_starts_at=old_starts_at,
            old_ends_at=old_ends_at,
            new_starts_at=updated.starts_at,
            new_ends_at=updated.ends_at,
        )
        logger.info(
            "Rescheduled appointment %d by actor=%d: %s → %s",
            appointment_id,
            actor_user_id,
            old_starts_at,
            updated.starts_at,
        )
        return RescheduleResult(
            appointment=updated,
            old_starts_at=old_starts_at,
            old_ends_at=old_ends_at,
        )

    async def shift_late(
        self,
        *,
        appointment_id: int,
        master_user_id: int,
        minutes: int,
        schedule_mode: str = "weekly",
        now: datetime | None = None,
    ) -> RescheduleResult:
        if not (_MIN_SHIFT_MINUTES <= minutes <= _MAX_SHIFT_MINUTES):
            raise ValueError(
                f"minutes must be between {_MIN_SHIFT_MINUTES} and "
                f"{_MAX_SHIFT_MINUTES}, got: {minutes}",
            )
        if now is None:
            now = datetime.now(UTC)

        appointment = await self._repos.appointments.get_appointment(
            appointment_id=appointment_id,
        )
        if appointment is None:
            raise AppointmentNotFound
        if appointment.master_user_id != master_user_id:
            raise ForbiddenBookingAction
        if appointment.status not in _ACTIVE_STATUSES:
            raise InvalidAppointmentStatus

        old_starts_at = appointment.starts_at
        old_ends_at = appointment.ends_at
        delta = timedelta(minutes=minutes)
        new_starts_at = old_starts_at + delta
        new_ends_at = old_ends_at + delta
        if new_ends_at <= now:
            raise AppointmentAlreadyEnded

        bookable = await AvailabilityService(self._repos).is_interval_bookable(
            master_user_id=appointment.master_user_id,
            starts_at=new_starts_at,
            ends_at=new_ends_at,
            schedule_mode=schedule_mode,
            exclude_appointment_id=appointment_id,
        )
        if not bookable:
            raise WindowNotAvailable

        updated = await self._repos.appointments.reschedule(
            appointment_id=appointment_id,
            starts_at=new_starts_at,
            ends_at=new_ends_at,
            status=appointment.status,
        )
        if updated is None:
            raise AppointmentNotFound

        await self._repos.appointments.add_reschedule_log(
            appointment_id=appointment_id,
            actor_user_id=master_user_id,
            kind=RescheduleKind.SHIFT,
            old_starts_at=old_starts_at,
            old_ends_at=old_ends_at,
            new_starts_at=updated.starts_at,
            new_ends_at=updated.ends_at,
        )
        logger.info(
            "Late-shifted appointment %d by master=%d: +%d min → %s",
            appointment_id,
            master_user_id,
            minutes,
            updated.starts_at,
        )
        return RescheduleResult(
            appointment=updated,
            old_starts_at=old_starts_at,
            old_ends_at=old_ends_at,
        )

    async def client_min_lead_minutes(self, *, master_user_id: int) -> int:
        """Master's min_lead for client booking / reschedule checks."""
        settings = await self._repos.master_settings.get_by_master(
            master_user_id=master_user_id,
        )
        if settings is not None:
            return settings.min_lead_minutes
        return AvailabilityService.default_settings(master_user_id).min_lead_minutes

    @staticmethod
    def is_client_reschedule_too_late(
        *,
        starts_at: datetime,
        min_lead_minutes: int,
        now: datetime,
    ) -> bool:
        return starts_at < now + timedelta(minutes=min_lead_minutes)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
