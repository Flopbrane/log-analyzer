# -*- coding: utf-8 -*-
"""ログデータのメッセージ情報を集計し、要約エンジンに提供するモジュール。
このモジュールは、ログデータからメッセージ情報を抽出し、その出現頻度や関連する情報を集計して、要約エンジンに提供する役割を担います。"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from summary_engine.aggregators.count_aggregator import count_by_field
from summary_engine.analyzers.ranking_analyzer import top_items
from summary_engine.summary_types import RankingItem


def aggregate_messages(logs: Iterable[Mapping[str, Any]], limit: int = 5) -> tuple[RankingItem, ...]:
    """what.message別の上位ランキングを返す。"""
    return top_items(count_by_field(logs, "what.message"), limit=limit)
