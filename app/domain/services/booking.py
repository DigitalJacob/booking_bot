import logging
from datetime import datetime, timezone

from psycopg.errors import UniqueViolation

from app.domain.enums import AppointmentStatus
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
    ServiceInactive,
    ServiceNotFound,
    SlotInThePast,
    SlotMasterMismatch,
    SlotNotFound,
    SlotTaken,
)
from app.domain.models import Appointment, Service, Slot
from app.infrastructure.database.repositories import Repositories


logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, repos: Repositories) -> None:
        self._repos = repos

    async def list_services(self, *, master_user_id: int) -> list[Service]:
        return await self._repos.services.list_by_master(
            master_user_id=master_user_id,
            active_only=True,
        )

    async def list_available_slots(
            self,
            *,
            master_user_id: int,
            now: datetime | None = None,
    ) -> list[Slot]:
        if now is None:
            now = datetime.now(timezone.utc)
        return await self._repos.slots.list_by_master(
            master_user_id=master_user_id,
            from_dt=now,
            available_only=True,
        )

    async def book(
            self,
            *,
            client_user_id: int,
            service_id: int,
            slot_id: int,
            now: datetime | None = None
    ) -> Appointment:
        if now is None:
            now = datetime.now(timezone.utc)

        service = await self._repos.services.get_service(service_id=service_id)
        if service is None:
            raise ServiceNotFound
        if not service.is_active:
            raise ServiceInactive

        slot = await self._repos.slots.get_slot(slot_id=slot_id)
        if slot is None:
            raise SlotNotFound
        if slot.master_user_id != service.master_user_id:
            raise SlotMasterMismatch
        if slot.starts_at <= now:
            raise SlotInThePast

        taken = await self._repos.appointments.get_active_by_slot(slot_id=slot_id)
        if taken is not None:
            raise SlotTaken

        try:
            appointment = await self._repos.appointments.add_appointment(
                client_user_id=client_user_id,
                master_user_id=slot.master_user_id,
                service_id=service_id,
                slot_id=slot_id,
                status=AppointmentStatus.PENDING,
            )
        except UniqueViolation as e:
            raise SlotTaken from e

        logger.info(
            "Booked appointment %d: client=%d, master=%d, slot=%d",
            appointment.id,
            client_user_id,
            slot.master_user_id,
            slot.id,
        )
        return appointment

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
