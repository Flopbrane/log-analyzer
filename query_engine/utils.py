"""パーサーと評価器で共有する小さな補助関数。"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast


def get_path(document: Any, path: str) -> Any:
    """dict/list 形状の文書からドット区切りパスで値を取得する。"""
    current: object = document
    for part in path.split("."):
        if isinstance(current, Mapping):
            mapping: Mapping[str, object] = cast("Mapping[str, object]", current)
            if part not in mapping:
                return None
            current = mapping[part]
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            sequence: Sequence[object] = cast("Sequence[object]", current)
            if not part.isdigit():
                return None
            index = int(part)
            if index >= len(sequence):
                return None
            current = sequence[index]
            continue
        return None
    return current


def flatten_text(value: Any) -> str:
    """ネストしたJSON風の値を全文検索用テキストへ変換する。"""
    if value is None:
        return ""
    if isinstance(value, Mapping):
        mapping: Mapping[object, object] = cast("Mapping[object, object]", value)
        parts: list[str] = []
        for key, child in mapping.items():
            parts.append(str(key))
            parts.append(flatten_text(child))
        return " ".join(part for part in parts if part)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        return " ".join(flatten_text(child) for child in sequence)
    return str(value)
