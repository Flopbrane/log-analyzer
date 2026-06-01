# -*- coding: utf-8 -*-
"""テキスト要約モジュール
text_summary.pyは、ログデータのテキスト情報を要約し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータのテキスト情報を分析し、テキストに基づく洞察を提供して、人間が理解しやすい要約を生成するための基盤を提供します。"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from summary_engine.summary_types import NumericStats, RankingItem


def build_text_summary(
    total_count: int,
    condition_text: str,
    level_counts: Mapping[str, int],
    module_ranking: Sequence[RankingItem],
    message_ranking: Sequence[RankingItem],
    context_numeric_stats: Mapping[str, NumericStats],
    insights: Sequence[str],
) -> str:
    """集計結果をViewerへ出しやすい1行要約へ変換する。"""
    condition: str = condition_text if condition_text else "条件なし"
    parts: list[str] = [f"条件: {condition}", f"件数: {total_count}"]
    if level_counts:
        levels: str = ", ".join(f"{key}={value}" for key, value in sorted(level_counts.items()))
        parts.append(f"level: {levels}")
    if module_ranking:
        parts.append("module上位: " + _format_ranking(module_ranking))
    if message_ranking:
        parts.append("message上位: " + _format_ranking(message_ranking))
    numeric_preview: list[str] = []
    for stat in list(context_numeric_stats.values())[:3]:
        numeric_preview.append(
            f"{stat.field} avg={stat.average:.6g} min={stat.minimum:.6g} max={stat.maximum:.6g}"
        )
    if numeric_preview:
        parts.append("数値: " + "; ".join(numeric_preview))
    if insights:
        parts.append("所見: " + " ".join(insights))
    return " / ".join(parts)


def _format_ranking(items: Sequence[RankingItem]) -> str:
    return ", ".join(f"{item.key}={item.count}" for item in items)
