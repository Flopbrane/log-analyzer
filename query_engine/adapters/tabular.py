"""表形式データを検索対象Documentへ寄せる共通処理。"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from query_engine.adapters.base import normalize_document
from query_engine.models import Document

Record = dict[str, Any]


def row_to_document(
    row: Mapping[str, Any],
    *,
    source: str = "",
    table: str = "",
    row_number: int | None = None,
) -> Document:
    """1行分のデータを、フィールド検索と全文検索の両方に使えるDocumentへ変換する。"""
    record: Record = dict(row)
    metadata: Record = {
        "source": source,
        "table": table,
        "row_number": row_number,
        "columns": list(record.keys()),
    }
    return normalize_document(
        record,
        id=_make_id(source=source, table=table, row_number=row_number),
        title=_make_title(record, row_number=row_number),
        source=source,
        metadata=metadata,
    ).to_mapping()


def rows_to_documents(
    rows: Iterable[Mapping[str, Any]],
    *,
    source: str = "",
    table: str = "",
    start_row: int = 1,
) -> list[Document]:
    """複数行のデータを検索対象Documentのリストへ変換する。"""
    return [
        row_to_document(row, source=source, table=table, row_number=index)
        for index, row in enumerate(rows, start=start_row)
    ]


def _make_title(row: Mapping[str, Any], *, row_number: int | None) -> str:
    for value in row.values():
        if value not in (None, ""):
            return str(value)[:80]
    if row_number is None:
        return ""
    return f"row {row_number}"


def _make_id(*, source: str, table: str, row_number: int | None) -> str:
    parts: list[str] = [part for part in (source, table, str(row_number) if row_number is not None else "") if part]
    return ":".join(parts)
