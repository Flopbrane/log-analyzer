# -*- coding: utf-8 -*-
"""ユーザー集計モジュール
user_aggregator.pyは、ログデータのユーザー情報を集計し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータの条件別統計を作成し、人間が理解しやすい要約を生成するための基盤を提供します。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from summary_engine.aggregators.count_aggregator import get_nested_value
from summary_engine.analyzers.ranking_analyzer import top_items
from summary_engine.summary_types import RankingItem

USER_FIELD_PATHS: tuple[str, ...] = (
    "context.user",
    "context.user_id",
    "context.user.id",
    "context.original_row.user",
    "context.original_row.user.id",
    "context.original_row.user_id",
    "user",
    "user_id",
)


def aggregate_users(logs: Iterable[Mapping[str, Any]], limit: int = 5) -> tuple[RankingItem, ...]:
    """ログ内のユーザー候補を集計し、上位ランキングを返す。"""
    counts: Counter[str] = Counter()
    for log in logs:
        value: object | None = _first_value(log, USER_FIELD_PATHS)
        if value not in (None, ""):
            counts[str(value)] += 1
    return top_items(dict(counts), limit=limit)


def _first_value(log: Mapping[str, Any], field_paths: Iterable[str]) -> object | None:
    for field_path in field_paths:
        value: object | None = get_nested_value(log, field_path)
        if value not in (None, ""):
            return value
    return None
