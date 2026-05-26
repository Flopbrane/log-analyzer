"""Loggerの検索窓からTraceQL検索コアを使うための橋渡し。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any, Iterable, Mapping, cast

from zoneinfo import ZoneInfo

from logs.log_types import LogDict

# TRACEQL_ROOT = Path(__file__).resolve().parents[2]
# if str(TRACEQL_ROOT) not in sys.path:
#     sys.path.insert(0, str(TRACEQL_ROOT))
from query_engine.evaluators.memory import match_query  # noqa: E402
from query_engine.models import Document  # noqa: E402
from query_engine.parser import QuerySyntaxError  # noqa: E402

SORT_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<body>.*?)"
    r"(?:\s+)?sort\s+by\s+"
    r"(?P<field>[A-Za-z_][\w.]*|time|level|message)"
    r"(?:\s+(?P<direction>asc|desc))?\s*$",
    flags=re.IGNORECASE,
)
TOP_PATTERN: re.Pattern[str] = re.compile(
    r"^top\s+"
    r"(?P<limit>\d+)\s+by\s+"
    r"(?P<field>[A-Za-z_][\w.]*|time|level|message)"
    r"(?:\s+(?P<direction>asc|desc))?"
    r"(?:\s+where\s+(?P<body>.+))?\s*$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class TraceQLLogResult:
    """TraceQL解析後にViewerへ返すための境界データ。"""

    index: int
    matched: bool
    log: LogDict
    document: Document


def match_traceql_search(log: LogDict, raw_query: str, tz: str | tzinfo) -> bool:
    """Loggerの1行をTraceQLのメモリ検索で判定する。"""
    query: str = _strip_result_modifiers(raw_query).strip()
    if not query:
        return True
    try:
        return match_query(query, log_to_traceql_document(log, tz))
    except QuerySyntaxError:
        return False


def analyze_logs_for_viewer(
    logs: Iterable[LogDict],
    raw_query: str,
    tz: str | tzinfo,
) -> list[TraceQLLogResult]:
    """Loggerのログ列をTraceQLで解析し、Viewerが扱いやすい結果へ戻す。

    logs層からTraceQLへ渡す入口はこのbridgeに限定する。
    呼び出し側はquery_engineのDocumentやparserを直接importしない。
    """
    query: str = _strip_result_modifiers(raw_query).strip()
    if not query:
        return [
            TraceQLLogResult(
                index=index,
                matched=True,
                log=log,
                document=log_to_traceql_document(log, tz),
            )
            for index, log in enumerate(logs)
        ]

    results: list[TraceQLLogResult] = []
    for index, log in enumerate(logs):
        document: Document = log_to_traceql_document(log, tz)
        try:
            matched = match_query(query, document)
        except QuerySyntaxError:
            matched = False
        results.append(
            TraceQLLogResult(
                index=index,
                matched=matched,
                log=log,
                document=document,
            )
        )
    return results


def filter_logs_for_viewer(
    logs: Iterable[LogDict],
    raw_query: str,
    tz: str | tzinfo,
) -> list[LogDict]:
    """TraceQL解析結果からViewer表示用のLogDictだけを返す。"""
    return [
        result.log
        for result in analyze_logs_for_viewer(logs, raw_query, tz)
        if result.matched
    ]


def log_to_traceql_document(log: LogDict, tz: str | tzinfo) -> Document:
    """LoggerのLogDictをTraceQLが扱いやすいDocumentへ変換する。"""
    where: Mapping[str, Any] = cast(Mapping[str, Any], log.get("where", {}))
    what: Mapping[str, Any] = cast(Mapping[str, Any], log.get("what", {}))
    context: Mapping[str, Any] = cast(Mapping[str, Any], log.get("context", {}))
    normalized_context: dict[str, Any] = _unwrap_logger_values(context)
    message: str = str(what.get("message", ""))
    local_dt: datetime | None = _to_local_datetime(log.get("time"), tz)

    document: dict[str, Any] = {
        "level": log.get("level", ""),
        "time": log.get("time", ""),
        "trace_id": log.get("trace_id", ""),
        "trace": log.get("trace_id", ""),
        "output": log.get("output", ""),
        "where": dict(where),
        "what": dict(what),
        "context": normalized_context,
        "raw_context": dict(context),
        "message": message,
        "msg": message,
        "function": where.get("function", ""),
        "func": where.get("function", ""),
        "file": where.get("file", ""),
        "module": where.get("module", ""),
        "line": where.get("line", ""),
    }
    if local_dt is not None:
        document["local_time"] = local_dt.isoformat(timespec="seconds")
        document["local_date"] = local_dt.strftime("%Y-%m-%d")
        document["local_clock"] = local_dt.strftime("%H:%M:%S")
        document["date"] = document["local_date"]

    return document


def should_use_legacy_search(raw_query: str) -> bool:
    """TraceQLへ渡さず、Logger旧検索に任せる構文を判定する。"""
    query: str = _strip_result_modifiers(raw_query).strip()
    if not query:
        return False
    lower: str = query.lower()
    if "(ignore:" in lower:
        return True
    if lower.startswith(("regex ", "similar ", "count ", "max ", "min ", "avg ", "ave ", "mean ", "median ", "mode ")):
        return True
    if lower.startswith("group by "):
        return True
    if ".." in query or " - " in query:
        return True
    return False


def _strip_result_modifiers(raw_query: str) -> str:
    stripped: str = raw_query.strip()
    top_match: re.Match[str] | None = TOP_PATTERN.fullmatch(stripped)
    if top_match is not None:
        return (top_match.group("body") or "").strip()
    sort_match: re.Match[str] | None = SORT_PATTERN.fullmatch(stripped)
    if sort_match is not None:
        return (sort_match.group("body") or "").strip()
    return stripped


def _to_local_datetime(raw_time: object, tz: str | tzinfo) -> datetime | None:
    if not isinstance(raw_time, str):
        return None
    try:
        dt: datetime = datetime.fromisoformat(raw_time)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_resolve_timezone(tz))


def _resolve_timezone(tz: str | tzinfo) -> tzinfo:
    if isinstance(tz, tzinfo):
        return tz
    try:
        return ZoneInfo(tz)
    except Exception:
        if tz == "Asia/Tokyo":
            return timezone(timedelta(hours=9))
        return timezone.utc


def _unwrap_logger_values(value: object) -> Any:
    """Loggerの {"type": ..., "value": ...} 形式を検索向けの素直な値へ戻す。"""
    if isinstance(value, Mapping):
        mapping: Mapping[str, object] = cast(Mapping[str, object], value)
        if set(mapping.keys()) == {"type", "value"}:
            return _unwrap_logger_values(mapping["value"])
        return {str(key): _unwrap_logger_values(child) for key, child in mapping.items()}
    if isinstance(value, list):
        list_value: list[object] = cast(list[object], value)
        return [_unwrap_logger_values(child) for child in list_value]
    if isinstance(value, tuple):
        tuple_value: tuple[object, ...] = cast(tuple[object, ...], value)
        return tuple(_unwrap_logger_values(child) for child in tuple_value)
    return value
