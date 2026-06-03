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
    """集計結果をViewerへ出しやすい複数行要約へ変換する。"""
    condition: str = condition_text if condition_text else "条件なし"
    lines: list[str] = [
        "検索条件",
        f"  条件: {condition}",
        f"  件数: {total_count}",
    ]

    if total_count == 0:
        lines.extend(["", "該当ログはありません。"])
        return "\n".join(lines)

    if level_counts:
        lines.extend(["", "レベル別件数"])
        for key, value in sorted(level_counts.items()):
            lines.append(f"  - {key}: {value}")

    if module_ranking:
        lines.extend(["", "モジュール上位"])
        lines.extend(_format_ranking_lines(module_ranking))

    if message_ranking:
        lines.extend(["", "メッセージ上位"])
        lines.extend(_format_ranking_lines(message_ranking))

    for stat in list(context_numeric_stats.values())[:3]:
        if "数値コンテキスト" not in lines:
            lines.extend(["", "数値コンテキスト"])
        lines.extend(
            [
                f"  - {stat.field}",
                f"      件数: {stat.count}",
                f"      平均: {stat.average:.6g}",
                f"      最小: {stat.minimum:.6g}",
                f"      最大: {stat.maximum:.6g}",
                f"      中央値: {stat.median:.6g}",
            ]
        )

    if insights:
        lines.extend(["", "所見"])
        for insight in insights:
            lines.append(f"  - {insight}")

    return "\n".join(lines)


def _format_ranking_lines(items: Sequence[RankingItem]) -> list[str]:
    return [f"  - {item.key}: {item.count}" for item in items]
