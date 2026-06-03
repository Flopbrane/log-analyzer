# -*- coding: utf-8 -*-

"""件数集計モジュール。"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any, Iterable


def count_by_field(logs: Iterable[Mapping[str, Any]], field_path: str) -> dict[str, int]:
    """ドット区切りのフィールド値ごとに件数を集計する。"""
    counts: Counter[str] = Counter()
    for log in logs:
        value: object = get_nested_value(log, field_path)
        if value in (None, ""):
            counts["<missing>"] += 1
        else:
            counts[str(value)] += 1
    return dict(counts)


# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
def get_nested_value(
    mapping: Mapping[str, Any],
    field_path: str,
) -> object | None:
    """ドット区切りのフィールドパスに従って、ネストされた値を取得する。(動的なJSON探索に使用)"""
    if not field_path:
        return mapping

    current: object = mapping

    for part in field_path.split("."):
        if not isinstance(current, Mapping):
            return None

        value: object | None = current.get(part)

        if value is None:
            return None

        current = value

    return current