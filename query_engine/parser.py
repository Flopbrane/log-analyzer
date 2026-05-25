"""検索DSL文字列をASTへ変換するパーサー。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from query_engine.ast import (
    AndNode,
    CompareNode,
    CompareOperator,
    EmptyNode,
    FieldNode,
    NotNode,
    OrNode,
    PhraseNode,
    QueryNode,
    RegexNode,
    TermNode,
)
from query_engine.grammar import COMPARE_OPERATORS, GRAMMAR, IDENT_PATTERN, TokenKind
from query_engine.models import SearchQuery

__all__: list[str] = [
    "GRAMMAR",
    "QuerySyntaxError",
    "Token",
    "parse",
    "parse_query",
    "tokenize",
]


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: str
    position: int


class QuerySyntaxError(ValueError):
    """検索文字列が固定文法に一致しないときに送出する例外。"""


def parse_query(text: str) -> SearchQuery:
    parser: _Parser = _Parser(tokenize(text), raw_text=text)
    ast_root: QueryNode = parser.parse()
    return SearchQuery(raw_text=text, ast=ast_root)


def parse(text: str) -> QueryNode:
    return parse_query(text).ast


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    length: int = len(text)
    while index < length:
        char: str = text[index]
        if char.isdigit():
            # 日時 token: YYYY-MM-DD HH:MM / YYYY-MM-DD HH:MM:SS
            datetime_match: re.Match[str] | None = re.match(
                r"\d{2,4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}(:\d{2})?",
                text[index:],
            )
            if datetime_match:
                value: str = datetime_match.group(0)
                tokens.append(Token(TokenKind.WORD, value, index))
                index += len(value)
                continue

            # 時刻 token: HH:MM / HH:MM:SS
            time_match: re.Match[str] | None = re.match(
                r"(?:[01]?\d|2[0-3]):[0-5]\d(:[0-5]\d)?",
                text[index:],
            )
            if time_match:
                value = time_match.group(0)
                tokens.append(Token(TokenKind.WORD, value, index))
                index += len(value)
                continue

            # 日付 token: YYYY-MM-DD
            date_match: re.Match[str] | None = re.match(
                r"\d{2,4}-\d{1,2}-\d{1,2}",
                text[index:],
            )
            if date_match:
                value = date_match.group(0)
                tokens.append(Token(TokenKind.WORD, value, index))
                index += len(value)
                continue
        if char.isspace():
            index += 1
            continue
        if char == "(":
            tokens.append(Token(TokenKind.LPAREN, char, index))
            index += 1
            continue
        if char == ")":
            tokens.append(Token(TokenKind.RPAREN, char, index))
            index += 1
            continue
        if char == ":":
            tokens.append(Token(TokenKind.COLON, char, index))
            index += 1
            continue
        if char == "~":
            tokens.append(Token(TokenKind.TILDE, char, index))
            index += 1
            continue
        if char in "<>!=":
            op: str = _read_operator(text, index)
            tokens.append(Token(TokenKind.OP, op, index))
            index += len(op)
            continue
        if char == '"':
            phrase, index = _read_phrase(text, index)
            tokens.append(Token(TokenKind.PHRASE, phrase, index))
            continue
        if char == "/":
            pattern, index = _read_regex(text, index)
            tokens.append(Token(TokenKind.REGEX, pattern, index))
            continue

        word_start: int = index
        while index < length and not text[index].isspace() and text[index] not in '():"~<>!=':
            index += 1
        tokens.append(Token(TokenKind.WORD, text[word_start:index], word_start))

    tokens.append(Token(TokenKind.EOF, "", length))
    return tokens


def _read_operator(text: str, index: int) -> str:
    two: str = text[index : index + 2]
    if two in COMPARE_OPERATORS:
        return two
    one: str = text[index]
    if one in {"<", ">"}:
        return one
    raise QuerySyntaxError(f"Invalid operator at position {index}.")


def _read_phrase(text: str, index: int) -> tuple[str, int]:
    index += 1
    chars: list[str] = []
    while index < len(text):
        char: str = text[index]
        if char == "\\" and index + 1 < len(text):
            chars.append(text[index + 1])
            index += 2
            continue
        if char == '"':
            return "".join(chars), index + 1
        chars.append(char)
        index += 1
    raise QuerySyntaxError("Unterminated quoted phrase.")


def _read_regex(text: str, index: int) -> tuple[str, int]:
    index += 1
    chars: list[str] = []
    while index < len(text):
        char: str = text[index]
        if char == "\\" and index + 1 < len(text):
            chars.extend([char, text[index + 1]])
            index += 2
            continue
        if char == "/":
            return "".join(chars), index + 1
        chars.append(char)
        index += 1
    raise QuerySyntaxError("Unterminated regex pattern.")


class _Parser:
    def __init__(self, tokens: list[Token], *, raw_text: str) -> None:
        self.tokens: list[Token] = tokens
        self.raw_text: str = raw_text
        self.index = 0

    def parse(self) -> QueryNode:
        if self._peek().kind == TokenKind.EOF:
            return EmptyNode()
        node: QueryNode = self._parse_or()
        self._expect(TokenKind.EOF)
        return node

    def _parse_or(self) -> QueryNode:
        node: QueryNode = self._parse_and()
        while self._match_word("OR"):
            node = OrNode(left=node, right=self._parse_and())
        return node

    def _parse_and(self) -> QueryNode:
        node: QueryNode = self._parse_not()
        while self._starts_primary() or self._match_word("AND"):
            node = AndNode(left=node, right=self._parse_not())
        return node

    def _parse_not(self) -> QueryNode:
        if self._match_word("NOT"):
            return NotNode(self._parse_not())
        token: Token = self._peek()
        if token.kind == TokenKind.WORD and token.value.startswith("-") and len(token.value) > 1:
            self._advance()
            return NotNode(TermNode(token.value[1:]))
        return self._parse_primary()

    def _parse_primary(self) -> QueryNode:
        token: Token = self._peek()
        if token.kind == TokenKind.LPAREN:
            self._advance()
            node: QueryNode = self._parse_or()
            self._expect(TokenKind.RPAREN)
            return node
        if token.kind == TokenKind.PHRASE:
            self._advance()
            return PhraseNode(token.value)
        if token.kind == TokenKind.TILDE:
            self._advance()
            return RegexNode(pattern=self._expect(TokenKind.REGEX).value)
        if token.kind != TokenKind.WORD:
            raise QuerySyntaxError(f"Expected expression at position {token.position}.")

        word: str = self._advance().value
        if self._match(TokenKind.COLON):
            return FieldNode(field=_validate_identifier(word), value=self._read_value())
        if self._match(TokenKind.TILDE):
            return RegexNode(field=_validate_identifier(word), pattern=self._expect(TokenKind.REGEX).value)
        if self._peek().kind == TokenKind.OP:
            operator: CompareOperator = _parse_compare_operator(self._advance().value)
            number: str = self._expect(TokenKind.WORD).value
            return CompareNode(field=_validate_identifier(word), operator=operator, value=_parse_number(number))
        compact: QueryNode | None = _parse_compact_atom(word)
        if compact is not None:
            return compact
        return TermNode(word)

    def _read_value(self) -> str:
        token: Token = self._peek()
        if token.kind in {TokenKind.WORD, TokenKind.PHRASE}:
            return self._advance().value
        raise QuerySyntaxError(f"Expected field value at position {token.position}.")

    def _starts_primary(self) -> bool:
        token: Token = self._peek()
        if token.kind in {TokenKind.WORD, TokenKind.PHRASE, TokenKind.LPAREN, TokenKind.TILDE}:
            if token.kind == TokenKind.WORD and token.value.upper() in {"AND", "OR"}:
                return False
            return True
        return False

    def _match_word(self, value: str) -> bool:
        token: Token = self._peek()
        if token.kind == TokenKind.WORD and token.value.upper() == value:
            self._advance()
            return True
        return False

    def _match(self, kind: TokenKind) -> bool:
        if self._peek().kind == kind:
            self._advance()
            return True
        return False

    def _expect(self, kind: TokenKind) -> Token:
        token: Token = self._peek()
        if token.kind != kind:
            raise QuerySyntaxError(f"Expected {kind.value} at position {token.position}.")
        return self._advance()

    def _peek(self) -> Token:
        return self.tokens[self.index]

    def _advance(self) -> Token:
        token: Token = self.tokens[self.index]
        self.index += 1
        return token


def _parse_compact_atom(word: str) -> QueryNode | None:
    field_match: re.Match[str] | None = re.fullmatch(rf"({IDENT_PATTERN}):(.+)", word)
    if field_match:
        return FieldNode(field=field_match.group(1), value=field_match.group(2))
    compare_match: re.Match[str] | None = re.fullmatch(rf"({IDENT_PATTERN})(<=|>=|==|!=|<|>)(-?\d+(?:\.\d+)?)", word)
    if compare_match:
        return CompareNode(
            field=compare_match.group(1),
            operator=_parse_compare_operator(compare_match.group(2)),
            value=float(compare_match.group(3)),
        )
    return None


def _validate_identifier(value: str) -> str:
    if not re.fullmatch(IDENT_PATTERN, value):
        raise QuerySyntaxError(f"Invalid field name: {value!r}.")
    return value


def _parse_number(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise QuerySyntaxError(f"Expected numeric value, got {value!r}.") from exc


def _parse_compare_operator(value: str) -> CompareOperator:
    if value in COMPARE_OPERATORS:
        return cast(CompareOperator, value)
    raise QuerySyntaxError(f"Invalid comparison operator: {value!r}.")
