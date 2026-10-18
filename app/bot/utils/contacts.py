"""Resolve display name + phone for TG users and appointments."""

from __future__ import annotations

from app.domain.models import Appointment, User
from app.infrastructure.database.repositories import Repositories


def client_contact(user: User | None) -> tuple[str, str]:
    if user is None:
        return "?", "-"
    phone = user.phone or "-"
    return user.display_name, phone


async def appointment_client_contact(
    repos: Repositories,
    appointment: Appointment,
) -> tuple[str, str]:
    """Resolve display name + phone for a TG or manual appointment client."""
    if appointment.client_user_id is not None:
        user = await repos.users.get_user_by_id(user_id=appointment.client_user_id)
        return client_contact(user)
    if appointment.manual_client_id is not None:
        manual = await repos.manual_clients.get(
            manual_client_id=appointment.manual_client_id,
            master_user_id=appointment.master_user_id,
        )
        if manual is None:
            return "?", "-"
        return manual.name, manual.phone or "-"
    return "?", "-"
