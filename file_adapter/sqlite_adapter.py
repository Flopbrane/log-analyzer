# -*- coding: utf-8 -*-
"""SQLiteデータベースを処理するためのアダプター。
sqlite_adapter.pyは、SQLiteデータベースを処理するためのアダプターです。
このモジュールは、SQLiteデータベースを操作し、必要な情報を抽出して、
要約エンジンやUI層で利用できる形式に変換する役割を担います。
また、将来的には、他の形式のデータベースにも対応できるように、柔軟な設計を目指しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord


def load_sqlite_records(path: Path) -> AdapterResult:
    """SQLiteのlogsテーブル、または最初のユーザーテーブルをraw recordへ変換する。"""
    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            table: str | None = _select_table(conn)
            if table is None:
                return AdapterResult(records=[], format_name=FileAdapterFormat.SQLITE.value, success=False, error="no table")
            rows: list[Any] = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            records: list[RawRecord] = []
            for row_no, row in enumerate(rows, start=1):
                record: RawRecord = dict(row)
                record.setdefault("event_id", f"sqlite:{table}:{row_no}")
                record.setdefault("source_format", FileAdapterFormat.SQLITE.value)
                record.setdefault("row_no", row_no)
                records.append(record)
        return AdapterResult(records=records, format_name=FileAdapterFormat.SQLITE.value, success=True)
    except Exception as exc:
        return AdapterResult(records=[], format_name=FileAdapterFormat.SQLITE.value, success=False, error=str(exc))


def _select_table(conn: sqlite3.Connection) -> str | None:
    rows: list[Any] = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    names: list[str] = [str(row[0]) for row in rows]
    if "logs" in names:
        return "logs"
    return names[0] if names else None
