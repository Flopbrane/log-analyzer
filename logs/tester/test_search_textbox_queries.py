# -*- coding: utf-8 -*-
"""LogViewer の検索テキストボックス用テストスクリプト。

目的:
- JSONLログを複数読み込む
- 検索テキストボックスに入れる想定の文字列を自動テストする
- 年月日 / 時刻 / 期間 / level / message / function / context などを確認する

使い方:
    python test_search_textbox_queries.py

または、任意のログファイルを指定:
    python test_search_textbox_queries.py alarm_2026-04-22.jsonl alarm_2026-04-23.jsonl alarm_2026-04-24.jsonl
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, cast

from zoneinfo import ZoneInfo

# =========================================
# 設定
# =========================================
TIMEZONE = "Asia/Tokyo"

# コマンドライン引数がない場合に使うログファイル
# 黒川さんの環境では、必要に応じてここを書き換えてください。
DEFAULT_LOAD_FILE_PATHS: list[Path] = [
    Path("alarm_2026-04-22.jsonl"),
    Path("alarm_2026-04-23.jsonl"),
    Path("alarm_2026-04-24.jsonl"),
]


@dataclass(frozen=True)
class SearchTestCase:
    """検索テキストボックス用テストケース"""

    query: str
    expected_count: int
    note: str = ""


# =========================================
# 読み込み
# =========================================
def load_jsonl(load_file_path: Path) -> list[dict[str, Any]]:
    """JSONLファイルを読み込む"""
    logs: list[dict[str, Any]] = []

    with load_file_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line: str = line.strip()
            if not line:
                continue
            try:
                raw: object = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[SKIP] JSON decode error: {load_file_path}:{line_no} {e}")
                continue

            if isinstance(raw, dict):
                logs.append(cast(dict[str, Any], raw))
            else:
                print(f"[SKIP] not dict: {load_file_path}:{line_no}")

    return logs


def load_logs(load_file_paths: Iterable[Path]) -> list[dict[str, Any]]:
    """複数JSONLを読み込む"""
    logs: list[dict[str, Any]] = []
    for load_file_path in load_file_paths:
        logs.extend(load_jsonl(load_file_path))
    return logs


# =========================================
# 値取得・変換
# =========================================
def get_nested_value(data: dict[str, Any], dotted_key: str) -> object:
    """where.function のようなドット区切りキーで値を取得する"""
    current: object = data

    for key in dotted_key.split("."):
        if not isinstance(current, dict):
            return None
        current_dict: dict[str, Any] = cast(dict[str, Any], current) # type: ignore[reportUnnecessaryCast]
        current = current_dict.get(key)

    return current


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
        value_dict: dict[object, object] = cast(dict[object, object], value) # type: ignore[reportUnnecessaryCast]
        parts: list[str] = []
        for k, v in value_dict.items():
            parts.append(str(k))
            parts.append(flatten_text(v))
        return " ".join(parts)

    if isinstance(value, (list, tuple, set)):
        return " ".join(flatten_text(cast(object, v)) for v in value) # type: ignore[reportUnnecessaryCast]

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


def search_logs(logs: list[dict[str, Any]], query: str, tz_name: str = TIMEZONE) -> list[dict[str, Any]]:
    """検索実行"""
    tz = ZoneInfo(tz_name)
    return [log for log in logs if match_search_query(log, query, tz)]


# =========================================
# テストケース
# =========================================
TEST_CASES: list[SearchTestCase] = [
    SearchTestCase("", 69, "空欄なら全件"),
    SearchTestCase("2026-04-22", 3, "年月日検索"),
    SearchTestCase("2026-04-23", 30, "年月日検索"),
    SearchTestCase("2026-04-24", 36, "年月日検索"),
    SearchTestCase("2026-04-23..2026-04-24", 66, "日付期間検索"),
    SearchTestCase("2026-04-23..2026-04-23", 30, "単日を期間形式で検索"),
    SearchTestCase("2026-04-23 14:49..2026-04-23 14:49", 12, "分単位の期間検索"),
    SearchTestCase("2026-04-23 15:00:31..2026-04-23 15:00:37", 18, "秒単位の期間検索"),
    SearchTestCase("10:15", 18, "時刻検索 HH:MM"),
    SearchTestCase("10:16", 18, "時刻検索 HH:MM"),
    SearchTestCase("2026-04-24 10:16", 18, "日時プレフィックス検索"),
    SearchTestCase("level:ERROR", 4, "レベル指定"),
    SearchTestCase("level:WARNING", 11, "レベル指定"),
    SearchTestCase("message:test_error", 4, "message指定"),
    SearchTestCase("message:system_cpu_percent", 24, "message指定"),
    SearchTestCase("message:system_gpu_status", 18, "message指定"),
    SearchTestCase("function:run_test", 20, "where.function指定"),
    SearchTestCase("file:system_monitor.py", 46, "where.file指定"),
    SearchTestCase("context:cpu_percent", 24, "contextキー検索"),
    SearchTestCase("context:gpu_mem_total_mb", 18, "contextキー検索"),
    SearchTestCase("trace_id:fc036f388b7542c48117d55c8ec1728c", 3, "trace_id指定"),
]


def resolve_load_file_paths() -> list[Path]:
    """CLI指定またはデフォルトからload_file_pathsを決める"""
    if len(sys.argv) >= 2:
        return [Path(p) for p in sys.argv[1:]]

    # スクリプトと同じフォルダにログがある想定
    script_dir: Path = Path(__file__).resolve().parent
    candidates: list[Path] = [script_dir / p for p in DEFAULT_LOAD_FILE_PATHS]

    if all(p.exists() for p in candidates):
        return candidates

    # カレントディレクトリにログがある想定
    return DEFAULT_LOAD_FILE_PATHS


def main() -> None:
    load_file_paths: list[Path] = resolve_load_file_paths()

    print("=== load files ===")
    for load_file_path in load_file_paths:
        print(load_file_path)

    logs: list[dict[str, Any]] = load_logs(load_file_paths)
    print(f"\nloaded logs: {len(logs)}")
    print("timezone:", TIMEZONE)
    print("\n=== search textbox tests ===")

    failed = 0
    for test_case in TEST_CASES:
        matched: list[dict[str, Any]] = search_logs(logs, test_case.query)
        actual_count: int = len(matched)
        ok: bool = actual_count == test_case.expected_count
        mark: str = "OK" if ok else "NG"
        print(
            f"[{mark}] query={test_case.query!r:<55} "
            f"expected={test_case.expected_count:<3} actual={actual_count:<3} "
            f"{test_case.note}"
        )
        if not ok:
            failed += 1

    print("\n=== result ===")
    if failed == 0:
        print("ALL OK")
    else:
        print(f"FAILED: {failed}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
