# -*- coding: utf-8 -*-
"""時間集計モジュール
time_aggregator.pyは、ログデータの時間情報を集計し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータの条件別統計を作成し、人間が理解しやすい要約を生成するための基盤を提供します。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any, Literal

from summary_engine.analyzers.ranking_analyzer import top_items
from summary_engine.summary_types import RankingItem

TimeBucket = Literal["hour", "date"]


def aggregate_times(
    logs: Iterable[Mapping[str, Any]],
    bucket: TimeBucket = "hour",
    limit: int = 24,
) -> tuple[RankingItem, ...]:
    """time別の件数を集計する。bucket='hour'なら時間単位、'date'なら日単位。"""
    counts: Counter[str] = Counter()
    for log in logs:
        raw_time: object = log.get("time") or log.get("timestamp")
        label: str | None = _bucket_label(raw_time, bucket)
        if label is not None:
            counts[label] += 1
    return top_items(dict(counts), limit=limit)


def aggregate_dates(logs: Iterable[Mapping[str, Any]], limit: int = 31) -> tuple[RankingItem, ...]:
    """日付別の件数を集計する。"""
    return aggregate_times(logs, bucket="date", limit=limit)


def aggregate_hours(logs: Iterable[Mapping[str, Any]], limit: int = 24) -> tuple[RankingItem, ...]:
    """時間別の件数を集計する。"""
    return aggregate_times(logs, bucket="hour", limit=limit)


def _bucket_label(raw_time: object, bucket: TimeBucket) -> str | None:
    if not isinstance(raw_time, str) or not raw_time:
        return None
    try:
        dt = datetime.fromisoformat(raw_time)
    except ValueError:
        return raw_time[:10] if bucket == "date" and len(raw_time) >= 10 else None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if bucket == "date":
        return dt.date().isoformat()
    return dt.replace(minute=0, second=0, microsecond=0).isoformat()
