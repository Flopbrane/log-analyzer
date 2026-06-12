# -*- coding: utf-8 -*-
"""
*.fv ファイルを解析するモジュール。
fv_parser は FVテキストを読み込み、
FVRecipe オブジェクトへ変換する責務を持つ。
このモジュールは実行を行わない。
入力:
    *.fv テキスト
出力:
    FVRecipe
Parserは
テキスト
↓
型
まで。

## 禁止事項
- 検索を実行しない
- 要約を実行しない
- Exportを実行しない
- query_engineを呼び出さない
- summary_engineを呼び出さない
- GUI処理を実装しない
このモジュールは *.fv を FVRecipe に変換することのみを担当する。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from collections.abc import Iterable

from fv_engine.fv_reserved_words import (
    FV_EXPORT_VALUES,
    FV_RESERVED_WORDS,
    FV_SUMMARY_VALUES,
)
from fv_engine.fv_types import FVExportFormat, FVRecipe, FVSummaryMode

__all__: list[str] = [
    "parse_fv_text",
    "parse_fv_lines",
]


def parse_fv_text(text: str) -> FVRecipe:
    """FVテキストを解析し、FVRecipeを返す。"""
    return parse_fv_lines(text.splitlines())


def parse_fv_lines(lines: Iterable[str]) -> FVRecipe:
    """FVテキスト行を解析し、FVRecipeを返す。"""
    sections: dict[str, list[str]] = {word: [] for word in FV_RESERVED_WORDS}
    current_section: str | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        line: str = raw_line.strip()
        if not line:
            continue

        section_name: str | None = _section_name(line)
        if section_name is not None:
            if section_name not in FV_RESERVED_WORDS:
                raise ValueError(f"未対応の予約語です: {section_name} ({line_number}行目)")
            current_section = section_name
            remainder: str = line[len(section_name) + 1 :].strip()
            if remainder:
                sections[current_section].append(remainder)
            continue

        if current_section is None:
            raise ValueError(f"予約語の前に本文があります ({line_number}行目): {line}")
        sections[current_section].append(raw_line.rstrip())

    title: str = _single_text(sections["TITLE"], "TITLE")
    query: str = "\n".join(part.strip() for part in sections["QUERY"] if part.strip())
    if not query:
        raise ValueError("QUERY は必須です。")

    summary_text: str = _optional_single_text(
        sections["SUMMARY"],
        "SUMMARY",
        FVSummaryMode.ON.value)
    summary_value: str = summary_text.upper()
    if summary_value not in FV_SUMMARY_VALUES:
        raise ValueError(f"SUMMARY は ON または OFF を指定してください: {summary_text}")

    export_text: str = _optional_single_text(
        sections["EXPORT"],
        "EXPORT",
        FVExportFormat.NONE.value)
    export_value: str = export_text.upper()
    if export_value not in FV_EXPORT_VALUES:
        raise ValueError(f"EXPORT は CSV、JSON、NONE のいずれかを指定してください: {export_text}")

    return FVRecipe(
        title=title,
        query=query,
        summary=FVSummaryMode(summary_value),
        export=FVExportFormat(export_value),
    )


def _section_name(line: str) -> str | None:
    if ":" not in line:
        return None
    before_colon: str = line.split(":", 1)[0].strip()
    if not before_colon:
        return None
    candidate: str = before_colon.upper()
    if candidate in FV_RESERVED_WORDS:
        return candidate
    if candidate.isidentifier() and candidate == before_colon:
        return candidate
    return None


def _single_text(values: list[str], section: str) -> str:
    text: str = _optional_single_text(values, section, "")
    if not text:
        raise ValueError(f"{section} は必須です。")
    return text


def _optional_single_text(
    values: list[str],
    section: str,
    default: str) -> str:
    meaningful_values: list[str] = [
        value.strip()
        for value in values
        if value.strip()]

    if not meaningful_values:
        return default

    if len(meaningful_values) > 1:
        raise ValueError(f"{section} は1行で指定してください。")

    return meaningful_values[0]
