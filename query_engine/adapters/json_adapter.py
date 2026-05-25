# -*- coding: utf-8 -*-
"""JSON/JSONLを検索しやすいdict/Documentへ変換するアダプタ。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from query_engine.adapters.tabular import Record, rows_to_documents
from query_engine.models import Document


class JsonAdapter:
    """JSON/JSONLファイルを、レコード単位で読み込む小さなアダプタ。"""

    def __init__(self, load_file_path: str | Path) -> None:
        self.load_file_path = Path(load_file_path)

    def load(self) -> list[Record]:
        suffix: str = self.load_file_path.suffix.lower()

        if suffix == ".jsonl":
            return self._load_jsonl()

        if suffix == ".json":
            return self._load_json()

        raise ValueError(f"Unsupported file: {suffix}")

    def documents(self) -> list[Document]:
        return json_to_documents(self.load_file_path)

    def _load_json(self) -> list[Record]:
        data: object = json.loads(self.load_file_path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            items = cast("list[object]", data)
            return [_coerce_record(item) for item in items]

        if isinstance(data, dict):
            record = cast(Record, data)
            rows = _find_embedded_rows(record)
            if rows is not None:
                return rows
            return [record]

        raise ValueError("Invalid JSON structure")

    def _load_jsonl(self) -> list[Record]:
        rows: list[Record] = []
        with self.load_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                rows.append(_coerce_record(json.loads(line)))

        return rows


def load_json(path: str | Path) -> list[Record]:
    """JSON/JSONLをlist[dict]へ変換する。"""
    return JsonAdapter(path).load()


def json_to_documents(path: str | Path) -> list[Document]:
    """JSON/JSONLの各レコードをQuery Engineで検索できるDocumentへ変換する。"""
    json_path = Path(path)
    return rows_to_documents(load_json(json_path), source=str(json_path), table=json_path.stem)


def _coerce_record(value: object) -> Record:
    if isinstance(value, dict):
        return cast(Record, value)
    return {"value": value}


def _find_embedded_rows(record: Record) -> list[Record] | None:
    for key in ("records", "rows", "items", "data"):
        value = record.get(key)
        if isinstance(value, list):
            items = cast("list[object]", value)
            return [_coerce_record(item) for item in items]
    return None
