# -*- coding: utf-8 -*-
"""ファイルアダプタ層のコントローラー。
file_adapter_controller.pyは、ファイルアダプタ層のコントローラーです。
"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from pathlib import Path

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat
from file_adapter.apache_adapter import load_apache_records
from file_adapter.csv_adapter import load_csv_records
from file_adapter.json_adapter import load_json_records
from file_adapter.nginx_adapter import load_nginx_records
from file_adapter.py_traceback_adapter import load_py_traceback_records
from file_adapter.sqlite_adapter import load_sqlite_records


def load_records_by_adapter(path: Path) -> AdapterResult:
    """ファイル種別に応じたadapterでraw recordsを読み込む。"""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv_records(path)
    if suffix in {".sqlite", ".sqlite3", ".db"}:
        return load_sqlite_records(path)
    if suffix == ".json":
        return load_json_records(path)
    if suffix in {".traceback", ".tb"}:
        return load_py_traceback_records(path)

    text = _read_preview(path)
    if "Traceback (most recent call last):" in text:
        return load_py_traceback_records(path)

    web_result = load_nginx_records(path)
    if web_result.success:
        return web_result

    return AdapterResult(
        records=[],
        format_name=FileAdapterFormat.UNKNOWN.value,
        success=False,
        error=f"unsupported file format: {path.suffix}",
    )


def _read_preview(path: Path, size: int = 4096) -> str:
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore") as file:
            return file.read(size)
    except OSError:
        return ""
