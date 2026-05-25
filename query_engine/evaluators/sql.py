"""検索ASTをSQL WHERE句へ変換する初期コンパイラ。

このモジュールはDBへ直接接続しません。ASTを受け取り、プレースホルダ付き
SQL断片とパラメータだけを返します。SQLiteを最初の基準にしていますが、
field_mapperを差し替えれば他のDBにも寄せられます。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
from query_engine.models import SearchQuery
from query_engine.parser import parse_query

FieldMapper = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class SqlCompileResult:
    """SQL断片とバインド値をまとめた結果。"""

    where_sql: str
    params: tuple[object, ...]


def compile_sql_where(
    query: str | SearchQuery | QueryNode,
    *,
    text_column: str = "text",
    field_mapper: FieldMapper | None = None,
) -> SqlCompileResult:
    """検索条件をSQL WHERE句へ変換する。"""
    compiler: _SqlCompiler = _SqlCompiler(text_column=text_column, field_mapper=field_mapper)
    sql: str
    params: list[object]
    sql, params = compiler.compile(_to_node(query))
    return SqlCompileResult(where_sql=sql, params=tuple(params))


class _SqlCompiler:
    def __init__(self, *, text_column: str, field_mapper: FieldMapper | None) -> None:
        self.text_column = _quote_identifier(text_column)
        self.field_mapper = field_mapper

    def compile(self, node: QueryNode) -> tuple[str, list[object]]:
        if isinstance(node, EmptyNode):
            return "1 = 1", []
        if isinstance(node, TermNode):
            return f"{self.text_column} LIKE ?", [f"%{node.term}%"]
        if isinstance(node, PhraseNode):
            return f"{self.text_column} LIKE ?", [f"%{node.phrase}%"]
        if isinstance(node, FieldNode):
            return f"{self._field(node.field)} LIKE ?", [f"%{node.value}%"]
        if isinstance(node, CompareNode):
            return f"{self._field(node.field)} {node.operator} ?", [node.value]
        if isinstance(node, RegexNode):
            column: str = self.text_column if node.field is None else self._field(node.field)
            return f"{column} REGEXP ?", [node.pattern]
        if isinstance(node, NotNode):
            sql: str
            params: list[object]
            sql, params = self.compile(node.child)
            return f"NOT ({sql})", params
        if isinstance(node, AndNode):
            return self._compile_binary("AND", node.left, node.right)
        return self._compile_binary("OR", node.left, node.right)

    def _compile_binary(self, operator: str, left: QueryNode, right: QueryNode) -> tuple[str, list[object]]:
        left_sql: str
        left_params: list[object]
        right_sql: str
        right_params: list[object]
        left_sql, left_params = self.compile(left)
        right_sql, right_params = self.compile(right)
        return f"({left_sql}) {operator} ({right_sql})", [*left_params, *right_params]

    def _field(self, field: str) -> str:
        if self.field_mapper is not None:
            return self.field_mapper(field)
        return _quote_identifier(field.replace(".", "__"))


def _to_node(query: str | SearchQuery | QueryNode) -> QueryNode:
    if isinstance(query, str):
        return parse_query(query).ast
    if isinstance(query, SearchQuery):
        return query.ast
    return query


def _quote_identifier(identifier: str) -> str:
    """SQLite向けに識別子を安全にクォートする。"""
    escaped: str = identifier.replace('"', '""')
    return f'"{escaped}"'
