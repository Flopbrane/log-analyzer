# -*- coding: utf-8 -*-
"""検索DSLの文法仕様を集約するモジュール。

このファイルを文法の基準点にします。parser.py はここに定義された
トークン種別、識別子ルール、演算子、文法説明を参照して動きます。
将来 TypeScript へ移植するときも、まずこの内容を写す想定です。
"""
from __future__ import annotations

from enum import Enum
from typing import LiteralString

from query_engine.models import GrammarSpec
from query_engine.reserved_words import DSL_RESERVED_WORDS

IDENT_PATTERN = r"[A-Za-z_][A-Za-z0-9_.-]*"
COMPARE_OPERATORS: frozenset[str] = frozenset({"<", "<=", ">", ">=", "==", "!="})
LOGICAL_OPERATORS: frozenset[str] = DSL_RESERVED_WORDS

GRAMMAR = GrammarSpec(
    name="Query Engine DSL",
    version="0.1",
    rules=(
        "裸の単語は文書全体の全文検索として扱う。",
        "ダブルクォートで囲んだ文字列は完全一致フレーズとして扱う。",
        "field:value は指定フィールドの値を検索する。",
        "field>=10、field < 10 などの数値比較を扱う。",
        "AND は OR より強く結合し、隣接した条件は AND とみなす。",
        "NOT term と -term は条件を否定する。",
        "丸括弧で条件の結合順を明示できる。",
        "field~/pattern/ または ~/pattern/ は正規表現検索として扱う。",
    ),
)

GRAMMAR_EBNF: LiteralString = """
query       := or_expr
or_expr     := and_expr ("OR" and_expr)*
and_expr    := not_expr (("AND")? not_expr)*
not_expr    := ("NOT" | "-") not_expr | primary
primary     := term | phrase | field | compare | regex | "(" query ")"
field       := IDENT ":" VALUE
compare     := IDENT OP NUMBER
regex       := IDENT? "~" "/" PATTERN "/"
""".strip()


class TokenKind(str, Enum):
    """検索DSLで使うトークン種別。"""

    WORD = "WORD"
    PHRASE = "PHRASE"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COLON = "COLON"
    OP = "OP"
    REGEX = "REGEX"
    TILDE = "TILDE"
    EOF = "EOF"
