# -*- coding: utf-8 -*-
"""NGINXログファイルを処理するためのアダプター。
nginx_adapter.pyは、NGINXのログを処理するためのアダプターです。
このモジュールは、NGINXのログを解析し、必要な情報を抽出して、
要約エンジンやUI層で利用できる形式に変換する役割を担います。
また、将来的には、他の形式のログにも対応できるように、柔軟な設計を目指しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from pathlib import Path

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord
from file_adapter.apache_adapter import parse_access_log_line


def load_nginx_records(path: Path) -> AdapterResult:
    """Nginx標準access_log風の行をraw recordへ変換する。"""
    try:
        records: list[RawRecord] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            record: RawRecord | None = parse_access_log_line(line, line_no=line_no, source_format=FileAdapterFormat.NGINX.value)
            if record is not None:
                records.append(record)
        return AdapterResult(records=records, format_name=FileAdapterFormat.NGINX.value, success=bool(records))
    except Exception as exc:
        return AdapterResult(records=[], format_name=FileAdapterFormat.NGINX.value, success=False, error=str(exc))
