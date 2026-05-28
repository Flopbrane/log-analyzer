"""TraceQL/parserエラーをViewer向けレポートへ変換する橋渡し。"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from logs.error_response_dict import (EXPECTED_HINTS, FIELD_ALIASES,
                                      FIELD_VALUE_SUGGESTIONS, KNOWN_FIELDS)

POSITION_PATTERN: re.Pattern[str] = re.compile(r"position\s+(\d+)", flags=re.IGNORECASE)
FIELD_PREFIX_PATTERN: re.Pattern[str] = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*:\s*$")


@dataclass(frozen=True, slots=True)
class QueryErrorResponse:
    """Viewerで表示する構文エラーレポート。"""

    query: str
    error: str
    position: int | None
    expected: str
    suggestions: tuple[str, ...]

    def format_report(self) -> str:
        lines: list[str] = [
            "QUERY ERROR",
            "=" * 60,
            f"Query : {self.query}",
            f"Error : {self.error}",
        ]
        if self.expected:
            lines.append(f"Expected : {self.expected}")
        if self.position is not None:
            caret_index: int = max(self.position - 1, 0)
            lines.extend(["", self.query, " " * caret_index + "^"])
        if self.suggestions:
            lines.extend(["", "Did you mean:"])
            lines.extend(f"- {suggestion}" for suggestion in self.suggestions)
        return "\n".join(lines)


def build_query_error_response(query: str, error: str) -> QueryErrorResponse:
    """query/error文字列から候補付きレスポンスを組み立てる。"""
    position: int | None = _extract_position(error)
    expected: str = _classify_expected(error)
    suggestions: tuple[str, ...] = tuple(_build_suggestions(query, expected))
    return QueryErrorResponse(
        query=query,
        error=error,
        position=position,
        expected=expected,
        suggestions=suggestions,
    )


def build_query_error_text(query: str, error: str) -> str:
    """Viewer表示用の構文エラー文字列を返す。"""
    return build_query_error_response(query, error).format_report()


def _extract_position(error: str) -> int | None:
    match: re.Match[str] | None = POSITION_PATTERN.search(error)
    if match is None:
        return None
    return int(match.group(1))


def _classify_expected(error: str) -> str:
    lowered = error.lower()
    if "expected field value" in lowered:
        return EXPECTED_HINTS["field_value"]
    if "expected numeric value" in lowered:
        return EXPECTED_HINTS["numeric_value"]
    if "invalid comparison operator" in lowered or "invalid operator" in lowered:
        return EXPECTED_HINTS["operator"]
    if "expected expression" in lowered:
        return EXPECTED_HINTS["expression"]
    return ""


def _build_suggestions(query: str, expected: str) -> list[str]:
    stripped: str = query.strip()
    field_match: re.Match[str] | None = FIELD_PREFIX_PATTERN.fullmatch(stripped)
    if field_match is not None and expected == EXPECTED_HINTS["field_value"]:
        field: str = _normalize_field(field_match.group(1))
        return [f"{field}:{value}" for value in FIELD_VALUE_SUGGESTIONS.get(field, ())]

    if ":" in stripped:
        field, value = stripped.split(":", 1)
        normalized: str = _normalize_field(field.strip())
        if normalized != field.strip() and value:
            return [f"{normalized}:{value.strip()}"]

    first_word: str = stripped.split(":", 1)[0].split(" ", 1)[0].strip()
    if first_word:
        close_fields: list[str] = difflib.get_close_matches(first_word, KNOWN_FIELDS, n=3, cutoff=0.72)
        return [f"{field}:" for field in close_fields]

    return []


def _normalize_field(field: str) -> str:
    lowered: str = field.lower()
    if lowered in FIELD_ALIASES:
        return FIELD_ALIASES[lowered]
    close_fields: list[str] = difflib.get_close_matches(lowered, KNOWN_FIELDS, n=1, cutoff=0.72)
    return close_fields[0] if close_fields else lowered
