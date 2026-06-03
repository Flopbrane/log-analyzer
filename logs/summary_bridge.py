# -*- coding: utf-8 -*-
"""要約層との橋渡し。
summary_bridge.pyは、要約層とのデータのやり取りを行います。
必ず、ここを通らないと、要約層にアクセスできないようにしてください。
このモジュールは、要約エンジンとUI層の間のインターフェースを提供し、将来的には要約エンジンの実装を変更しても、UI層に影響を与えないように設計されています。"""
#########################
# Author: F.Kurokawa
# Description:
# 要約層との橋渡し。
#########################
from __future__ import annotations

from collections.abc import Mapping
from datetime import tzinfo
from typing import Any, Iterable, cast

from logs.log_types import LogDict
from summary_engine.summary_engine import summarize_logs
from summary_engine.summary_types import LogSummaryDict, SummaryResult


def summarize_logs_for_viewer(
    logs: Iterable[LogDict],
    condition_text: str,
    tz: str | tzinfo,
) -> SummaryResult:
    """Viewerの検索結果を要約エンジンへ渡し、表示用要約を返す。"""
    return summarize_logs(
        logs=(_to_summary_log(log) for log in logs),
        condition_text=condition_text,
        timezone=str(tz),
    )


def summarize_text_for_viewer(
    logs: Iterable[LogDict],
    condition_text: str,
    tz: str | tzinfo,
) -> str:
    """Viewerがそのまま表示できる要約文字列を返す。"""
    return summarize_logs_for_viewer(logs, condition_text, tz).text


def _to_summary_log(log: LogDict) -> LogSummaryDict:
    """logs層のLogDictをsummary_engine用の入力形へ変換する。"""
    where: Mapping[str, Any] = cast(Mapping[str, Any], log.get("where", {}))
    what: Mapping[str, Any] = cast(Mapping[str, Any], log.get("what", {}))
    context: Mapping[str, Any] = cast(Mapping[str, Any], log.get("context", {}))
    return {
        "level": str(log.get("level", "")),
        "time": str(log.get("time", "")),
        "trace_id": str(log.get("trace_id", "")),
        "where": dict(where),
        "what": dict(what),
        "context": dict(context),
        "output": str(log.get("output", "")),
    }
