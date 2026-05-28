# -*- coding: utf-8 -*-
"""検索ASTをLogDictへ適用する判定モジュール。"""
from __future__ import annotations

import operator
import re
import statistics
from collections import Counter
from datetime import datetime, timezone, tzinfo
from typing import Any, Callable, cast

from logs.log_types import LogDict
from logs.search_ast import (AndNode, CompareNode, EmptyNode, FieldNode,
                             NotNode, OrNode, QueryNode, RegexNode,
                             SimilarNode, TermNode)
from logs.search_models import (AggregateQuery, AggregateResult,
                                CompareOperator, IgnoreRule, SearchQuery,
                                SortSpec)
from logs.search_similarity import (DEFAULT_SIMILARITY_THRESHOLD,
                                    similarity_score)
from logs.search_text_analysis import (is_time_query, parse_query,
                                       resolve_timezone)
from logs.traceql_bridge import match_traceql_search, should_use_legacy_search

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

COMPARE_FUNCS: dict[CompareOperator, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}

_MISSING: object = object()


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
    value: object = _get_nested_value(data, dotted_key, default="")
    return value


def _get_nested_value(data: dict[str, Any], dotted_key: str, *, default: object) -> object:
    """where.function のようなドット区切りキーで値を取得する。"""
    current: object = data

    for key in dotted_key.split("."):
        if not isinstance(current, dict):
            return default
        current_dict: dict[str, object] = cast(dict[str, object], current)
        if key not in current_dict:
            return default
        current = current_dict[key]

    return current


def build_search_blob(log: LogDict, tz: str | tzinfo) -> str:
    """全文検索用の文字列を作る。"""
    blob: str = flatten_text(log).lower()
    local_dt: datetime | None = to_local_datetime(log.get("time"), tz)
    if local_dt is not None:
        blob += " " + local_dt.strftime("%Y-%m-%d %H:%M:%S").lower()
        blob += " " + local_dt.isoformat(timespec="seconds").lower()
    return blob


def _resolve_search_field(field: str) -> str:
    """検索用field名をLogDict上のdotted keyへ解決する。"""
    normalized: str = field.lower().strip()
    return FIELD_MAP.get(normalized, normalized)


def _iter_scalar_values(value: object) -> list[object]:
    """集計用にdict/listをスカラー値へほどく。"""
    if value in ("", None):
        return []

    if isinstance(value, dict):
        values: list[object] = []
        value_dict: dict[object, object] = cast(dict[object, object], value)
        for child_value in value_dict.values():
            values.extend(_iter_scalar_values(child_value))
        return values

    if isinstance(value, (list, tuple, set)):
        values = []
        children: list[object] | tuple[object, ...] | set[object] = cast(
            list[object] | tuple[object, ...] | set[object],
            value,
        )
        for child in children:
            values.extend(_iter_scalar_values(child))
        return values

    return [value]


def get_aggregate_values(log: LogDict, aggregate: AggregateQuery) -> list[object]:
    """集計対象フィールドの値を取り出す。"""
    if aggregate.field == "*":
        return [log]

    dotted_key: str = _resolve_search_field(aggregate.field)
    value: object = _get_nested_value(cast(dict[str, Any], log), dotted_key, default=_MISSING)
    if value is _MISSING:
        return []

    return _iter_scalar_values(value)


def get_numeric_aggregate_values(log: LogDict, aggregate: AggregateQuery) -> list[float]:
    """数値集計対象フィールドの値を取り出す。"""
    values: list[float] = []
    for value in get_aggregate_values(log, aggregate):
        values.extend(iter_numeric_values(value))
    return values


def _match_field_node(log: LogDict, node: FieldNode) -> bool:
    if not node.field or not node.value:
        return False

    search_field: str = node.field.lower()
    dotted_key: str = _resolve_search_field(search_field)
    value: object = get_nested_value(cast(dict[str, Any], log), dotted_key)
    value_text: str = flatten_text(value).lower()
    keyword: str = node.value.lower()

    if search_field == "level":
        return value_text == keyword

    return keyword in value_text


def _match_regex_node(log: LogDict, node: RegexNode, blob: str) -> bool:
    try:
        pattern: re.Pattern[str] = re.compile(node.pattern, flags=re.IGNORECASE)
    except re.error:
        return False

    if node.field is None:
        return pattern.search(blob) is not None

    dotted_key: str = _resolve_search_field(node.field)
    value: object = get_nested_value(cast(dict[str, Any], log), dotted_key)
    return pattern.search(flatten_text(value)) is not None


def _match_similar_node(node: SimilarNode, blob: str) -> bool:
    threshold: float = node.threshold or DEFAULT_SIMILARITY_THRESHOLD
    return similarity_score(node.text, blob) >= threshold


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


def _match_compare_node(log: LogDict, node: CompareNode) -> bool:
    dotted_key: str = _resolve_search_field(node.field)
    value: object = _get_nested_value(cast(dict[str, Any], log), dotted_key, default=_MISSING)
    numbers: list[float] = [] if value is _MISSING else iter_numeric_values(value)

    if value is _MISSING and "." in node.field:
        return False

    if not numbers:
        key_filter: str = node.field.rsplit(".", 1)[-1].lower()
        numbers = iter_numeric_values(cast(dict[str, Any], log), key_filter=key_filter)

    compare_func: Callable[[float, float], bool] = COMPARE_FUNCS[node.operator]
    return any(compare_func(number, node.value) for number in numbers)


def match_ignore_rule(log: LogDict, rule: IgnoreRule, tz: str | tzinfo) -> bool:
    """ignore条件に該当するか判定する。Trueなら除外。"""
    if rule.operator is None or rule.number is None:
        return rule.raw_text.lower() in build_search_blob(log, tz)

    search_area: object = log.get("context", {})
    key_filter: str | None = rule.key.lower().rsplit(".", 1)[-1] if rule.key else None
    numbers: list[float] = iter_numeric_values(search_area, key_filter=key_filter)

    if not numbers and rule.key is not None:
        numbers = iter_numeric_values(cast(dict[str, Any], log), key_filter=key_filter)

    compare_func: Callable[[float, float], bool] = COMPARE_FUNCS[rule.operator]
    return any(compare_func(number, rule.number) for number in numbers)


def match_query_node(log: LogDict, node: QueryNode, blob: str) -> bool:
    """検索AST 1ノードを判定する。"""
    if isinstance(node, EmptyNode):
        return True

    if isinstance(node, TermNode):
        return node.term.lower() in blob

    if isinstance(node, FieldNode):
        return _match_field_node(log, node)

    if isinstance(node, RegexNode):
        return _match_regex_node(log, node, blob)

    if isinstance(node, SimilarNode):
        return _match_similar_node(node, blob)

    if isinstance(node, CompareNode):
        return _match_compare_node(log, node)

    if isinstance(node, NotNode):
        return not match_query_node(log, node.child, blob)

    if isinstance(node, AndNode):
        return match_query_node(log, node.left, blob) and match_query_node(log, node.right, blob)

    if isinstance(node, OrNode):
        return match_query_node(log, node.left, blob) or match_query_node(log, node.right, blob)

    return False


def _find_similar_node(node: QueryNode | None) -> SimilarNode | None:
    if node is None:
        return None
    if isinstance(node, SimilarNode):
        return node
    if isinstance(node, NotNode):
        return None
    if isinstance(node, AndNode | OrNode):
        return _find_similar_node(node.left) or _find_similar_node(node.right)
    return None


def _match_query_dataclass(log: LogDict, query: SearchQuery, tz: str | tzinfo) -> bool:
    local_dt: datetime | None = to_local_datetime(log.get("time"), tz)

    if query.start is not None or query.end is not None:
        if local_dt is None:
            return False
        if query.start is not None and local_dt < query.start:
            return False
        if query.end is not None and local_dt > query.end:
            return False
        if query.ast_root is None:
            return True

    if is_time_query(query.raw_text):
        return local_dt is not None and local_dt.strftime("%H:%M:%S").startswith(query.raw_text)

    if any(match_ignore_rule(log, rule, tz) for rule in query.ignore_rules):
        return False

    if query.ast_root is None:
        return True

    return match_query_node(log, query.ast_root, build_search_blob(log, tz))


def match_aggregate_log(log: LogDict, aggregate: AggregateQuery, tz: str | tzinfo) -> bool:
    """集計対象として表示すべきログか判定する。"""
    if aggregate.where_query is not None and not _match_query_dataclass(log, aggregate.where_query, tz):
        return False

    if aggregate.function == "count" and aggregate.field == "*":
        return True

    if aggregate.function in {"max", "min", "avg", "ave", "mean", "median"}:
        return bool(get_numeric_aggregate_values(log, aggregate))

    return bool(get_aggregate_values(log, aggregate))


def filter_aggregate_logs(
    logs: list[LogDict],
    aggregate: AggregateQuery,
    tz: str | tzinfo,
) -> list[LogDict]:
    """集計対象になったログだけを返す。"""
    return [log for log in logs if match_aggregate_log(log, aggregate, tz)]


def _format_aggregate_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _calculate_aggregate_value(values: list[object], function: str) -> tuple[object, int]:
    """集計値と値件数を計算する。"""
    if function == "count":
        return len(values), len(values)

    if function in {"max", "min", "avg", "ave", "mean", "median"}:
        numbers: list[float] = []
        for value in values:
            numbers.extend(iter_numeric_values(value))

        if not numbers:
            return None, 0
        if function == "max":
            return max(numbers), len(numbers)
        if function == "min":
            return min(numbers), len(numbers)
        if function == "median":
            return statistics.median(numbers), len(numbers)
        return statistics.mean(numbers), len(numbers)

    text_values: list[str] = [str(value) for value in values]
    if not text_values:
        return None, 0

    counts: Counter[str] = Counter(text_values)
    top_count: int = counts.most_common(1)[0][1]
    modes: list[str] = sorted(value for value, count in counts.items() if count == top_count)
    return ", ".join(modes), len(text_values)


def _run_group_aggregate_query(
    matched_logs: list[LogDict],
    aggregate: AggregateQuery,
    tz: str | tzinfo,
) -> AggregateResult:
    """group by付き集計検索を実行する。"""
    group_field: str = aggregate.group_by or ""
    grouped_logs: dict[str, list[LogDict]] = {}

    for log in matched_logs:
        group_values: list[object] = _iter_scalar_values(
            get_nested_value(cast(dict[str, Any], log), _resolve_search_field(group_field))
        )
        if not group_values:
            group_values = ["<missing>"]
        for group_value in group_values:
            grouped_logs.setdefault(str(group_value), []).append(log)

    parts: list[str] = []
    total_value_count = 0
    for group_value in sorted(grouped_logs):
        logs_for_group: list[LogDict] = grouped_logs[group_value]
        values: list[object] = []
        if aggregate.function == "count" and aggregate.field == "*":
            values = list(logs_for_group)
        else:
            for log in logs_for_group:
                values.extend(get_aggregate_values(log, aggregate))
        value, value_count = _calculate_aggregate_value(values, aggregate.function)
        total_value_count += value_count
        parts.append(f"{group_value}:{_format_aggregate_value(value)}")

    message = (
        f"group by {group_field} {aggregate.function} {aggregate.field} -> "
        f"{'; '.join(parts)} "
        f"(groups={len(grouped_logs)}, logs={len(matched_logs)}, values={total_value_count})"
    )
    return AggregateResult(
        query=aggregate,
        value=dict(grouped_logs),
        matched_count=len(matched_logs),
        value_count=total_value_count,
        message=message,
    )


def run_aggregate_query(
    logs: list[LogDict],
    aggregate: AggregateQuery,
    tz: str | tzinfo,
) -> AggregateResult:
    """集計検索を実行する。"""
    matched_logs: list[LogDict] = filter_aggregate_logs(logs, aggregate, tz)
    function: str = aggregate.function
    field: str = aggregate.field

    if aggregate.group_by is not None:
        return _run_group_aggregate_query(matched_logs, aggregate, tz)

    if function == "count":
        if field == "*":
            value: object = len(matched_logs)
            value_count: int = len(matched_logs)
        else:
            values: list[object] = []
            for log in matched_logs:
                values.extend(get_aggregate_values(log, aggregate))
            value = len(values)
            value_count = len(values)

        message = (
            f"{function} {field} = {_format_aggregate_value(value)} "
            f"(logs={len(matched_logs)}, values={value_count})"
        )
        return AggregateResult(
            query=aggregate,
            value=value,
            matched_count=len(matched_logs),
            value_count=value_count,
            message=message,
        )

    if function in {"max", "min", "avg", "ave", "mean", "median"}:
        numbers: list[float] = []
        for log in matched_logs:
            numbers.extend(get_numeric_aggregate_values(log, aggregate))

        if not numbers:
            value = None
        elif function == "max":
            value = max(numbers)
        elif function == "min":
            value = min(numbers)
        elif function == "median":
            value = statistics.median(numbers)
        else:
            value = statistics.mean(numbers)

        message = (
            f"{function} {field} = {_format_aggregate_value(value)} "
            f"(logs={len(matched_logs)}, values={len(numbers)})"
        )
        return AggregateResult(
            query=aggregate,
            value=value,
            matched_count=len(matched_logs),
            value_count=len(numbers),
            message=message,
        )

    values: list[str] = []
    for log in matched_logs:
        values.extend(str(value) for value in get_aggregate_values(log, aggregate))

    if not values:
        value = None
    else:
        counts: Counter[str] = Counter(values)
        top_count: int = counts.most_common(1)[0][1]
        modes: list[str] = sorted(value for value, count in counts.items() if count == top_count)
        value = ", ".join(modes)

    message = (
        f"{function} {field} = {_format_aggregate_value(value)} "
        f"(logs={len(matched_logs)}, values={len(values)})"
    )
    return AggregateResult(
        query=aggregate,
        value=value,
        matched_count=len(matched_logs),
        value_count=len(values),
        message=message,
    )


def match_search_query(log: LogDict, query: str | SearchQuery, tz: str | tzinfo) -> bool:
    """検索テキストボックス1回分の判定を行う。"""
    if isinstance(query, str) and not should_use_legacy_search(query):
        return match_traceql_search(log, query, tz)
    parsed: SearchQuery = query if isinstance(query, SearchQuery) else parse_query(query, tz)
    if not parsed.raw_text.strip():
        return True
    if parsed.aggregate is not None:
        return match_aggregate_log(log, parsed.aggregate, tz)
    return _match_query_dataclass(log, parsed, tz)


def filter_logs(
    logs: list[LogDict],
    query: str | SearchQuery,
    tz: str | tzinfo,
) -> list[LogDict]:
    """Viewerが既に保持しているログだけを検索条件で絞り込む。"""
    parsed: SearchQuery = query if isinstance(query, SearchQuery) else parse_query(query, tz)
    return [log for log in logs if match_search_query(log, parsed, tz)]


def _sort_value(
    log: LogDict,
    sort: SortSpec,
    tz: str | tzinfo,
) -> tuple[int, int, float, str]:
    field: str = sort.field.lower()
    if field == "time":
        local_dt: datetime | None = to_local_datetime(log.get("time"), tz)
        return (0, 0, local_dt.timestamp(), "") if local_dt is not None else (1, 0, 0.0, "")

    value: object = _get_nested_value(
        cast(dict[str, Any], log),
        _resolve_search_field(field),
        default=_MISSING,
    )
    if value is _MISSING:
        return 1, 0, 0.0, ""

    numeric_values: list[float] = iter_numeric_values(value)
    if numeric_values:
        return 0, 0, numeric_values[0], ""

    return 0, 1, 0.0, flatten_text(value).lower()


def apply_result_modifiers(
    logs: list[LogDict],
    query: SearchQuery,
    tz: str | tzinfo,
) -> list[LogDict]:
    """sort/top を検索結果へ適用する。"""
    result: list[LogDict] = list(logs)
    if query.sort is not None:
        sort_spec: SortSpec = query.sort
        present_logs: list[LogDict] = [
            log for log in result if _sort_value(log, sort_spec, tz)[0] == 0
        ]
        missing_logs: list[LogDict] = [
            log for log in result if _sort_value(log, sort_spec, tz)[0] != 0
        ]
        present_logs.sort(
            key=lambda log: _sort_value(log, sort_spec, tz),
            reverse=sort_spec.direction == "desc",
        )
        result = present_logs + missing_logs
    else:
        similar_node: SimilarNode | None = _find_similar_node(query.ast_root)
        if similar_node is not None:
            result.sort(
                key=lambda log: similarity_score(
                    similar_node.text,
                    build_search_blob(log, tz),
                ),
                reverse=True,
            )

    if query.top is not None:
        return result[:query.top]

    return result
