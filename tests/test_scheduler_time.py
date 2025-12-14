import pytest
from datetime import datetime, timezone

from features.scheduling.time_utils import (
    ScheduleTimeError,
    compute_next_occurrence_from_hour_minute,
    compute_run_at_from_components,
)


def test_compute_run_at_rejects_invalid_date():
    now = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ScheduleTimeError):
        compute_run_at_from_components(month=2, day=30, hour=12, minute=0, now=now)


def test_compute_run_at_rejects_past_time():
    now = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ScheduleTimeError):
        compute_run_at_from_components(month=6, day=1, hour=11, minute=59, now=now)


def test_compute_run_at_returns_epoch_seconds_for_future_time():
    now = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    run_at = compute_run_at_from_components(month=6, day=1, hour=12, minute=1, now=now)
    assert run_at == int(datetime(2025, 6, 1, 12, 1, tzinfo=timezone.utc).timestamp())


def test_next_occurrence_from_hour_minute_moves_to_next_day_if_needed():
    now = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    run_at = compute_next_occurrence_from_hour_minute(hour=11, minute=59, now=now)
    assert run_at == int(datetime(2025, 6, 2, 11, 59, tzinfo=timezone.utc).timestamp())
