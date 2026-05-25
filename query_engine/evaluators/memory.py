"""dict形式の文書を直接評価するメモリ内評価器。"""
from __future__ import annotations

import operator
import re
from typing import Any, Callable, Iterable

from query_engine.ast import (
    AndNode,
    CompareNode,
    EmptyNode,
    FieldNode,
    NotNode,
    PhraseNode,
    QueryNode,
    RegexNode,
    TermNode,
)
from query_engine.models import Document, SearchQuery, SearchResult
from query_engine.parser import parse_query
from query_engine.utils import flatten_text, get_path

COMPARE_FUNCS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def match_query(query: str | SearchQuery | QueryNode, document: Document) -> bool:
    """検索文字列またはASTを、1件の文書へ適用する。"""
    return match_node(_to_node(query), document)


def search(query: str | SearchQuery | QueryNode, documents: Iterable[Document]) -> list[SearchResult]:
    """文書列から条件に一致する文書を返す。"""
    node: QueryNode = _to_node(query)
    return [SearchResult(document=document) for document in documents if match_node(node, document)]


def match_node(node: QueryNode, document: Document) -> bool:
    """ASTノードをdict形式の文書へ適用する。"""
    if isinstance(node, EmptyNode):
        return True
    if isinstance(node, TermNode):
        return _contains(flatten_text(document), node.term)
    if isinstance(node, PhraseNode):
        return _contains(flatten_text(document), node.phrase)
    if isinstance(node, FieldNode):
        field_value: Any = get_path(document, node.field)
        return field_value is not None and _contains(flatten_text(field_value), node.value)
    if isinstance(node, CompareNode):
        value: float | None = _to_float(get_path(document, node.field))
        return value is not None and COMPARE_FUNCS[node.operator](value, node.value)
    if isinstance(node, RegexNode):
        haystack: str = flatten_text(document if node.field is None else get_path(document, node.field))
        return re.search(node.pattern, haystack, flags=re.IGNORECASE) is not None
    if isinstance(node, NotNode):
        return not match_node(node.child, document)
    if isinstance(node, AndNode):
        return match_node(node.left, document) and match_node(node.right, document)
    return match_node(node.left, document) or match_node(node.right, document)


def _to_node(query: str | SearchQuery | QueryNode) -> QueryNode:
    if isinstance(query, str):
        return parse_query(query).ast
    if isinstance(query, SearchQuery):
        return query.ast
    return query


def _contains(text: str, needle: str) -> bool:
    return needle.casefold() in text.casefold()


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
