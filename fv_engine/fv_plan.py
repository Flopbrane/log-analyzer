# -*- coding: utf-8 -*-
"""
fv実行計画。

fv_interpreter が生成し、
fv_runner が実行する。

このクラスは
FVRecipe を実行可能な形式へ
変換した結果を保持する。

禁止事項:
- 検索処理を実装しない
- 要約処理を実装しない
- Export処理を実装しない
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from dataclasses import dataclass

from fv_engine.fv_types import (
    FVExportFormat,
    FVRecipe,
)


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """fv実行計画"""
    recipe: FVRecipe
    source: str | None
    query: str
    run_summary: bool
    export_format: FVExportFormat
    execution_id: str
    output_file_path: str | None
