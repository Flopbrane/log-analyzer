# -*- coding: utf-8 -*-
# pylint: disable=W0718
"""Logの入出力を纏めて行う"""
#########################
# Author: F.Kurokawa
# Description:
# ログの保存・読み込みを行うモジュール
#########################
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from file_adapter.adapter_types import AdapterResult
from file_adapter.defender_adapter import adapt_defender_records
from file_adapter.extra_file_storage import load_extra_records


__all__: list[str] = [
    "load_log",
    "load_multi_logs",
    "save_log",
]



def load_log(log_path: Path) -> list[dict[str, Any]]:
    """ログファイルを読み込む"""
    log_entries: list[dict[str, Any]] | None = _load_json_lines(log_path)
    if log_entries is not None:
        return adapt_defender_records(log_path, log_entries)

    result: AdapterResult = load_extra_records(log_path)
    if result.success:
        return adapt_defender_records(log_path, result.records)

    print(f"Failed to load log file {log_path}: {result.error}")
    return []


def _load_json_lines(log_path: Path) -> list[dict[str, Any]] | None:
    """従来形式のJSONLを読み込む。失敗時はfallbackのためNoneを返す。"""
    log_entries: list[dict[str, Any]] = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                value: Any = json.loads(line)
                if not isinstance(value, dict):
                    return None
                log_entries.append(cast(dict[str, Any], value))
    except Exception:
        return None
    return log_entries


def load_multi_logs(log_paths: list[Path]) -> list[dict[str, Any]]:
    """複数のログファイルを読み込み、時系列でソートして返す"""
    all_logs: list[dict[str, Any]] = []
    for path in log_paths:
        logs: list[dict[str, Any]] = load_log(path)
        all_logs.extend(logs)

    # 🔥 時系列ソート
    all_logs.sort(key=lambda x: str(x.get("time") or x.get("timestamp") or ""))
    return all_logs


def save_log(log_path: Path, log_entry: dict[str, Any]) -> None:
    """ログエントリをファイルに保存する"""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to save log entry to {log_path}: {e}")
