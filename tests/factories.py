from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import cast

from app.domain.enums import AppointmentStatus
from app.domain.models import Appointment, Service, Slot
from app.infrastructure.database.repositories import (
    AppointmentsRepository,
    Repositories,
    ServicesRepository,
    SlotsRepository,
    UsersRepository,
)


MASTER_ID = 100
CLIENT_ID = 200
OTHER_ID = 300

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def make_service(
        *,
        service_id: int = 1,
        master_user_id: int = MASTER_ID,
        duration_minutes: int = 60,
        is_active: bool = True,
) -> Service:
    return Service(
        id=service_id,
        master_user_id=master_user_id,
        title=f"Service {service_id}",
        duration_minutes=duration_minutes,
        price=Decimal("1500"),
        is_active=is_active,
        created_at=NOW,
    )


def make_slot(
        *,
        slot_id: int = 1,
        master_user_id: int = MASTER_ID,
        starts_in_hours: int = 2,
        duration_minutes: int = 60,
) -> Slot:
    starts_at = NOW + timedelta(hours=starts_in_hours)
    return Slot(
        id=slot_id,
        master_user_id=master_user_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=duration_minutes),
        created_at=NOW,
    )


def make_appointment(
        *,
        appointment_id: int = 1,
        client_user_id: int = CLIENT_ID,
        master_user_id: int = MASTER_ID,
        service_id = 1,
        slot_id: int = 1,
        status: AppointmentStatus = AppointmentStatus.PENDING,
) -> Appointment:
    return Appointment(
        id=appointment_id,
        client_user_id=client_user_id,
        master_user_id=master_user_id,
        service_id=service_id,
        slot_id=slot_id,
        status=status,
        created_at=NOW,
    )


class FakeServicesRepository:
    def __init__(self, services: list[Service]) -> None:
        self._services = {service.id: service for service in services}

    async def get_service(self, *, service_id: int) -> Service | None:
        return self._services.get(service_id)

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            active_only: bool = False,
    ) -> list[Service]:
        return [
            service for service in self._services.values()
            if service.master_user_id == master_user_id
            and (not active_only or service.is_active)
        ]


class FakeSlotsRepository:
    def __init__(
            self,
            slots: list[Slot],
            taken_slot_ids: set[int] | None = None,
    ) -> None:
        self._slots = {slot.id: slot for slot in slots}
        self._taken = taken_slot_ids or set()

    async def get_slot(self, *, slot_id: int) -> Slot | None:
        return self._slots.get(slot_id)

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            available_only: bool = False,
    ) -> list[Slot]:
        result = [
            slot for slot in self._slots.values()
            if slot.master_user_id == master_user_id
            and (from_dt is None or slot.starts_at >= from_dt)
            and (not available_only or slot.id not in self._taken)
        ]
        return sorted(result, key=lambda slot: slot.starts_at)


class FakeAppointmentsRepository:
    def __init__(
            self,
            appointments: list[Appointment],
            slots: list[Slot] | None = None,
    ) -> None:
        self._appointments = {item.id: item for item in appointments}
        self._slots = {slot.id: slot for slot in (slots or [])}
        self._next_id = max(self._appointments, default=0) + 1

    async def add_appointment(
            self,
            *,
            client_user_id: int,
            master_user_id: int,
            service_id: int,
            slot_id: int,
            status: AppointmentStatus = AppointmentStatus.PENDING,
    ) -> Appointment:
        appointment = make_appointment(
            appointment_id=self._next_id,
            client_user_id=client_user_id,
            master_user_id=master_user_id,
            service_id=service_id,
            slot_id=slot_id,
            status=status,
        )
        self._appointments[appointment.id] = appointment
        self._next_id += 1
        return appointment

    async def get_appointment(
            self,
            *,
            appointment_id: int,
    ) -> Appointment | None:
        return self._appointments.get(appointment_id)

    async def get_active_by_slot(
            self,
            *,
            slot_id: int,
    ) -> Appointment | None:
        for appointment in self._appointments.values():
            if appointment.slot_id == slot_id and appointment.status in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            ):
                return appointment
        return None

    async def list_by_client(
            self,
            *,
            client_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]:
        result = []
        for appointment in self._appointments.values():
            if appointment.client_user_id != client_user_id:
                continue
            slot = self._slots.get(appointment.slot_id)
            if slot is None:
                continue
            if from_dt is not None and slot.starts_at < from_dt:
                continue
            if to_dt is not None and slot.starts_at >= to_dt:
                continue
            result.append(appointment)
        return sorted(
            result,
            key=lambda item: self._slots[item.slot_id].starts_at,
        )

    async def change_status(
            self,
            *,
            appointment_id: int,
            status: AppointmentStatus,
    ) -> Appointment | None:
        appointment = self._appointments.get(appointment_id)
        if appointment is None:
            return None
        updated = replace(appointment, status=status)
        self._appointments[appointment_id] = updated
        return updated


def make_repos(
        *,
        services: list[Service] | None = None,
        slots: list[Slot] | None = None,
        appointments: list[Appointment] | None = None,
        taken_slot_ids: set[int] | None = None,
) -> Repositories:
    slots = slots or []
    return Repositories(
        users=cast(UsersRepository, None),
        services=cast(
            ServicesRepository,
            FakeServicesRepository(services or []),
        ),
        slots=cast(
            SlotsRepository,
            FakeSlotsRepository(slots, taken_slot_ids),
        ),
        appointments=cast(
            AppointmentsRepository,
            FakeAppointmentsRepository(appointments or [], slots),
        ),
    )
