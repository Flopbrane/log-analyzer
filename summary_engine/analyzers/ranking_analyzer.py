# -*- coding: utf-8 -*-
"""ランキング分析モジュール
ranking_analyzer.pyは、ログデータのランキング情報を分析し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータのパターンを分析し、ランキングに基づく洞察を提供して、人間が理解しやすい要約を生成するための基盤を提供します。"""
from __future__ import annotations

from collections.abc import Mapping

from summary_engine.summary_types import RankingItem


def top_items(counts: Mapping[str, int], limit: int = 5) -> tuple[RankingItem, ...]:
    """件数dictを多い順、同数なら名前順に並べる。"""
    sorted_items: list[tuple[str, int]] = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(RankingItem(key=key, count=count) for key, count in sorted_items[:limit])
