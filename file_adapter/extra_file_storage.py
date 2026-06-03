# -*- coding: utf-8 -*-
"""log_storage.pyが
読み込めなかったfile形式の各種fileを読み込むためのモジュール。
file_adapter/extra_file_storage.pyは、
log_storage.pyが対応していないファイル形式を読み込むfile。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from pathlib import Path

from file_adapter.adapter_types import AdapterResult
from file_adapter.file_adapter_controller import load_records_by_adapter


def load_extra_records(path: Path) -> AdapterResult:
    """log_storage.pyの標準JSONL読込で扱えないファイルを読み込む。"""
    return load_records_by_adapter(path)
