# -*- coding: utf-8 -*-
"""
fv_engine の実行結果型。
FVResult に関連する補助型や
結果整形処理を提供する。
## 禁止事項
- 検索処理を実装しない
- 要約処理を実装しない
- Export処理を実装しない
- ファイルI/Oを行わない
- GUI処理を実装しない
このモジュールは実行結果の表現のみを担当する。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from fv_engine.fv_types import FVResult

__all__: list[str] = [
    "FVResult",
    "format_fv_result",
]


def format_fv_result(result: FVResult) -> str:
    """FVResultを表示用の短いテキストへ整形する。"""
    lines: list[str] = [
        f"TITLE: {result.recipe.title}",
        f"MATCHED: {result.matched_count}",
    ]
    if result.summary is not None:
        lines.append(result.summary.text)
    if result.export_file_path is not None:
        lines.append(f"EXPORT: {result.export_file_path}")
    return "\n".join(lines)
