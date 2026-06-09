# -*- coding: utf-8 -*-
"""
FVRecipe を実行するモジュール。
fv_runner は query_engine、
summary_engine、
result_exporter を呼び出し、
FVResult を生成する。
fv_runner 自身は検索ロジックや
要約ロジックを実装しない。
入力
    FVRecipe
出力
    FVResult

## 禁止事項
- 検索アルゴリズムを実装しない
- 要約アルゴリズムを実装しない
- Exportアルゴリズムを実装しない
- GUI処理を実装しない
- query_engineを改変しない
- summary_engineを改変しない
検索・要約・出力は既存エンジンへ委譲することのみを担当する。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

from fv_engine.fv_plan import ExecutionPlan
from fv_engine.fv_types import FVExportFormat, FVResult
from logs.log_types import LogDict
from logs.result_exporter import export_logs_to_csv, export_search_result_bundle
from query_engine.evaluators.memory import search
from query_engine.models import SearchResult
from summary_engine.summary_engine import summarize_logs
from summary_engine.summary_types import LogSummaryDict, SummaryResult

__all__: list[str] = [
    "run_execution_plan",
]


def run_execution_plan(
    plan: ExecutionPlan,
    documents: Iterable[Mapping[str, Any]],
    *,
    timezone: str = "UTC",
) -> FVResult:
    """実行計画を既存エンジンへ委譲し、FVResultを返す。"""
    query_results: list[SearchResult] = search(
        plan.query,
        documents,
    )
    matched_logs: list[LogDict] = [
        cast(LogDict, result.document)
        for result in query_results
    ]

    summary: SummaryResult | None = None
    if plan.run_summary:
        summary = summarize_logs(
            cast(Iterable[LogSummaryDict], matched_logs),
            condition_text=plan.query,
            timezone=timezone,
            metadata={"fv_title": plan.recipe.title, "execution_id": plan.execution_id},
        )

    export_file_path: Path | None = _export_result(plan, matched_logs, summary)
    return FVResult(
        recipe=plan.recipe,
        matched_count=len(matched_logs),
        summary=summary,
        export_file_path=export_file_path,
    )


def _export_result(
    plan: ExecutionPlan,
    logs: Iterable[LogDict],
    summary: SummaryResult | None,
) -> Path | None:
    if plan.export_format is FVExportFormat.NONE:
        return None
    if plan.export_format is FVExportFormat.CSV:
        return export_logs_to_csv(logs, plan.output_file_path)
    if plan.export_format is FVExportFormat.JSON:
        return export_search_result_bundle(
            logs=logs,
            summary=summary,
            save_file_path=plan.output_file_path,
        )
    raise ValueError(f"未対応のEXPORT形式です: {plan.export_format}")
