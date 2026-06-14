# -*- coding: utf-8 -*-
# pylint: disable=C0103
"""アプリ全体共通ロガー"""
from __future__ import annotations

from logs.log_paths import LOGS_DIR  # ← ここ重要
from logs.multi_info_logger import AppLogger, LogOutput

_logger: AppLogger | None = None


def get_logger() -> AppLogger:
    """アプリ全体で使用するロガー（遅延初期化）"""
    global _logger  # pylint: disable=global-statement

    if _logger is None:
        _logger = AppLogger(
            log_dir=LOGS_DIR,
            app_name="alarm",
            default_output=LogOutput.BOTH,
        )

    return _logger
