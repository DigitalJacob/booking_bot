from datetime import UTC, datetime, timedelta

from app.bot.reminders import _recipient_user_id
from app.domain.enums import AppointmentStatus, ReminderKind
from app.domain.models import Appointment

CREATED = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _appt(*, client_user_id: int | None) -> Appointment:
    starts = CREATED + timedelta(hours=2)
    return Appointment(
        id=1,
        client_user_id=client_user_id,
        master_user_id=100,
        service_id=1,
        starts_at=starts,
        ends_at=starts + timedelta(minutes=60),
        status=AppointmentStatus.CONFIRMED,
        created_at=CREATED,
        manual_client_id=None if client_user_id is not None else 7,
    )


def test_recipient_for_client_kinds_is_none_without_telegram_client():
    appt = _appt(client_user_id=None)
    assert _recipient_user_id(appt, ReminderKind.CLIENT_HOUR) is None
    assert _recipient_user_id(appt, ReminderKind.CLIENT_EVENING) is None
    assert _recipient_user_id(appt, ReminderKind.MASTER_HOUR) == 100
    assert _recipient_user_id(appt, ReminderKind.MASTER_EVENING) == 100


def test_recipient_for_client_kinds_uses_telegram_id():
    appt = _appt(client_user_id=200)
    assert _recipient_user_id(appt, ReminderKind.CLIENT_HOUR) == 200
    assert _recipient_user_id(appt, ReminderKind.MASTER_HOUR) == 100
