# -*- coding: utf-8 -*-
"""RawRecordをViewer標準のLogDict候補へ正規化するモジュール。"""
from __future__ import annotations

from enum import Enum
from typing import Any, cast


class LogType(str, Enum):
    """入力ログの構造種別。"""

    LOGGER_PROJECT = "logger_project"
    FLAT_PRODUCTION = "flat_production"
    NESTED_JSON = "nested_json"
    WINDOWS_EVENT = "windows_event"
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

NESTED_JSON_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "time",
        "severity",
        "service",
        "event",
    }
)

WINDOWS_EVENT_KEYS: frozenset[str] = frozenset(
    {
        "EventID",
        "Level",
        "Provider",
        "Message",
    }
)


def detect_log_type(raw: dict[str, Any]) -> LogType:
    """キー構造からログ形式を判定する。"""
    keys: set[str] = set(raw)
    if LOGGER_PROJECT_KEYS.issubset(keys):
        return LogType.LOGGER_PROJECT
    if FLAT_PRODUCTION_REQUIRED_KEYS.issubset(keys):
        return LogType.FLAT_PRODUCTION
    if NESTED_JSON_REQUIRED_KEYS.issubset(keys):
        return LogType.NESTED_JSON
    if WINDOWS_EVENT_KEYS.issubset(keys):
        return LogType.WINDOWS_EVENT
    return LogType.UNKNOWN


def normalize_log_record(raw: dict[str, Any]) -> dict[str, Any]:
    """RawRecordをViewer標準のLogDict候補へ変換する。"""
    log_type: LogType = detect_log_type(raw)
    if log_type == LogType.LOGGER_PROJECT:
        return dict(raw)
    if log_type == LogType.FLAT_PRODUCTION:
        return _normalize_flat_production_log(raw)
    if log_type == LogType.NESTED_JSON:
        return _normalize_nested_json_log(raw)
    if log_type == LogType.WINDOWS_EVENT:
        return _normalize_windows_event_log(raw)
    return dict(raw)


def normalize_external_log(raw: dict[str, Any]) -> dict[str, Any]:
    """互換用: 外部ログをViewer標準形式へ変換する。"""
    return normalize_log_record(raw)


def _normalize_flat_production_log(raw: dict[str, Any]) -> dict[str, Any]:
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
        "context": _build_external_context(raw, FLAT_PRODUCTION_REQUIRED_KEYS),
        "output": "both",
    }


def _normalize_nested_json_log(raw: dict[str, Any]) -> dict[str, Any]:
    service = _as_mapping(raw.get("service"))
    event = _as_mapping(raw.get("event"))
    module = service.get("name") or service.get("module") or "nested_json"
    event_id = event.get("id") or raw.get("event_id") or raw.get("id")
    message = event.get("message") or raw.get("message") or ""
    return {
        "level": str(raw.get("severity") or raw.get("level") or "INFO").upper(),
        "time": str(raw["time"]),
        "trace_id": str(event_id or f"nested:{raw['time']}:{module}"),
        "where": {
            "module": str(module),
        },
        "what": {
            "message": str(message),
        },
        "context": _build_external_context(raw, NESTED_JSON_REQUIRED_KEYS),
        "output": "both",
    }


def _normalize_windows_event_log(raw: dict[str, Any]) -> dict[str, Any]:
    event_id = raw.get("EventID")
    provider = raw.get("Provider")
    return {
        "level": _normalize_windows_level(raw.get("Level")),
        "time": str(raw.get("TimeCreated") or raw.get("timestamp") or ""),
        "trace_id": str(event_id),
        "where": {
            "module": str(provider or "Windows Event Log"),
        },
        "what": {
            "message": str(raw.get("Message") or ""),
        },
        "context": _build_external_context(raw, WINDOWS_EVENT_KEYS),
        "output": "both",
    }


def _normalize_windows_level(value: object) -> str:
    text = str(value or "INFO").upper()
    if text in {"ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"}:
        return text
    if text in {"WARN", "WARNING_LEVEL"}:
        return "WARNING"
    if text in {"INFORMATION", "INFORMATIONAL"}:
        return "INFO"
    return text


def _build_external_context(raw: dict[str, Any], required_keys: frozenset[str]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    raw_context: object = raw.get("context")
    if isinstance(raw_context, dict):
        context.update(cast(dict[str, Any], raw_context))

    context["original_row"] = dict(raw)
    for key, value in raw.items():
        if key not in required_keys and key != "context":
            context.setdefault(key, value)
    return context


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(cast(dict[str, Any], value))
    return {}
