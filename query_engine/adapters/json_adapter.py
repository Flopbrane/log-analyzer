# -*- coding: utf-8 -*-
"""JSON/JSONLを検索しやすいdict/Documentへ変換するアダプタ。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Iterator, cast

from query_engine.adapters.base import normalize_document
from query_engine.adapters.tabular import Record
from query_engine.models import Document


@dataclass(frozen=True, slots=True)
class DocumentLoadIssue:
    """Non-fatal adapter issue found while streaming input."""

    source: str
    line_number: int | None
    message: str


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

    def iter_documents(self) -> Iterator[Document]:
        yield from iter_json_documents(self.load_file_path)

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


def iter_json_records(
    path: str | Path,
    *,
    issues: list[DocumentLoadIssue] | None = None,
    encoding: str = "utf-8",
) -> Iterator[Record]:
    """Stream JSON/JSONL records, skipping broken JSONL lines."""
    json_path = Path(path)
    if json_path.suffix.lower() != ".jsonl":
        for record in load_json(json_path):
            yield record
        return

    with json_path.open("r", encoding=encoding, errors="replace") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield _coerce_record(json.loads(stripped))
            except JSONDecodeError as exc:
                if issues is not None:
                    issues.append(
                        DocumentLoadIssue(
                            source=str(json_path),
                            line_number=line_number,
                            message=str(exc),
                        )
                    )


def iter_json_documents(
    path: str | Path,
    *,
    issues: list[DocumentLoadIssue] | None = None,
    encoding: str = "utf-8",
) -> Iterator[Document]:
    """Stream normalized documents from JSON/JSONL."""
    json_path = Path(path)
    for row_number, record in enumerate(
        iter_json_records(json_path, issues=issues, encoding=encoding),
        start=1,
    ):
        yield normalize_document(
            record,
            id=f"{json_path}:{row_number}",
            source=str(json_path),
            metadata={
                "source": str(json_path),
                "row_number": row_number,
                "format": json_path.suffix.lower().lstrip("."),
            },
        ).to_mapping()


def load_json(path: str | Path) -> list[Record]:
    """JSON/JSONLをlist[dict]へ変換する。"""
    return JsonAdapter(path).load()


def json_to_documents(path: str | Path) -> list[Document]:
    """JSON/JSONLの各レコードをQuery Engineで検索できるDocumentへ変換する。"""
    return list(iter_json_documents(path))


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
