# -*- coding: utf-8 -*-
"""JSONファイルを処理するためのアダプター。
json_adapter.pyは、JSONファイルを読み書きするためのアダプターです。
このモジュールは、JSONファイルを解析し、必要な情報を抽出して、
要約エンジンやUI層で利用できる形式に変換する役割を担います。
また、将来的には、他の形式のファイルにも対応できるように、柔軟な設計を目指しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord


def load_json_records(path: Path) -> AdapterResult:
    """JSON/JSONLをraw recordとして読み込む。"""
    try:
        text = path.read_text(encoding="utf-8-sig")
        stripped = text.strip()
        if not stripped:
            return AdapterResult(records=[], format_name=FileAdapterFormat.JSON.value, success=True)

        if stripped.startswith("[") or stripped.startswith("{"):
            value: Any = json.loads(stripped)
            records = _records_from_json_value(value)
        else:
            records = [json.loads(line) for line in text.splitlines() if line.strip()]

        return AdapterResult(records=records, format_name=FileAdapterFormat.JSON.value, success=True)
    except Exception as exc:
        return AdapterResult(records=[], format_name=FileAdapterFormat.JSON.value, success=False, error=str(exc))


def _records_from_json_value(value: Any) -> list[RawRecord]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        records_value: Any = value.get("records")
        if isinstance(records_value, list):
            return [item for item in records_value if isinstance(item, dict)]
        return [value]
    return []
