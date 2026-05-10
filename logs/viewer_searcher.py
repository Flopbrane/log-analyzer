# -*- coding: utf-8 -*-
"""ログビューアの検索ロジックを実メソッドで検証するテストScript。"""
#########################
# Author: F.Kurokawa
# Description:
# LogViewer の検索テキストボックスを実メソッドで検証するテストScript。
#########################


from __future__ import annotations

import re
import sys
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final, Sequence, cast

from zoneinfo import ZoneInfo

import logs.log_viewer as lv
from logs.log_searcher import collect_logs, summarize
from logs.log_types import LogDict

print("DEBUG IMPORT:", lv.__file__)

DEFAULT_FILENAMES: Final[list[str]] = [
    "alarm_2026-04-22.jsonl",
    "alarm_2026-04-23.jsonl",
    "alarm_2026-04-24.jsonl",
]


@dataclass(frozen=True)
class SearchCase:
    """検索欄テスト1件分"""

    query: str
    expected: int
    note: str

@dataclass(slots=True)
class SearchQuery:
    text: str
    start: datetime | None
    end: datetime | None
    field: str | None


def to_local_datetime(raw_time: object, tz: ZoneInfo) -> datetime | None:
    """ログの time をローカルdatetimeへ変換する"""
    if not isinstance(raw_time, str):
        return None

    try:
        dt: datetime = datetime.fromisoformat(raw_time)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(tz)


def flatten_text(value: object) -> str:
    """dict/listを含むログ全体を検索用テキストに潰す"""
    if isinstance(value, dict):
        value_dict: dict[object, object] = cast(dict[object, object], value)  # type: ignore[reportUnnecessaryCast]
        parts: list[str] = []
        for k, v in value_dict.items():
            parts.append(str(k))
            parts.append(flatten_text(v))
        return " ".join(parts)

    if isinstance(value, (list, tuple, set)):
        return " ".join(flatten_text(cast(object, v)) for v in value)  # type: ignore[reportUnnecessaryCast]

    return str(value)

# =========================================
# 日時クエリ解析
# =========================================
def parse_date_or_datetime(text: str, *, is_end: bool, tz: ZoneInfo) -> datetime | None:
    """YYYY-MM-DD / YYYY-MM-DD HH:MM / ISO文字列をdatetimeへ変換"""
    text = text.strip()
    if not text:
        return None

    # YYYY-MM-DD のみ
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        suffix: str = "23:59:59.999999" if is_end else "00:00:00"
        return datetime.fromisoformat(f"{text} {suffix}").replace(tzinfo=tz)

    # YYYY-MM-DD HH:MM のように分だけなら、終了側はその分の末尾へ
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", text):
        suffix: str = ":59.999999" if is_end else ":00"
        normalized: str = text.replace("T", " ") + suffix
        return datetime.fromisoformat(normalized).replace(tzinfo=tz)

    # YYYY-MM-DD HH:MM:SS または ISO
    try:
        normalized: str = text.replace("T", " ")
        dt: datetime = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)

    return dt


def is_date_query(query: str) -> bool:
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", query) is not None


def is_time_query(query: str) -> bool:
    return re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", query) is not None


def is_datetime_prefix_query(query: str) -> bool:
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?", query) is not None

# =========================================
# 検索判定
# =========================================
def match_field_query(log: dict[str, Any], query: str) -> bool | None:
    """level:ERROR / message:test_error などのフィールド指定検索"""
    if ":" not in query:
        return None
    field: str
    keyword: str

    field, keyword = query.split(":", 1)
    field = field.strip().lower()
    keyword = keyword.strip().lower()

    field_map: dict[str, str] = {
        "level": "level",
        "message": "what.message",
        "function": "where.function",
        "func": "where.function",
        "file": "where.file",
        "trace": "trace_id",
        "trace_id": "trace_id",
        "output": "output",
        "context": "context",
    }

    dotted_key: str | None = field_map.get(field)
    if dotted_key is None:
        return None

    value: object = get_nested_value(log, dotted_key)
    value_text: str = flatten_text(value).lower()

    if field == "level":
        return value_text == keyword

    return keyword in value_text


def match_search_query(log: dict[str, Any], query: str, tz: ZoneInfo) -> bool:
    """検索テキストボックス1回分の判定"""
    query = query.strip()
    if not query:
        return True

    local_dt: datetime | None = to_local_datetime(log.get("time"), tz)

    # 期間検索: 2026-04-23..2026-04-24
    if ".." in query:
        start_text, end_text = query.split("..", 1)
        start_dt: datetime | None = parse_date_or_datetime(start_text, is_end=False, tz=tz)
        end_dt: datetime | None = parse_date_or_datetime(end_text, is_end=True, tz=tz)
        if local_dt is None or start_dt is None or end_dt is None:
            return False
        return start_dt <= local_dt <= end_dt

    # フィールド指定検索
    field_result: bool | None = match_field_query(log, query)
    if field_result is not None:
        return field_result

    # 年月日検索
    if is_date_query(query):
        return local_dt is not None and local_dt.strftime("%Y-%m-%d") == query

    # 時刻検索 HH:MM / HH:MM:SS
    if is_time_query(query):
        return local_dt is not None and local_dt.strftime("%H:%M:%S").startswith(query)

    # 日時プレフィックス検索 YYYY-MM-DD HH:MM
    if is_datetime_prefix_query(query):
        normalized: str = query.replace("T", " ")
        return local_dt is not None and local_dt.strftime("%Y-%m-%d %H:%M:%S").startswith(normalized)

    # 通常の全文検索
    blob: str = flatten_text(log).lower()
    if local_dt is not None:
        blob += " " + local_dt.strftime("%Y-%m-%d %H:%M:%S").lower()
    return query.lower() in blob

def get_nested_value(data: dict[str, Any], dotted_key: str) -> object:
    """辞書のネストされた値を取得する。dotted_keyは "where.function" のような形式"""
    keys: list[str] = dotted_key.split(".")
    current: object = data

    for key in keys:
        if not isinstance(current, dict):
            return ""
        current_dict: dict[str, Any] = cast(dict[str, Any], current)  # type: ignore[reportUnnecessaryCast]
        current = current_dict.get(key, "")

    return current

# ==========================
# ログファイルを探す
# ==========================
def get_log_files(
    log_dir: Path,
    start: date | None = None,
    end: date | None = None,
) -> list[Path]:
    """ログファイルを探す関数。日付クエリに合致するファイルだけ返す。"""
    result: list[Path] = []
    for p in log_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".jsonl", ".log"):
            continue

        file_date: date | None = extract_date_from_path(p)
        if file_date is None:
            continue

        if start and file_date < start:
            continue
        if end and file_date > end:
            continue

        result.append(p)
    return result

def extract_date_from_path(path: Path) -> date | None:
    """ファイル名から日付を抽出する。例: alarm_2026-04-22.jsonl -> 2026-04-22"""
    match: re.Match[str] | None = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None

# ==========================
# 重要イベントを抽出する(全体の入口)
# ==========================
def search_logs(
    log_dir: Path,
    start: date | None = None,
    end: date | None = None,
) -> list[LogDict]:
    """ログファイルから重要イベントを抽出する関数。日付クエリもここで処理する。"""
    files: list[Path] = get_log_files(log_dir, start, end)
    all_logs: list[LogDict] = []
    for file in files:
        logs: list[LogDict] = collect_logs(file)
        all_logs.extend(logs)

    return all_logs


