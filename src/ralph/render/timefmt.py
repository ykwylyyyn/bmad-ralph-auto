from __future__ import annotations

from datetime import datetime, timezone


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_duration_between(start: str | None, end: str | None = None) -> str:
    start_dt = parse_timestamp(start)
    if start_dt is None:
        return "0s"
    end_dt = parse_timestamp(end) if end is not None else datetime.now(timezone.utc)
    if end_dt is None:
        end_dt = datetime.now(timezone.utc)
    total_seconds = max(0, int((end_dt - start_dt).total_seconds()))
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        if seconds:
            return f"{minutes}m {seconds}s"
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if minutes:
        return f"{hours}h {minutes}m"
    return f"{hours}h"
