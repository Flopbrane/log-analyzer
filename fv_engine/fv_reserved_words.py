# -*- coding: utf-8 -*-
"""
*.fv で使用する予約語定義。
例:
    TITLE
    QUERY
    SUMMARY
    EXPORT
fv_parser はこの定義を利用して
FV文書を解析する。

## 禁止事項
- 検索処理を実装しない
- 要約処理を実装しない
- Export処理を実装しない
- ファイルI/Oを行わない
- GUI処理を実装しない
このモジュールは型定義のみを担当する。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

FV_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "TITLE",
        "QUERY",
        "SUMMARY",
        "EXPORT",
    }
)

FUTURE_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "SOURCE",
        "PURPOSE",
        "REPORT",
    }
)

ADVANCED_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "SQL",
        "TOP_MESSAGE",
        "TOP_MODULE",
        "TOP_IP",
        "LIMIT",
    }
)

FV_SUMMARY_VALUES: frozenset[str] = frozenset(
    {
        "ON",
        "OFF",
    }
)

FV_EXPORT_VALUES: frozenset[str] = frozenset(
    {
        "NONE",
        "CSV",
        "JSON",
    }
)

__all__: list[str] = [
    "FV_RESERVED_WORDS",
    "FV_SUMMARY_VALUES",
    "FV_EXPORT_VALUES",
]
