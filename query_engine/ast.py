"""検索DSLのASTノード定義。

このモジュールはアプリ固有の型へ依存しません。各ノードは小さく保ち、
TypeScript の discriminated union へ移しやすい形にしています。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

CompareOperator: TypeAlias = Literal["<", "<=", ">", ">=", "==", "!="]


@dataclass(frozen=True, slots=True)
class EmptyNode:
    kind: Literal["empty"] = "empty"


@dataclass(frozen=True, slots=True)
class TermNode:
    term: str
    kind: Literal["term"] = "term"


@dataclass(frozen=True, slots=True)
class PhraseNode:
    phrase: str
    kind: Literal["phrase"] = "phrase"


@dataclass(frozen=True, slots=True)
class FieldNode:
    field: str
    value: str
    kind: Literal["field"] = "field"


@dataclass(frozen=True, slots=True)
class CompareNode:
    field: str
    operator: CompareOperator
    value: float
    kind: Literal["compare"] = "compare"


@dataclass(frozen=True, slots=True)
class RegexNode:
    pattern: str
    field: str | None = None
    kind: Literal["regex"] = "regex"


@dataclass(frozen=True, slots=True)
class NotNode:
    child: QueryNode
    kind: Literal["not"] = "not"


@dataclass(frozen=True, slots=True)
class AndNode:
    left: QueryNode
    right: QueryNode
    kind: Literal["and"] = "and"


@dataclass(frozen=True, slots=True)
class OrNode:
    left: QueryNode
    right: QueryNode
    kind: Literal["or"] = "or"


QueryNode: TypeAlias = (
    EmptyNode
    | TermNode
    | PhraseNode
    | FieldNode
    | CompareNode
    | RegexNode
    | NotNode
    | AndNode
    | OrNode
)
