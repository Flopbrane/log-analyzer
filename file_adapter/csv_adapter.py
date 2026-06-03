# -*- coding: utf-8 -*-
"""CSVファイルを処理するためのアダプター。
csv_adapter.pyは、CSVファイルを読み書きするためのアダプターです。
このモジュールは、CSVファイルを解析し、必要な情報を抽出して、
要約エンジンやUI層で利用できる形式に変換する役割を担います。
また、将来的には、他の形式のファイルにも対応できるように、柔軟な設計を目指しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import csv
from pathlib import Path

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord


def load_csv_records(path: Path) -> AdapterResult:
    """CSVを1行1dictのraw recordとして読み込む。"""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            records: list[RawRecord] = []
            for row_no, row in enumerate(reader, start=1):
                record = dict(row)
                record.setdefault("event_id", f"csv:{path.name}:{row_no}")
                record.setdefault("source_format", FileAdapterFormat.CSV.value)
                record.setdefault("line_no", row_no)
                records.append(record)
        return AdapterResult(records=records, format_name=FileAdapterFormat.CSV.value, success=True)
    except Exception as exc:
        return AdapterResult(records=[], format_name=FileAdapterFormat.CSV.value, success=False, error=str(exc))
