from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.enums import AppointmentStatus, ReminderKind
from app.domain.models import Appointment
from app.domain.services.reminders import (
    filter_due_reminders,
    is_evening_reminder_due,
    is_hour_reminder_due,
    is_reminder_due,
)

TZ = "Europe/Moscow"
MSK = ZoneInfo(TZ)
CREATED = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _appt(
        *,
        starts_at: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
        client_evening_reminded_at: datetime | None = None,
        client_hour_reminded_at: datetime | None = None,
        master_evening_reminded_at: datetime | None = None,
        master_hour_reminded_at: datetime | None = None,
        appointment_id: int = 1,
) -> Appointment:
    return Appointment(
        id=appointment_id,
        client_user_id=200,
        master_user_id=100,
        service_id=1,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=60),
        status=status,
        created_at=CREATED,
        client_evening_reminded_at=client_evening_reminded_at,
        client_hour_reminded_at=client_hour_reminded_at,
        master_evening_reminded_at=master_evening_reminded_at,
        master_hour_reminded_at=master_hour_reminded_at,
    )


def _local(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=MSK)


class TestHourReminder:
    def test_due_inside_lead_window(self) -> None:
        starts = _local(2026, 10, 5, 15, 0).astimezone(UTC)
        now = starts - timedelta(minutes=45)
        appt = _appt(starts_at=starts)
        assert is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_HOUR,
            now=now,
            lead_minutes=60,
        )
        assert is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.MASTER_HOUR,
            now=now,
            lead_minutes=60,
        )

    def test_not_due_before_lead_window(self) -> None:
        starts = _local(2026, 10, 5, 15, 0).astimezone(UTC)
        now = starts - timedelta(minutes=90)
        appt = _appt(starts_at=starts)
        assert not is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_HOUR,
            now=now,
            lead_minutes=60,
        )

    def test_not_due_after_start(self) -> None:
        starts = _local(2026, 10, 5, 15, 0).astimezone(UTC)
        now = starts + timedelta(minutes=1)
        appt = _appt(starts_at=starts)
        assert not is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_HOUR,
            now=now,
            lead_minutes=60,
        )

    def test_not_due_when_already_sent(self) -> None:
        starts = _local(2026, 10, 5, 15, 0).astimezone(UTC)
        now = starts - timedelta(minutes=30)
        appt = _appt(
            starts_at=starts,
            client_hour_reminded_at=now - timedelta(minutes=5),
        )
        assert not is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_HOUR,
            now=now,
            lead_minutes=60,
        )
        assert is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.MASTER_HOUR,
            now=now,
            lead_minutes=60,
        )

    def test_skips_pending_and_cancelled(self) -> None:
        starts = _local(2026, 10, 5, 15, 0).astimezone(UTC)
        now = starts - timedelta(minutes=30)
        for status in (AppointmentStatus.PENDING, AppointmentStatus.CANCELLED):
            appt = _appt(starts_at=starts, status=status)
            assert not is_hour_reminder_due(
                appointment=appt,
                kind=ReminderKind.CLIENT_HOUR,
                now=now,
                lead_minutes=60,
            )

    def test_evening_kind_rejected(self) -> None:
        starts = _local(2026, 10, 5, 15, 0).astimezone(UTC)
        now = starts - timedelta(minutes=30)
        appt = _appt(starts_at=starts)
        assert not is_hour_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            lead_minutes=60,
        )


class TestEveningReminder:
    def test_due_in_window_day_before(self) -> None:
        # Appointment tomorrow 11:00 MSK; now today 20:30 MSK.
        starts = _local(2026, 10, 6, 11, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 20, 30).astimezone(UTC)
        appt = _appt(starts_at=starts)
        assert is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )
        assert is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.MASTER_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )

    def test_not_due_before_window(self) -> None:
        starts = _local(2026, 10, 6, 11, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 19, 59).astimezone(UTC)
        appt = _appt(starts_at=starts)
        assert not is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )

    def test_not_due_at_end_exclusive(self) -> None:
        starts = _local(2026, 10, 6, 11, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 22, 0).astimezone(UTC)
        appt = _appt(starts_at=starts)
        assert not is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )

    def test_not_due_same_calendar_day(self) -> None:
        starts = _local(2026, 10, 5, 23, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 20, 30).astimezone(UTC)
        appt = _appt(starts_at=starts)
        assert not is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )

    def test_not_due_two_days_ahead(self) -> None:
        starts = _local(2026, 10, 7, 11, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 20, 30).astimezone(UTC)
        appt = _appt(starts_at=starts)
        assert not is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )

    def test_not_due_when_already_sent(self) -> None:
        starts = _local(2026, 10, 6, 11, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 20, 30).astimezone(UTC)
        appt = _appt(
            starts_at=starts,
            master_evening_reminded_at=now - timedelta(minutes=10),
        )
        assert not is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.MASTER_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )
        assert is_evening_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            evening_hour_start=20,
            evening_hour_end=22,
        )


class TestFilterDueReminders:
    def test_filters_mixed_list(self) -> None:
        starts_tomorrow = _local(2026, 10, 6, 11, 0).astimezone(UTC)
        starts_hour = _local(2026, 10, 5, 21, 30).astimezone(UTC)
        now = _local(2026, 10, 5, 20, 45).astimezone(UTC)
        appointments = [
            _appt(starts_at=starts_tomorrow, appointment_id=1),
            _appt(
                starts_at=starts_tomorrow,
                status=AppointmentStatus.PENDING,
                appointment_id=2,
            ),
            _appt(starts_at=starts_hour, appointment_id=3),
        ]
        evening = filter_due_reminders(
            appointments=appointments,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            lead_minutes=60,
            evening_hour_start=20,
            evening_hour_end=22,
        )
        assert [a.id for a in evening] == [1]

        hour = filter_due_reminders(
            appointments=appointments,
            kind=ReminderKind.CLIENT_HOUR,
            now=now,
            timezone_name=TZ,
            lead_minutes=60,
            evening_hour_start=20,
            evening_hour_end=22,
        )
        assert [a.id for a in hour] == [3]

    def test_is_reminder_due_dispatches(self) -> None:
        starts = _local(2026, 10, 6, 11, 0).astimezone(UTC)
        now = _local(2026, 10, 5, 20, 30).astimezone(UTC)
        appt = _appt(starts_at=starts)
        assert is_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_EVENING,
            now=now,
            timezone_name=TZ,
            lead_minutes=60,
            evening_hour_start=20,
            evening_hour_end=22,
        )
        assert not is_reminder_due(
            appointment=appt,
            kind=ReminderKind.CLIENT_HOUR,
            now=now,
            timezone_name=TZ,
            lead_minutes=60,
            evening_hour_start=20,
            evening_hour_end=22,
        )
