"""TraceQL構文エラー時の候補生成に使う辞書。"""
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
    "date": ("2026-05-28",),
    "local_date": ("2026-05-28",),
    "local_clock": ("10:00:00",),
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

KNOWN_FIELDS: tuple[str, ...] = tuple(
    sorted(set(FIELD_VALUE_SUGGESTIONS) | set(FIELD_ALIASES.values()))
)

EXPECTED_HINTS: dict[str, str] = {
    "field_value": "field value",
    "expression": "expression",
    "numeric_value": "numeric value",
    "operator": "comparison operator",
}
