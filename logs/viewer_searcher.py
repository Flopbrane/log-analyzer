# -*- coding: utf-8 -*-
"""LogViewerの検索テキスト解析専用モジュール。"""
#########################
# Author: F.Kurokawa
# Description:
# LogViewerの検索テキストボックスに入力された文字列を解析する。
# ログの読み込みは行わず、Viewerが保持しているLogDictだけを判定する。
#########################
from __future__ import annotations

import operator
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any, Callable, Literal, TypeAlias, cast

from zoneinfo import ZoneInfo

from logs.log_types import LogDict

CompareOperator: TypeAlias = Literal["<", "<=", ">", ">=", "==", "!="]

FIELD_MAP: dict[str, str] = {
    "level": "level",
    "message": "what.message",
    "msg": "what.message",
    "function": "where.function",
    "func": "where.function",
    "file": "where.file",
    "trace": "trace_id",
    "trace_id": "trace_id",
    "output": "output",
    "context": "context",
}

COMPARE_FUNCS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def _empty_str_list() -> list[str]:
    return []


def _empty_str_dict() -> dict[str, str]:
    return {}


def _empty_ignore_rule_list() -> list[IgnoreRule]:
    return []


@dataclass(slots=True)
class IgnoreRule:
    """(ignore: <80) のような条件排除ルール。"""

    raw_text: str
    key: str | None = None
    operator: CompareOperator | None = None
    number: float | None = None


@dataclass(slots=True)
class SearchQuery:
    """ログViewer用の検索条件。"""

    raw_text: str = ""
    start: datetime | None = None
    end: datetime | None = None
    include_terms: list[str] = field(default_factory=_empty_str_list)
    exclude_terms: list[str] = field(default_factory=_empty_str_list)
    field_filters: dict[str, str] = field(default_factory=_empty_str_dict)
    ignore_rules: list[IgnoreRule] = field(default_factory=_empty_ignore_rule_list)


def resolve_timezone(tz: str | tzinfo) -> tzinfo:
    """タイムゾーン名をtzinfoにする。"""
    if isinstance(tz, tzinfo):
        return tz
    try:
        return ZoneInfo(tz)
    except Exception:
        if tz == "Asia/Tokyo":
            return timezone(timedelta(hours=9))
        return timezone.utc


def to_local_datetime(raw_time: object, tz: str | tzinfo) -> datetime | None:
    """ログのtimeを表示中タイムゾーンのdatetimeへ変換する。"""
    if not isinstance(raw_time, str):
        return None

    try:
        dt: datetime = datetime.fromisoformat(raw_time)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(resolve_timezone(tz))


def flatten_text(value: object) -> str:
    """dict/listを含む値を全文検索用テキストへ変換する。"""
    if isinstance(value, dict):
        value_dict: dict[object, object] = cast(dict[object, object], value)
        parts: list[str] = []
        for key, child_value in value_dict.items():
            parts.append(str(key))
            parts.append(flatten_text(child_value))
        return " ".join(parts)

    if isinstance(value, (list, tuple, set)):
        children: list[object] | tuple[object, ...] | set[object] = cast(
            list[object] | tuple[object, ...] | set[object],
            value,
        )
        return " ".join(flatten_text(child) for child in children)

    return str(value)


def get_nested_value(data: dict[str, Any], dotted_key: str) -> object:
    """where.function のようなドット区切りキーで値を取得する。"""
    current: object = data

    for key in dotted_key.split("."):
        if not isinstance(current, dict):
            return ""
        current_dict: dict[str, object] = cast(dict[str, object], current)
        current = current_dict.get(key, "")

    return current


def build_search_blob(log: LogDict, tz: str | tzinfo) -> str:
    """全文検索用の文字列を作る。"""
    blob: str = flatten_text(log).lower()
    local_dt: datetime | None = to_local_datetime(log.get("time"), tz)
    if local_dt is not None:
        blob += " " + local_dt.strftime("%Y-%m-%d %H:%M:%S").lower()
        blob += " " + local_dt.isoformat(timespec="seconds").lower()
    return blob


def parse_date_or_datetime(text: str, *, is_end: bool, tz: str | tzinfo) -> datetime | None:
    """YYYY-MM-DD / YYYY-MM-DD HH:MM / ISO文字列をdatetimeへ変換する。"""
    text = text.strip()
    if not text:
        return None

    local_tz: tzinfo = resolve_timezone(tz)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        suffix: str = "23:59:59.999999" if is_end else "00:00:00"
        return datetime.fromisoformat(f"{text} {suffix}").replace(tzinfo=local_tz)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", text):
        suffix = ":59.999999" if is_end else ":00"
        normalized: str = text.replace("T", " ") + suffix
        return datetime.fromisoformat(normalized).replace(tzinfo=local_tz)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", text):
        suffix = ".999999" if is_end else ""
        normalized = text.replace("T", " ") + suffix
        return datetime.fromisoformat(normalized).replace(tzinfo=local_tz)

    try:
        normalized = text.replace("T", " ")
        dt: datetime = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=local_tz)

    return dt.astimezone(local_tz)


def is_date_query(query: str) -> bool:
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", query) is not None


def is_time_query(query: str) -> bool:
    return re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", query) is not None


def is_datetime_prefix_query(query: str) -> bool:
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?", query) is not None


def split_range_query(query: str) -> tuple[str, str] | None:
    """期間検索を start/end に分解する。"""
    if ".." in query:
        start_text, end_text = query.split("..", 1)
        return start_text.strip(), end_text.strip()

    if " - " in query:
        start_text, end_text = query.split(" - ", 1)
        return start_text.strip(), end_text.strip()

    return None


def parse_ignore_rule(text: str) -> IgnoreRule:
    """ignore句をルールへ変換する。"""
    raw_text: str = text.strip()
    match: re.Match[str] | None = re.fullmatch(
        r"(?:(?P<key>[A-Za-z_][\w.]*)\s*)?"
        r"(?P<op><=|>=|==|!=|<|>)\s*"
        r"(?P<num>-?\d+(?:\.\d+)?)",
        raw_text,
    )

    if match is None:
        return IgnoreRule(raw_text=raw_text)

    return IgnoreRule(
        raw_text=raw_text,
        key=match.group("key"),
        operator=cast(CompareOperator, match.group("op")),
        number=float(match.group("num")),
    )


def parse_query(raw_text: str) -> SearchQuery:
    """検索文字列をSearchQueryに変換する。"""
    include_terms: list[str] = []
    exclude_terms: list[str] = []
    field_filters: dict[str, str] = {}
    ignore_rules: list[IgnoreRule] = []

    def collect_ignore(match: re.Match[str]) -> str:
        ignore_rules.append(parse_ignore_rule(match.group(1)))
        return " "

    query_text: str = re.sub(
        r"\(\s*ignore\s*:\s*([^)]+)\)",
        collect_ignore,
        raw_text,
        flags=re.IGNORECASE,
    )

    for token in query_text.split():
        if not token:
            continue
        if token.startswith("-") and len(token) > 1:
            exclude_terms.append(token[1:].lower())
            continue
        if ":" in token:
            key, value = token.split(":", 1)
            if key.lower() in FIELD_MAP:
                field_filters[key.lower()] = value.lower()
                continue
        include_terms.append(token.lower())

    return SearchQuery(
        raw_text=raw_text,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        field_filters=field_filters,
        ignore_rules=ignore_rules,
    )


def match_field_filters(log: LogDict, field_filters: dict[str, str]) -> bool:
    """level:ERROR / message:test_error などのフィールド指定検索。"""
    for search_field, keyword in field_filters.items():
        dotted_key: str | None = FIELD_MAP.get(search_field)
        if dotted_key is None:
            return False

        value: object = get_nested_value(cast(dict[str, Any], log), dotted_key)
        value_text: str = flatten_text(value).lower()

        if search_field == "level":
            if value_text != keyword:
                return False
            continue

        if keyword not in value_text:
            return False

    return True


def iter_numeric_values(value: object, *, key_filter: str | None = None) -> list[float]:
    """dict/listから数値を再帰的に取り出す。"""
    numbers: list[float] = []

    if isinstance(value, dict):
        value_dict: dict[object, object] = cast(dict[object, object], value)
        for key, child_value in value_dict.items():
            child_value_obj: object = child_value
            key_text: str = str(key).lower()
            if key_filter is None or key_text == key_filter or key_text.endswith(f".{key_filter}"):
                numbers.extend(iter_numeric_values(child_value_obj))
            else:
                numbers.extend(iter_numeric_values(child_value_obj, key_filter=key_filter))
        return numbers

    if isinstance(value, (list, tuple, set)):
        children: list[object] | tuple[object, ...] | set[object] = cast(
            list[object] | tuple[object, ...] | set[object],
            value,
        )
        for child in children:
            numbers.extend(iter_numeric_values(child, key_filter=key_filter))
        return numbers

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [float(value)]

    if isinstance(value, str):
        try:
            return [float(value)]
        except ValueError:
            return []

    return numbers


def match_ignore_rule(log: LogDict, rule: IgnoreRule, tz: str | tzinfo) -> bool:
    """ignore条件に該当するか判定する。Trueなら除外。"""
    if rule.operator is None or rule.number is None:
        return rule.raw_text.lower() in build_search_blob(log, tz)

    search_area: object = log.get("context", {})
    key_filter: str | None = rule.key.lower() if rule.key else None
    numbers: list[float] = iter_numeric_values(search_area, key_filter=key_filter)

    if not numbers and rule.key is not None:
        numbers = iter_numeric_values(cast(dict[str, Any], log), key_filter=key_filter)

    compare_func: Callable[[float, float], bool] = COMPARE_FUNCS[rule.operator]
    return any(compare_func(number, rule.number) for number in numbers)


def match_search_query(log: LogDict, query: str, tz: str | tzinfo) -> bool:
    """検索テキストボックス1回分の判定を行う。"""
    query = query.strip()
    if not query:
        return True

    local_dt: datetime | None = to_local_datetime(log.get("time"), tz)
    range_parts: tuple[str, str] | None = split_range_query(query)

    start_text: str
    end_text: str

    if range_parts is not None:
        start_text, end_text = range_parts
        start_dt: datetime | None = parse_date_or_datetime(start_text, is_end=False, tz=tz)
        end_dt: datetime | None = parse_date_or_datetime(end_text, is_end=True, tz=tz)
        if local_dt is None:
            return False
        if start_dt is not None and local_dt < start_dt:
            return False
        if end_dt is not None and local_dt > end_dt:
            return False
        return True

    if is_date_query(query):
        return local_dt is not None and local_dt.strftime("%Y-%m-%d") == query

    if is_time_query(query):
        return local_dt is not None and local_dt.strftime("%H:%M:%S").startswith(query)

    if is_datetime_prefix_query(query):
        normalized: str = query.replace("T", " ")
        return local_dt is not None and local_dt.strftime("%Y-%m-%d %H:%M:%S").startswith(normalized)

    parsed: SearchQuery = parse_query(query)
    blob: str = build_search_blob(log, tz)

    if any(match_ignore_rule(log, rule, tz) for rule in parsed.ignore_rules):
        return False

    if not match_field_filters(log, parsed.field_filters):
        return False

    if any(term in blob for term in parsed.exclude_terms):
        return False

    return all(term in blob for term in parsed.include_terms)


def filter_logs(
    logs: list[LogDict],
    query: str,
    tz: str | tzinfo,
) -> list[LogDict]:
    """Viewerが既に保持しているログだけを検索条件で絞り込む。"""
    return [log for log in logs if match_search_query(log, query, tz)]
