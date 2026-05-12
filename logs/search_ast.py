# -*- coding: utf-8 -*-
"""検索テキスト用の独自ASTノード定義。"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import ClassVar

from logs.search_models import CompareOperator


@dataclass(slots=True)
class QueryNode(ast.AST):
    """Python文法ではなく、検索テキスト用に組み立てるASTの基底。"""

    _fields: ClassVar[tuple[str, ...]] = ()


@dataclass(slots=True)
class EmptyNode(QueryNode):
    """空条件ノード。"""

    _fields: ClassVar[tuple[str, ...]] = ()


@dataclass(slots=True)
class TermNode(QueryNode):
    """全文検索ノード。"""

    term: str

    _fields: ClassVar[tuple[str, ...]] = ("term",)


@dataclass(slots=True)
class FieldNode(QueryNode):
    """field:value 条件ノード。"""

    field: str
    value: str

    _fields: ClassVar[tuple[str, ...]] = ("field", "value")


@dataclass(slots=True)
class RegexNode(QueryNode):
    """正規表現検索ノード。"""

    pattern: str
    field: str | None = None

    _fields: ClassVar[tuple[str, ...]] = ("pattern", "field")


@dataclass(slots=True)
class SimilarNode(QueryNode):
    """TF-IDF/文字n-gram風の近似検索ノード。"""

    text: str
    threshold: float = 0.08

    _fields: ClassVar[tuple[str, ...]] = ("text", "threshold")


@dataclass(slots=True)
class CompareNode(QueryNode):
    """context.cpu_percent >= 20 のような比較条件ノード。"""

    field: str
    operator: CompareOperator
    value: float

    _fields: ClassVar[tuple[str, ...]] = ("field", "operator", "value")


@dataclass(slots=True)
class NotNode(QueryNode):
    """否定条件ノード。"""

    child: QueryNode

    _fields: ClassVar[tuple[str, ...]] = ("child",)


@dataclass(slots=True)
class AndNode(QueryNode):
    """AND条件ノード。"""

    left: QueryNode
    right: QueryNode

    _fields: ClassVar[tuple[str, ...]] = ("left", "right")


@dataclass(slots=True)
class OrNode(QueryNode):
    """OR条件ノード。"""

    left: QueryNode
    right: QueryNode

    _fields: ClassVar[tuple[str, ...]] = ("left", "right")
