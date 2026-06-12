# -*- coding: utf-8 -*-
"""fv_fileの出入り口"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from pathlib import Path

from fv_engine.fv_plan import ExecutionPlan

__all__: list[str] = [
    "run_fv_file",
    ]

from fv_engine.fv_interpreter import build_execution_plan
from fv_engine.fv_parser import parse_fv_text
from fv_engine.fv_runner import run_execution_plan
from fv_engine.fv_types import FVRecipe, FVResult


def run_fv_file(
    file_path: Path,
    rows: list[dict[str, object]],
    timezone: str,
) -> FVResult:
    """FVレシピファイルを実行する。"""
    recipe_text: str = file_path.read_text(encoding="utf-8")
    recipe: FVRecipe = parse_fv_text(recipe_text)
    plan: ExecutionPlan = build_execution_plan(recipe)
    return run_execution_plan(
        plan,
        rows,
        timezone=timezone,
    )
