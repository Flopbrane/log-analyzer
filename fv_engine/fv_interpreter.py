# -*- coding: utf-8 -*-
"""
FVRecipe を実行計画へ変換するモジュール。
fv_interpreter は Recipe の意味解釈を行い、
実行可能な ExecutionPlan を生成する。
このモジュールは検索や要約を実行しない。
入力:
    FVRecipe
出力:
    ExecutionPlan

## 禁止事項
- 検索を実行しない
- 要約を実行しない
- Exportを実行しない
- ファイルを読み込まない
- GUI処理を実装しない
このモジュールは FVRecipe を実行計画へ変換することのみを担当する。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from uuid import uuid4

from fv_engine.fv_plan import ExecutionPlan
from fv_engine.fv_types import FVExportFormat, FVRecipe, FVSummaryMode

__all__: list[str] = [
    "build_execution_plan",
]


def build_execution_plan(
    recipe: FVRecipe,
    *,
    source: str | None = None,
    output_file_path: str | None = None,
    execution_id: str | None = None,
) -> ExecutionPlan:
    """FVRecipeから実行計画を生成する。"""
    return ExecutionPlan(
        recipe=recipe,
        source=source,
        query=recipe.query,
        run_summary=recipe.summary is FVSummaryMode.ON,
        export_format=recipe.export,
        execution_id=execution_id or uuid4().hex,
        output_file_path=(
            None
            if recipe.export is FVExportFormat.NONE
            else output_file_path
        ),
    )
