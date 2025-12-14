from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class ScheduleTimeError(ValueError):
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def compute_run_at_from_components(
    *,
    month: int,
    day: int,
    hour: int,
    minute: int,
    now: Optional[datetime] = None,
    year: Optional[int] = None,
) -> int:
    """
    Compute unix epoch seconds for an absolute schedule time in the bot's local timezone.

    Rules:
    - Uses current local timezone (from `now`) for timestamp conversion.
    - Defaults `year` to current year.
    - Rejects invalid dates (e.g. Feb 30).
    - Requires scheduled time to be in the future (strictly > now).
    """
    if now is None:
        now = datetime.now().astimezone()

    if year is None:
        year = now.year

    tz = now.tzinfo
    if tz is None:
        raise ScheduleTimeError("Cannot determine local timezone.")

    try:
        target = datetime(year, month, day, hour, minute, tzinfo=tz)
    except ValueError as e:
        raise ScheduleTimeError(f"Invalid date/time: {e}") from e

    if target <= now:
        raise ScheduleTimeError("Scheduled time must be in the future.")

    return int(target.timestamp())


def compute_next_occurrence_from_hour_minute(
    *,
    hour: int,
    minute: int,
    now: Optional[datetime] = None,
) -> int:
    """
    Compute unix epoch seconds for the next occurrence of HH:MM in the bot's local timezone.
    """
    if now is None:
        now = datetime.now().astimezone()

    tz = now.tzinfo
    if tz is None:
        raise ScheduleTimeError("Cannot determine local timezone.")

    try:
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError as e:
        raise ScheduleTimeError(f"Invalid time: {e}") from e

    if target <= now:
        target = target + timedelta(days=1)

    return int(target.timestamp())
