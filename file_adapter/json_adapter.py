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
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord


def load_json_records(path: Path) -> AdapterResult:
    """JSON/JSONLをraw recordとして読み込む。"""
    try:
        text: str = path.read_text(encoding="utf-8-sig")
        stripped: str = text.strip()

        if not stripped:
            return AdapterResult(
                records=[],
                format_name=FileAdapterFormat.JSON.value,
                success=True,
            )

        records: list[RawRecord]

        if stripped.startswith("[") or stripped.startswith("{"):
            value: object = json.loads(stripped)
            records = _records_from_json_value(value)
        else:
            records = _records_from_jsonl_text(text)

        return AdapterResult(
            records=records,
            format_name=FileAdapterFormat.JSON.value,
            success=True,
        )

    except Exception as exc:
        return AdapterResult(
            records=[],
            format_name=FileAdapterFormat.JSON.value,
            success=False,
            error=str(exc),
        )


def _records_from_jsonl_text(text: str) -> list[RawRecord]:
    """JSONL文字列をRawRecordのlistへ変換する。"""
    records: list[RawRecord] = []

    for line in text.splitlines():
        if not line.strip():
            continue

        value: object = json.loads(line)

        if isinstance(value, dict):
            records.append(cast(RawRecord, value))

    return records


def _records_from_json_value(value: object) -> list[RawRecord]:
    """JSON値をRawRecordのlistへ変換する。"""
    if isinstance(value, list):
        values: list[object] = cast(list[object], value)
        return _records_from_list(values)

    if isinstance(value, dict):
        raw_value: RawRecord = cast(RawRecord, value)
        records_value: object = raw_value.get("records")

        if isinstance(records_value, list):
            values = cast(list[object], records_value)
            return _records_from_list(values)

        return [raw_value]

    return []


def _records_from_list(values: Iterable[object]) -> list[RawRecord]:
    """list内のdict要素だけをRawRecordとして取り出す。"""
    records: list[RawRecord] = []

    for item in values:
        if isinstance(item, dict):
            records.append(cast(RawRecord, item))

    return records