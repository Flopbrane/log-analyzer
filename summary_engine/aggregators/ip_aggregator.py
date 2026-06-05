# -*- coding: utf-8 -*-
"""ログに記録されているIPアドレスを集計し、要約エンジンに提供するモジュール。
このモジュールは、ログデータからIPアドレスを抽出し、その出現頻度や関連する情報を集計して、要約エンジンに提供する役割を担います。"""
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

IP_FIELD_PATHS: tuple[str, ...] = (
    "context.ip",
    "context.client_ip",
    "context.remote_addr",
    "context.original_row.ip",
    "context.original_row.client_ip",
    "context.original_row.remote_addr",
    "ip",
)


def aggregate_ips(logs: Iterable[Mapping[str, Any]], limit: int = 5) -> tuple[RankingItem, ...]:
    """ログ内のIPアドレス候補を集計し、上位ランキングを返す。"""
    counts: Counter[str] = Counter()
    for log in logs:
        value: object | None = _first_value(log, IP_FIELD_PATHS)
        if value not in (None, ""):
            counts[str(value)] += 1
    return top_items(dict(counts), limit=limit)


def _first_value(log: Mapping[str, Any], field_paths: Iterable[str]) -> object | None:
    for field_path in field_paths:
        value: object | None = get_nested_value(log, field_path)
        if value not in (None, ""):
            return value
    return None
