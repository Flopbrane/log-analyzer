# -*- coding: utf-8 -*-
"""異常検知モジュール
anomaly_analyzer.pyは、ログデータの異常を検知し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータのパターンを分析し、異常な挙動を特定して、人間が理解しやすい要約を生成するための基盤を提供します。"""
from __future__ import annotations

from collections.abc import Mapping


def detect_level_anomalies(level_counts: Mapping[str, int], total_count: int) -> tuple[str, ...]:
    """レベル分布から簡易的な注意点を返す。"""
    if total_count <= 0:
        return ("該当ログはありません。",)

    insights: list[str] = []
    error_count: int = sum(
        count
        for level, count in level_counts.items()
        if level.upper() in {"ERROR", "CRITICAL"}
    )
    warning_count: int = sum(
        count
        for level, count in level_counts.items()
        if level.upper() == "WARNING"
    )
    if error_count:
        insights.append(f"ERROR/CRITICAL が {error_count} 件あります。")
    if warning_count:
        insights.append(f"WARNING が {warning_count} 件あります。")
    if not insights:
        insights.append("重大レベルのログは目立ちません。")
    return tuple(insights)
