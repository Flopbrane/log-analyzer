# -*- coding: utf-8 -*-
"""外部ログ形式をViewer標準形式へ寄せる分析・変換モジュール。"""
from __future__ import annotations

from enum import Enum
from typing import Any, cast


class LogType(str, Enum):
    """入力ログの構造種別。"""

    LOGGER_PROJECT = "logger_project"
    FLAT_PRODUCTION = "flat_production"
    UNKNOWN = "unknown"


LOGGER_PROJECT_KEYS: frozenset[str] = frozenset(
    {
        "level",
        "time",
        "trace_id",
        "where",
        "what",
        "context",
        "output",
    }
)

FLAT_PRODUCTION_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "timestamp",
        "level",
        "module",
        "event_id",
        "message",
    }
)


def detect_log_type(raw: dict[str, Any]) -> LogType:
    """キー構造からログ形式を判定する。"""
    keys: set[str] = set(raw)
    if LOGGER_PROJECT_KEYS.issubset(keys):
        return LogType.LOGGER_PROJECT
    if FLAT_PRODUCTION_REQUIRED_KEYS.issubset(keys):
        return LogType.FLAT_PRODUCTION
    return LogType.UNKNOWN


def normalize_external_log(raw: dict[str, Any]) -> dict[str, Any]:
    """外部ログをViewer標準形式へ変換する。標準ログは呼び出し側で除外する。"""
    log_type: LogType = detect_log_type(raw)
    if log_type == LogType.FLAT_PRODUCTION:
        return _normalize_flat_production_log(raw)
    return dict(raw)


def _normalize_flat_production_log(raw: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = _build_external_context(raw)
    return {
        "level": str(raw["level"]),
        "time": str(raw["timestamp"]),
        "trace_id": str(raw["event_id"]),
        "where": {
            "module": str(raw["module"]),
        },
        "what": {
            "message": str(raw["message"]),
        },
        "context": context,
        "output": "both",
    }


def _build_external_context(raw: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    raw_context: object = raw.get("context")
    if isinstance(raw_context, dict):
        context.update(cast(dict[str, Any], raw_context))

    context["original_row"] = dict(raw)
    for key, value in raw.items():
        if key not in FLAT_PRODUCTION_REQUIRED_KEYS and key != "context":
            context.setdefault(key, value)
    return context
