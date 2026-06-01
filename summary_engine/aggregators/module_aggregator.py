# -*- coding: utf-8 -*-
"""モジュール集計モジュール
module_aggregator.pyは、ログデータのモジュール情報を集計し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータの条件別統計を作成し、人間が理解しやすい要約を生成するための基盤を提供します。"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from summary_engine.aggregators.count_aggregator import count_by_field
from summary_engine.analyzers.ranking_analyzer import top_items
from summary_engine.summary_types import RankingItem


def aggregate_modules(logs: Iterable[Mapping[str, Any]], limit: int = 5) -> tuple[RankingItem, ...]:
    """where.module別の上位ランキングを返す。"""
    return top_items(count_by_field(logs, "where.module"), limit=limit)
