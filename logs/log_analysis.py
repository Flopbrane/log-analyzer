# -*- coding: utf-8 -*-
"""ログ構造の判定入口。

正規化処理の本体はlog_normalizer.pyに置く。
このモジュールは既存importとの互換性を保つ薄い入口。
"""
from __future__ import annotations

from logs.log_normalizer import LogType, detect_log_type, normalize_external_log, normalize_log_record

__all__: list[str] = [
    "LogType",
    "detect_log_type",
    "normalize_external_log",
    "normalize_log_record",
]
