# -*- coding: utf-8 -*-
"""要約エンジンの実装。
summary_bridge.pyからのデータを受け取り、
このフォルダ内の各モジュールを使用して、
ログデータの条件別統計を作成し、
人間が理解しやすい要約を提供することを目的としています。"""
#########################
# Author: F.Kurokawa
# Description:
#　要約エンジンは、このフォルダ内の各モジュールを使用して、ログデータの条件別統計を作成し、
# 人間が理解しやすい要約をsummary_bridgeを通じてUIデータ提供します。
#　このモジュールは、要約エンジンのコアロジックを実装し、将来的には外部の要約アルゴリズムや機械学習モデルと統合できるように設計されています。
#########################

from __future__ import annotations

from typing import Any, Iterable, Mapping

from summary_engine.aggregators.context_aggregator import aggregate_numeric_context
from summary_engine.aggregators.level_aggregator import aggregate_levels
from summary_engine.aggregators.message_aggregator import aggregate_messages
from summary_engine.aggregators.module_aggregator import aggregate_modules
from summary_engine.analyzers.anomaly_analyzer import detect_level_anomalies
from summary_engine.summaries.text_summary import build_text_summary
from summary_engine.summary_types import (
    LogSummaryDict,
    NumericStats,
    RankingItem,
    SummaryRequest,
    SummaryResult,
)


def summarize_logs(
    logs: Iterable[LogSummaryDict],
    condition_text: str = "",
    timezone: str = "UTC",
    metadata: Mapping[str, Any] | None = None,
) -> SummaryResult:
    """ログ列と検索条件から条件別統計の要約を生成する。"""
    request = SummaryRequest(
        logs=tuple(logs),
        condition_text=condition_text,
        timezone=timezone,
        metadata={} if metadata is None else metadata,
    )
    return summarize_request(request)


def summarize_request(request: SummaryRequest) -> SummaryResult:
    """SummaryRequestを処理し、UI非依存のSummaryResultを返す。"""
    logs: tuple[LogSummaryDict, ...] = request.logs
    total_count: int = len(logs)
    level_counts: dict[str, int] = aggregate_levels(logs)
    module_ranking: tuple[RankingItem, ...] = aggregate_modules(logs)
    message_ranking: tuple[RankingItem, ...] = aggregate_messages(logs)
    context_numeric_stats: dict[str, NumericStats] = aggregate_numeric_context(logs)
    insights: tuple[str, ...] = detect_level_anomalies(level_counts, total_count)
    text: str = build_text_summary(
        total_count=total_count,
        condition_text=request.condition_text,
        level_counts=level_counts,
        module_ranking=module_ranking,
        message_ranking=message_ranking,
        context_numeric_stats=context_numeric_stats,
        insights=insights,
    )
    return SummaryResult(
        total_count=total_count,
        condition_text=request.condition_text,
        level_counts=level_counts,
        module_ranking=module_ranking,
        message_ranking=message_ranking,
        context_numeric_stats=context_numeric_stats,
        insights=insights,
        text=text,
    )
