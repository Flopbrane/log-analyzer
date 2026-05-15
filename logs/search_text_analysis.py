# -*- coding: utf-8 -*-
"""LogViewerの検索テキスト解析専用モジュール。"""
#########################
# Author: F.Kurokawa
# Description:
# LogViewerの検索テキストボックスに入力された文字列を解析する。
# ログの読み込みは行わず、Viewerが保持しているLogDictだけを判定する。
#########################
from __future__ import annotations

import re
import shlex
from datetime import datetime, timedelta, timezone, tzinfo
from typing import cast
from zoneinfo import ZoneInfo

from logs.search_ast import (
    AndNode,
    CompareNode,
    EmptyNode,
    FieldNode,
    NotNode,
    OrNode,
    QueryNode,
    RegexNode,
    SimilarNode,
    TermNode,
)
from logs.search_models import (
    AggregateFunction,
    AggregateQuery,
    CompareOperator,
    FieldFilter,
    IgnoreRule,
    SearchQuery,
    SortDirection,
    SortSpec,
)

COMPARE_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<field>[A-Za-z_][\w.]*)"
    r"(?P<op><=|>=|==|!=|<|>)"
    r"(?P<num>-?\d+(?:\.\d+)?)$"
)

OP_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<op><=|>=|==|!=|<|>)"
    r"(?P<num>-?\d+(?:\.\d+)?)$"
)

NUMBER_PATTERN: re.Pattern[str] = re.compile(r"^-?\d+(?:\.\d+)?$")
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

AGGREGATE_FUNCTION_ALIASES: dict[str, AggregateFunction] = {
    "count": "count",
    "max": "max",
    "min": "min",
    "avg": "avg",
    "ave": "ave",
    "mean": "mean",
    "median": "median",
    "mode": "mode",
}

KNOWN_FIELD_NAMES: set[str] = {
    "level",
    "message",
    "msg",
    "function",
    "func",
    "file",
    "trace",
    "trace_id",
    "output",
    "context",
}


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
    start_text: str
    end_text: str
    
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


def tokenize_query(query_text: str) -> list[str]:
    """一般テキスト検索用のトークン列へ分解する。"""
    lexer = shlex.shlex(query_text, posix=True, punctuation_chars="()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return [token for token in lexer if token]


class SearchQueryParser:
    """検索テキストを独自ASTへ変換する小さな再帰下降Parser。"""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens: list[str] = tokens
        self.index = 0

    def parse(self) -> QueryNode | None:
        if not self.tokens:
            return None
        node: QueryNode | None = self._parse_or()
        if node is None:
            return None
        return node

    def _current(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _advance(self) -> str | None:
        token: str | None = self._current()
        if token is not None:
            self.index += 1
        return token

    def _parse_or(self) -> QueryNode | None:
        left: QueryNode | None = self._parse_and()
        if left is None:
            return None

        while self._current() is not None and self._current_upper() == "OR":
            self._advance()
            right: QueryNode | None = self._parse_and()
            if right is None:
                right = EmptyNode()
            left = OrNode(left=left, right=right)

        return left

    def _parse_and(self) -> QueryNode | None:
        nodes: list[QueryNode] = []

        while self._current() is not None:
            current: str = cast(str, self._current())
            if current == ")" or current.upper() == "OR":
                break
            if current.upper() == "AND":
                self._advance()
                continue

            node: QueryNode | None = self._parse_factor()
            if node is not None:
                nodes.append(node)

        if not nodes:
            return None

        result: QueryNode = nodes[0]
        for node in nodes[1:]:
            result = AndNode(left=result, right=node)
        return result

    def _parse_factor(self) -> QueryNode | None:
        token: str | None = self._current()
        if token is None:
            return None

        if token == "(":
            self._advance()
            node: QueryNode | None = self._parse_or()
            if self._current() == ")":
                self._advance()
            return node

        if token.startswith("-") and len(token) > 1:
            self._advance()
            return NotNode(child=self._atom_from_token(token[1:]))

        if token == "-":
            self._advance()
            child: QueryNode | None = self._parse_factor()
            return NotNode(child=child or EmptyNode())

        return self._parse_atom()

    def _parse_atom(self) -> QueryNode | None:
        token: str | None = self._advance()
        if token is None:
            return None

        if token.lower() == "regex":
            return self._parse_regex_node()

        if token.lower() == "similar":
            return self._parse_similar_node()

        combined_match: re.Match[str] | None = COMPARE_PATTERN.fullmatch(token)
        if combined_match is not None:
            return CompareNode(
                field=combined_match.group("field").lower(),
                operator=cast(CompareOperator, combined_match.group("op")),
                value=float(combined_match.group("num")),
            )

        if self._looks_like_field_name(token):
            compare_node: CompareNode | None = self._consume_compare_after_field(token)
            if compare_node is not None:
                return compare_node

        return self._atom_from_token(token)

    def _parse_regex_node(self) -> QueryNode:
        first: str | None = self._advance()
        if first is None:
            return TermNode(term="regex")

        second: str | None = self._current()
        if second is not None and self._looks_like_field_name(first):
            self._advance()
            return RegexNode(field=first.lower(), pattern=second)

        return RegexNode(field=None, pattern=first)

    def _parse_similar_node(self) -> QueryNode:
        text: str | None = self._advance()
        if text is None:
            return TermNode(term="similar")

        threshold: float = 0.08
        next_token: str | None = self._current()
        if next_token is not None and NUMBER_PATTERN.fullmatch(next_token):
            self._advance()
            threshold = float(next_token)

        return SimilarNode(text=text, threshold=threshold)

    def _consume_compare_after_field(self, field: str) -> CompareNode | None:
        next_token: str | None = self._current()
        if next_token is None:
            return None

        op_number_match: re.Match[str] | None = OP_NUMBER_PATTERN.fullmatch(next_token)
        if op_number_match is not None:
            self._advance()
            return CompareNode(
                field=field.lower(),
                operator=cast(CompareOperator, op_number_match.group("op")),
                value=float(op_number_match.group("num")),
            )

        if next_token in {"<", "<=", ">", ">=", "==", "!="}:
            operator_token: str = cast(str, self._advance())
            number_token: str | None = self._current()
            if number_token is not None and NUMBER_PATTERN.fullmatch(number_token):
                self._advance()
                return CompareNode(
                    field=field.lower(),
                    operator=cast(CompareOperator, operator_token),
                    value=float(number_token),
                )

        return None

    def _atom_from_token(self, token: str) -> QueryNode:
        field: str | None = None
        value: str | None = None
        if ":" in token:
            field, value = token.split(":", 1)
            normalized_field: str = field.strip().lower()
            if (
                not normalized_field
                or normalized_field in KNOWN_FIELD_NAMES
                or "." in normalized_field
            ):
                return FieldNode(field=normalized_field, value=value.strip().lower())

        return TermNode(term=token.lower())

    def _looks_like_field_name(self, token: str) -> bool:
        return re.fullmatch(r"[A-Za-z_][\w.]*", token) is not None

    def _current_upper(self) -> str | None:
        token: str | None = self._current()
        return token.upper() if token is not None else None

# ==========================
# タイムゾーン関連のユーティリティ
# ==========================
EXCLUDED_PREFIXES: tuple[str, ...] = ()

def _collect_legacy_fields(node: QueryNode, query: SearchQuery) -> None:
    """旧API互換用にASTからinclude/exclude/field_filtersも埋める。"""
    if isinstance(node, TermNode):
        query.include_terms.append(node.term)
        return

    if isinstance(node, FieldNode):
        query.field_filters.append(FieldFilter(field=node.field, value=node.value))
        return

    if isinstance(node, RegexNode):
        query.include_terms.append(f"regex:{node.pattern}")
        return

    if isinstance(node, NotNode):
        if isinstance(node.child, TermNode):
            query.exclude_terms.append(node.child.term)
        return

    if isinstance(node, (AndNode, OrNode)):
        _collect_legacy_fields(node.left, query)
        _collect_legacy_fields(node.right, query)


def _extract_ignore_rules(raw_text: str) -> tuple[str, list[IgnoreRule]]:
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
    return query_text, ignore_rules


def _parse_datetime_bounds(raw_text: str, tz: str | tzinfo) -> tuple[datetime | None, datetime | None]:
    range_parts: tuple[str, str] | None = split_range_query(raw_text)

    if range_parts is not None:
        start_text, end_text = range_parts
        return (
            parse_date_or_datetime(start_text, is_end=False, tz=tz),
            parse_date_or_datetime(end_text, is_end=True, tz=tz),
        )

    if is_date_query(raw_text) or is_datetime_prefix_query(raw_text):
        return (
            parse_date_or_datetime(raw_text, is_end=False, tz=tz),
            parse_date_or_datetime(raw_text, is_end=True, tz=tz),
        )

    return None, None


def _extract_result_modifiers(raw_text: str) -> tuple[str, SortSpec | None, int | None]:
    """sort/top 指定を検索本文から分離する。"""
    stripped: str = raw_text.strip()
    top_match: re.Match[str] | None = TOP_PATTERN.fullmatch(stripped)
    if top_match is not None:
        direction: SortDirection = cast(
            SortDirection,
            (top_match.group("direction") or "desc").lower(),
        )
        return (
            (top_match.group("body") or "").strip(),
            SortSpec(
                field=top_match.group("field").lower(),
                direction=direction,
            ),
            int(top_match.group("limit")),
        )

    sort_match: re.Match[str] | None = SORT_PATTERN.fullmatch(stripped)
    if sort_match is not None:
        direction = cast(
            SortDirection,
            (sort_match.group("direction") or "asc").lower(),
        )
        return (
            (sort_match.group("body") or "").strip(),
            SortSpec(
                field=sort_match.group("field").lower(),
                direction=direction,
            ),
            None,
        )

    return stripped, None, None


def parse_aggregate_query(
    raw_text: str,
    tz: str | tzinfo = "Asia/Tokyo",
) -> AggregateQuery | None:
    """count/max/min/avg/median/mode などの集計検索を解析する。"""
    body: str = raw_text.strip()
    if not body:
        return None

    tokens: list[str] = tokenize_query(body)
    if not tokens:
        return None

    if len(tokens) >= 5 and tokens[0].lower() == "group" and tokens[1].lower() == "by":
        group_by: str = tokens[2].lower()
        function: AggregateFunction | None = AGGREGATE_FUNCTION_ALIASES.get(tokens[3].lower())
        if function is None:
            return None

        rest: str = body.split(tokens[3], 1)[1].strip()
        where_text: str = ""
        where_match: re.Match[str] | None = re.search(r"\s+where\s+", rest, flags=re.IGNORECASE)
        if where_match is not None:
            where_text = rest[where_match.end():].strip()
            rest = rest[:where_match.start()].strip()

        field: str = rest or "*"
        if function != "count" and field == "*":
            return None

        where_query: SearchQuery | None = (
            parse_query(where_text, tz, allow_aggregate=False)
            if where_text
            else None
        )

        return AggregateQuery(
            function=function,
            field=field.lower(),
            where_text=where_text,
            where_query=where_query,
            group_by=group_by,
        )

    function: AggregateFunction | None = AGGREGATE_FUNCTION_ALIASES.get(tokens[0].lower())
    if function is None:
        return None

    rest: str = body[len(tokens[0]):].strip()
    where_text: str = ""
    where_match: re.Match[str] | None = re.search(r"\s+where\s+", rest, flags=re.IGNORECASE)
    if where_match is not None:
        where_text = rest[where_match.end():].strip()
        rest = rest[:where_match.start()].strip()

    field: str = rest or "*"
    if function != "count" and field == "*":
        return None

    where_query: SearchQuery | None = (
        parse_query(where_text, tz, allow_aggregate=False)
        if where_text
        else None
    )

    return AggregateQuery(
        function=function,
        field=field.lower(),
        where_text=where_text,
        where_query=where_query,
    )


def parse_query(
    raw_text: str,
    tz: str | tzinfo = "Asia/Tokyo",
    *,
    allow_aggregate: bool = True,
) -> SearchQuery:
    """検索文字列をSearchQuery dataclassに変換する。"""
    raw_text = raw_text.strip()
    query = SearchQuery(raw_text=raw_text)
    if not raw_text:
        return query

    query_text_for_parse, sort_spec, top_limit = _extract_result_modifiers(raw_text)
    query.sort = sort_spec
    query.top = top_limit

    if allow_aggregate:
        query.aggregate = parse_aggregate_query(query_text_for_parse, tz)
        if query.aggregate is not None:
            return query

    query.start, query.end = _parse_datetime_bounds(query_text_for_parse, tz)
    if query.start is not None or query.end is not None:
        return query

    query_text, query.ignore_rules = _extract_ignore_rules(query_text_for_parse)
    tokens: list[str] = tokenize_query(query_text)
    query.ast_root = SearchQueryParser(tokens).parse()
    if query.ast_root is not None:
        _collect_legacy_fields(query.ast_root, query)
    return query
