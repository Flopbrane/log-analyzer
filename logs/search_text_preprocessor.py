# -*- coding: utf-8 -*-
"""LogViewer用のテキスト前処理ヘルパーを提供するモジュール。"""
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
    """ロードされたログ行から一意のローカル日付を返す。

    この関数は意図的にロードされたログ行からのみ日付を読み取ります。
    datetime.now() は使用しません。検索の意図は開かれたログに基づくべきだからです。
    """
    dates: set[date] = set()
    for row in rows:
        raw_time: Any | None = row.get("time")
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
    """ロードされたログから日付を使用して、時刻のみの検索テキストを展開する。

    単一日のログの場合、"10:15" は "YYYY-MM-DD 10:15" に変換されます。
    複数日のログの場合、単一の "10:15" は時刻のみのクエリとして残り、
    すべての読み込まれた日付に一致する可能性があります。オープンレンジは
    既存のパーサーが範囲の境界に具体的な日付を必要とするため、最初の
    読み込まれたログ日付を使用します。
    """
    text: str = search_text.strip()
    if not text or not rows:
        return search_text

    log_dates: list[date] = collect_log_dates(rows, timezone_name)
    if not log_dates:
        return search_text

    date_str: str = log_dates[0].isoformat()
    single_day: bool = len(log_dates) == 1

    match_range: re.Match[str] | None = re.fullmatch(
        rf"({TIME_HH_MM_PATTERN.pattern})\.\.({TIME_HH_MM_PATTERN.pattern})",
        text,
    )
    if match_range:
        start_time: str | Any = match_range.group(1)
        end_time: str | Any = match_range.group(2)
        return f"{date_str} {start_time}..{date_str} {end_time}"

    match_start: re.Match[str] | None = re.fullmatch(rf"({TIME_HH_MM_PATTERN.pattern})\.\.", text)
    if match_start:
        start_time: str | Any = match_start.group(1)
        return f"{date_str} {start_time}.."

    match_end: re.Match[str] | None = re.fullmatch(rf"\.\.({TIME_HH_MM_PATTERN.pattern})", text)
    if match_end:
        end_time: str | Any = match_end.group(1)
        return f"..{date_str} {end_time}"

    match_single: re.Match[str] | None = re.fullmatch(TIME_HH_MM_PATTERN, text)
    if match_single and single_day:
        return f"{date_str} {text}"

    return search_text
