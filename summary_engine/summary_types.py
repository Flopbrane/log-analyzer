# -*- coding: utf-8 -*-
"""
要約層で使用する型定義をまとめたモジュール。
これらの型定義は、要約エンジンや要約ブリッジなど、要約層の各コンポーネントで共通して使用されます。"""
#########################
# Author: F.Kurokawa
# Description:
# 要約層で使用する型定義をまとめたモジュール。
# これらの型定義は、要約エンジンや要約ブリッジなど、要約層の各コンポーネントで共通して使用されます。
#########################

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, TypedDict, cast


class LogSummaryDict(TypedDict, total=False):
    level: str
    time: str
    trace_id: str
    where: Mapping[str, Any]
    what: Mapping[str, Any]
    context: Mapping[str, Any]
    output: str


@dataclass(frozen=True, slots=True)
class SummaryRequest:
    """要約エンジンへ渡す、UI非依存の入力データ。"""

    logs: tuple[LogSummaryDict, ...]
    condition_text: str = ""
    timezone: str = "UTC"
    metadata: Mapping[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


@dataclass(frozen=True, slots=True)
class RankingItem:
    """ランキング形式で返す集計項目。"""

    key: str
    count: int


@dataclass(frozen=True, slots=True)
class NumericStats:
    """数値フィールドの基本統計。"""

    field: str
    count: int
    minimum: float
    maximum: float
    average: float
    median: float


@dataclass(frozen=True, slots=True)
class SummaryResult:
    """要約エンジンからbridgeへ返す結果。"""

    total_count: int
    condition_text: str
    level_counts: Mapping[str, int]
    module_ranking: tuple[RankingItem, ...]
    message_ranking: tuple[RankingItem, ...]
    context_numeric_stats: Mapping[str, NumericStats]
    insights: tuple[str, ...]
    text: str
