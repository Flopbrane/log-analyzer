# -*- coding: utf-8 -*-
"""Search text preprocessing helpers for LogViewer."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from logs.time_utils import to_world_local_datetime


TIME_HH_MM_PATTERN: re.Pattern[str] = re.compile(r"\d{1,2}:\d{1,2}")


def collect_log_dates(
    rows: Sequence[Mapping[str, Any]],
    timezone_name: str,
) -> list[date]:
    """Return unique local dates from loaded log rows.

    This intentionally reads dates only from loaded log rows. It must not use
    datetime.now(), because search intent should be based on the opened logs.
    """
    dates: set[date] = set()
    for row in rows:
        raw_time = row.get("time")
        if not isinstance(raw_time, str):
            continue
        local_dt: datetime | None = to_world_local_datetime(raw_time, timezone_name)
        if local_dt is not None:
            dates.add(local_dt.date())
    return sorted(dates)


def build_search_text_datetime(
    search_text: str,
    rows: Sequence[Mapping[str, Any]],
    timezone_name: str,
) -> str:
    """Expand time-only search text using dates from the loaded logs.

    For a single-day log, "10:15" becomes "YYYY-MM-DD 10:15".
    For multi-day logs, a single "10:15" remains a time-only query so it can
    match every loaded date. Open ranges still use the first loaded log date
    because the existing parser needs a concrete date for range bounds.
    """
    text = search_text.strip()
    if not text or not rows:
        return search_text

    log_dates = collect_log_dates(rows, timezone_name)
    if not log_dates:
        return search_text

    date_str = log_dates[0].isoformat()
    single_day = len(log_dates) == 1

    match_range = re.fullmatch(
        rf"({TIME_HH_MM_PATTERN.pattern})\.\.({TIME_HH_MM_PATTERN.pattern})",
        text,
    )
    if match_range:
        start_time = match_range.group(1)
        end_time = match_range.group(2)
        return f"{date_str} {start_time}..{date_str} {end_time}"

    match_start = re.fullmatch(rf"({TIME_HH_MM_PATTERN.pattern})\.\.", text)
    if match_start:
        start_time = match_start.group(1)
        return f"{date_str} {start_time}.."

    match_end = re.fullmatch(rf"\.\.({TIME_HH_MM_PATTERN.pattern})", text)
    if match_end:
        end_time = match_end.group(1)
        return f"..{date_str} {end_time}"

    match_single = re.fullmatch(TIME_HH_MM_PATTERN, text)
    if match_single and single_day:
        return f"{date_str} {text}"

    return search_text
