# -*- coding: utf-8 -*-
"""検索条件で使うdataclass定義。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal, TypeAlias

from logs.log_types import LogDict

if TYPE_CHECKING:
    from logs.search_ast import QueryNode

CompareOperator: TypeAlias = Literal["<", "<=", ">", ">=", "==", "!="]
AggregateFunction: TypeAlias = Literal[
    "count",
    "max",
    "min",
    "avg",
    "ave",
    "mean",
    "median",
    "mode",
]
SortDirection: TypeAlias = Literal["asc", "desc"]


@dataclass(slots=True)
class SortSpec:
    """検索結果の並び替え条件。"""

    field: str
    direction: SortDirection = "asc"


@dataclass(slots=True)
class FieldFilter:
    """特定フィールドに対する単純な部分一致条件。"""
    field: str
    value: str


@dataclass(slots=True)
class SearchableLog:
    """検索可能なログエントリ。"""
    raw: LogDict
    blob: str


@dataclass(slots=True)
class IgnoreRule:
    """(ignore: <80) のような条件排除ルール。"""

    raw_text: str
    key: str | None = None
    operator: CompareOperator | None = None
    number: float | None = None


@dataclass(slots=True)
class AggregateQuery:
    """検索窓から実行する集計条件。"""

    function: AggregateFunction
    field: str = "*"
    where_text: str = ""
    where_query: SearchQuery | None = None
    group_by: str | None = None


@dataclass(slots=True)
class AggregateResult:
    """集計検索の計算結果。"""

    query: AggregateQuery
    value: object
    matched_count: int
    value_count: int
    message: str


def _empty_str_list() -> list[str]:
    return []


def _empty_field_filter_list() -> list[FieldFilter]:
    return []


def _empty_ignore_rule_list() -> list[IgnoreRule]:
    return []


@dataclass(slots=True)
class SearchQuery:
    """ログViewer用の検索条件。"""

    raw_text: str = ""
    start: datetime | None = None
    end: datetime | None = None
    ast_root: QueryNode | None = None
    aggregate: AggregateQuery | None = None
    sort: SortSpec | None = None
    top: int | None = None

    include_terms: list[str] = field(
        default_factory=_empty_str_list,
    )

    exclude_terms: list[str] = field(
        default_factory=_empty_str_list,
    )

    field_filters: list[FieldFilter] = field(
        default_factory=_empty_field_filter_list,
    )

    ignore_rules: list[IgnoreRule] = field(
        default_factory=_empty_ignore_rule_list,
    )
