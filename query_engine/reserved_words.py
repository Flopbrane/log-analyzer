"""検索DSLとSQLで特別扱いされる予約語リスト。"""
from __future__ import annotations

DSL_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "AND",
        "OR",
        "NOT",
    }
)

SQL_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "ADD",
        "ALL",
        "ALTER",
        "AND",
        "ANY",
        "AS",
        "ASC",
        "BETWEEN",
        "BY",
        "CASE",
        "CHECK",
        "COLUMN",
        "CREATE",
        "DELETE",
        "DESC",
        "DISTINCT",
        "DROP",
        "ELSE",
        "END",
        "EXISTS",
        "FROM",
        "GROUP",
        "HAVING",
        "IN",
        "INDEX",
        "INSERT",
        "INTO",
        "IS",
        "JOIN",
        "KEY",
        "LIKE",
        "LIMIT",
        "NOT",
        "NULL",
        "ON",
        "OR",
        "ORDER",
        "PRIMARY",
        "REGEXP",
        "SELECT",
        "SET",
        "TABLE",
        "THEN",
        "UNION",
        "UPDATE",
        "VALUES",
        "WHEN",
        "WHERE",
    }
)

QUERY_ENGINE_SYMBOLS: tuple[str, ...] = (
    ":",
    "<",
    "<=",
    ">",
    ">=",
    "==",
    "!=",
    "~",
    "/.../",
    '"..."',
    "(",
    ")",
    "-term",
)

RESERVED_WORDS: frozenset[str] = DSL_RESERVED_WORDS | SQL_RESERVED_WORDS
