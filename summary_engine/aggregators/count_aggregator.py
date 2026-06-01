# -*- coding: utf-8 -*-
"""件数集計モジュール。"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


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


def get_nested_value(
    mapping: Mapping[str, Any],
    field_path: str,
) -> object:
    """ドット区切りのフィールドパスに従って、ネストされた値を取得する。"""
    if not field_path:
        return mapping

    current: object = mapping

    for part in field_path.split("."):
        # このScriptは、"."で区切られたフィールドパスを使用して、ネストされたMappingから値を取得するための関数です。
        # 例えば、フィールドパスが"where.module"の場合、この関数はmapping["where"]["module"]の値を返します。
        # なので、Forブロックの外にif文を出してしまうと、1階層目しか探せなくなります。
        if not isinstance(current, Mapping):
            return None

        if part not in current:
            return None

        current = current[part]

    return current