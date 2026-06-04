# -*- coding: utf-8 -*-
"""WebサーバーApacheのログを処理するためのアダプター。
apache_adapter.pyは、Apacheのログを処理するためのアダプターです。
Apacheのログ形式は、一般的に「Common Log Format」や「Combined Log Format」と呼ばれる形式で記録されます。
このモジュールは、Apacheのログを解析し、必要な情報を抽出して、要約エンジンやUI層で利用できる形式に変換する役割を担います。 
また、将来的には、Apache以外のWebサーバーのログにも対応できるように、柔軟な設計を目指しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord

ACCESS_LOG_PATTERN: re.Pattern[str] = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+)'
)


def load_apache_records(path: Path) -> AdapterResult:
    """Apache Common/Combined風アクセスログをraw recordへ変換する。"""
    try:
        records: list[RawRecord] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            record: RawRecord | None = parse_access_log_line(line, line_no=line_no, source_format=FileAdapterFormat.APACHE.value)
            if record is not None:
                records.append(record)
        return AdapterResult(records=records, format_name=FileAdapterFormat.APACHE.value, success=bool(records))
    except Exception as exc:
        return AdapterResult(records=[], format_name=FileAdapterFormat.APACHE.value, success=False, error=str(exc))


def parse_access_log_line(line: str, *, line_no: int, source_format: str) -> RawRecord | None:
    match: re.Match[str] | None = ACCESS_LOG_PATTERN.match(line.strip())
    if match is None:
        return None

    status = int(match.group("status"))
    method: str | Any = match.group("method")
    request_path: str | Any = match.group("path")
    timestamp: str = _parse_apache_time(match.group("time"))
    return {
        "timestamp": timestamp,
        "level": "ERROR" if status >= 500 else "WARNING" if status >= 400 else "INFO",
        "module": "web",
        "event_id": f"{source_format}:{line_no}",
        "message": f"{method} {request_path} -> {status}",
        "ip": match.group("ip"),
        "method": method,
        "path": request_path,
        "protocol": match.group("protocol"),
        "status": status,
        "bytes": None if match.group("size") == "-" else int(match.group("size")),
        "source_format": source_format,
        "line_no": line_no,
    }


def _parse_apache_time(value: str) -> str:
    """Apache形式の日時をUTCのISO形式へ変換する。"""
    try:
        dt: datetime = datetime.strptime(value, "%d/%b/%Y:%H:%M:%S %z")
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return value
