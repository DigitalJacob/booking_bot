from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.domain.time_range import as_utc, intervals_overlap

_T0 = datetime(2026, 10, 11, 10, 0, tzinfo=UTC)
_T1 = datetime(2026, 10, 11, 11, 0, tzinfo=UTC)
_T2 = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
_T3 = datetime(2026, 10, 11, 13, 0, tzinfo=UTC)


def test_intervals_overlap_partial():
    assert intervals_overlap(_T0, _T2, _T1, _T3)


def test_intervals_overlap_contained():
    assert intervals_overlap(_T0, _T3, _T1, _T2)


def test_intervals_overlap_identical():
    assert intervals_overlap(_T0, _T1, _T0, _T1)


def test_intervals_no_overlap_adjacent_half_open():
    """Touching at an endpoint does not count as overlap."""
    assert not intervals_overlap(_T0, _T1, _T1, _T2)
    assert not intervals_overlap(_T1, _T2, _T0, _T1)


def test_intervals_no_overlap_gap():
    assert not intervals_overlap(_T0, _T1, _T2, _T3)


def test_as_utc_naive_assumes_utc():
    naive = datetime(2026, 10, 11, 10, 0)
    assert as_utc(naive) == naive.replace(tzinfo=UTC)


def test_as_utc_converts_aware():
    local = datetime(2026, 10, 11, 13, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    assert as_utc(local) == datetime(2026, 10, 11, 10, 0, tzinfo=UTC)
