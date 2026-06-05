# -*- coding: utf-8 -*-
"""TraceQL構文エラー時の候補生成に使う辞書。
TraceQL構文エラー時に候補を出すための辞書や定数を定義しています。
これらはquery_engineの内部でのみ使用され、logs層やViewerには直接関係しません。
将来的には、これらの定数や辞書を外部から拡張できるようにすることも検討しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

FIELD_VALUE_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "level": ("ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"),
    "message": ("timeout", "failed", "success", "error"),
    "msg": ("timeout", "failed", "success", "error"),
    "trace": ("trace_id",),
    "trace_id": ("trace-1",),
    "output": ("file", "console", "both"),
    "function": ("run", "main"),
    "func": ("run", "main"),
    "file": ("app.py",),
    "module": ("logs", "query_engine"),
}

FIELD_ALIASES: dict[str, str] = {
    "severity": "level",
    "type": "level",
    "text": "message",
    "massage": "message",
    "function_name": "function",
    "traceid": "trace_id",
    "trace.id": "trace_id",
}

DATETIME_FIELDS: tuple[str, ...] = ("date", "local_date", "local_clock")

KNOWN_FIELDS: tuple[str, ...] = tuple(
    sorted(set(FIELD_VALUE_SUGGESTIONS) | set(FIELD_ALIASES.values()) | set(DATETIME_FIELDS))
)

EXPECTED_HINTS: dict[str, str] = {
    "field_value": "field value",
    "expression": "expression",
    "numeric_value": "numeric value",
    "operator": "comparison operator",
}
