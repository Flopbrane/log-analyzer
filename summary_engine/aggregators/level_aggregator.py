# -*- coding: utf-8 -*-
"""ログデータのレベル情報を集計し、要約エンジンに提供するモジュール。
このモジュールは、ログデータからレベル情報を抽出し、その出現頻度や関連する情報を集計して、要約エンジンに提供する役割を担います。"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from summary_engine.aggregators.count_aggregator import count_by_field


def aggregate_levels(logs: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """level別件数を返す。"""
    return count_by_field(logs, "level")
