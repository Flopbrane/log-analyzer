# -*- coding: utf-8 -*-
"""
fv_engineで使用する型定義。

このモジュールは、*.fv ファイルの解析結果および
実行結果を表現するデータ型を提供する。

主な型:
    FVRecipe
        *.fv の解析結果

    FVResult
        *.fv の実行結果

このモジュールは型定義のみを担当し、
検索・要約・出力処理は行わない。
## 禁止事項
- 検索処理を実装しない
- 要約処理を実装しない
- Export処理を実装しない
- ファイルI/Oを行わない
- GUI処理を実装しない
このモジュールは型定義のみを担当する。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from summary_engine.summary_types import SummaryResult

__all__: list[str] = [
    "FVExportFormat",
    "FVSummaryMode",
    "FVRecipe",
    "FVResult",
]


class FVExportFormat(StrEnum):
    """出力形式"""
    NONE = "NONE"
    CSV = "CSV"
    JSON = "JSON"


class FVSummaryMode(StrEnum):
    """要約実行設定"""
    OFF = "OFF"
    ON = "ON"


@dataclass(frozen=True, slots=True)
class FVRecipe:
    """fvファイル解析結果"""
    title: str
    query: str
    summary: FVSummaryMode = FVSummaryMode.ON
    export: FVExportFormat = FVExportFormat.NONE


@dataclass(frozen=True, slots=True)
class FVResult:
    """fv実行結果"""
    recipe: FVRecipe
    matched_count: int
    summary: SummaryResult | None
    export_file_path: Path | None
