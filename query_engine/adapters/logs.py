"""ログ風のdictを汎用Documentへ寄せるアダプタ。"""
from __future__ import annotations

from typing import Any, Mapping

from query_engine.adapters.base import normalize_document
from query_engine.models import Document
from query_engine.utils import flatten_text


def log_to_document(log: Mapping[str, Any]) -> Document:
    """ログdictを検索用Documentへ変換する。

    Logger専用型へは依存せず、一般的なキーだけを緩く拾います。
    """
    message: str = _first_text(log, "message", "msg", "text")
    level: str = _first_text(log, "level", "severity")
    timestamp: str = _first_text(log, "time", "timestamp", "created_at")
    return normalize_document(
        {
            "level": level,
            "timestamp": timestamp,
            "message": message,
        },
        id=str(log.get("trace_id", "")),
        title=message[:80],
        text=flatten_text(log),
        source=str(log.get("source", "")),
        metadata=dict(log),
    ).to_mapping()


def _first_text(data: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value: Any | None = data.get(key)
        if value is not None:
            return str(value)
    return ""
