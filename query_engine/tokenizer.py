"""古いimportを残すための互換モジュール。

旧サンプルが動くように、綴りがずれたモジュール名を一時的に残しています。
新しいコードでは :mod:`query_engine.parser` を使ってください。
"""
from __future__ import annotations

from query_engine.parser import GRAMMAR, QuerySyntaxError, Token, TokenKind, parse, parse_query, tokenize

__all__: list[str] = [
    "GRAMMAR",
    "QuerySyntaxError",
    "Token",
    "TokenKind",
    "parse",
    "parse_query",
    "tokenize",
]
