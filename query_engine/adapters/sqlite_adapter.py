"""SQLite-backed document adapter for large local datasets.

The adapter keeps query_engine independent from Logger/UI code. Callers pass
generic Document mappings, and SQLite stores each document as JSON plus a
flattened text column for full-text-ish LIKE searches.
"""
# cspell:ignore executemany
from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from query_engine.evaluators.sql import SqlCompileResult, compile_sql_where
from query_engine.models import Document, SearchResult
from query_engine.utils import flatten_text


@dataclass(frozen=True, slots=True)
class SQLiteSearchBatch:
    """Chunked search result returned by iter_search()."""

    offset: int
    results: tuple[SearchResult, ...]


class SQLiteDocumentStore:
    """Persist and search generic Query Engine Documents with SQLite."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection: sqlite3.Connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.create_function("REGEXP", 2, _regexp)
        self.initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteDocumentStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_text ON documents(text)"
        )
        self.connection.commit()

    def clear(self) -> None:
        self.connection.execute("DELETE FROM documents")
        self.connection.commit()

    def add_documents(self, documents: Iterable[Document], *, commit_every: int = 1000) -> int:
        count = 0
        rows: list[tuple[str, str]] = []
        for document in documents:
            rows.append((_document_text(document), _document_json(document)))
            count += 1
            if len(rows) >= commit_every:
                self._insert_rows(rows)
                rows.clear()
        if rows:
            self._insert_rows(rows)
        return count

    def search(self, query: str, *, limit: int | None = None) -> list[SearchResult]:
        sql, params = self._search_sql(query, limit=limit, offset=None)
        rows = self.connection.execute(sql, params).fetchall()
        return [_row_to_search_result(row) for row in rows]

    def iter_search(
        self,
        query: str,
        *,
        batch_size: int = 1000,
    ) -> Iterator[SQLiteSearchBatch]:
        offset = 0
        while True:
            sql, params = self._search_sql(query, limit=batch_size, offset=offset)
            rows = self.connection.execute(sql, params).fetchall()
            if not rows:
                break
            results = tuple(_row_to_search_result(row) for row in rows)
            yield SQLiteSearchBatch(offset=offset, results=results)
            offset += len(rows)

    def _insert_rows(self, rows: list[tuple[str, str]]) -> None:
        self.connection.executemany(
            "INSERT INTO documents(text, data) VALUES (?, ?)",
            rows,
        )
        self.connection.commit()

    def _search_sql(
        self,
        query: str,
        *,
        limit: int | None,
        offset: int | None,
    ) -> tuple[str, tuple[object, ...]]:
        compiled: SqlCompileResult = compile_sql_where(
            query,
            text_column="text",
            field_mapper=_json_field_mapper,
        )
        sql: str = f"SELECT data FROM documents WHERE {compiled.where_sql} ORDER BY id"
        params: list[object] = list(compiled.params)
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            sql += " OFFSET ?"
            params.append(offset)
        return sql, tuple(params)


def documents_to_sqlite(
    documents: Iterable[Document],
    path: str | Path,
    *,
    replace: bool = False,
) -> SQLiteDocumentStore:
    """Create a store and bulk-load documents."""
    store = SQLiteDocumentStore(path)
    if replace:
        store.clear()
    store.add_documents(documents)
    return store


def _document_text(document: Document) -> str:
    value = document.get("text")
    if isinstance(value, str) and value:
        return value
    return flatten_text(document)


def _document_json(document: Document) -> str:
    return json.dumps(dict(document), ensure_ascii=False, default=str)


def _row_to_search_result(row: sqlite3.Row) -> SearchResult:
    document = json.loads(str(row["data"]))
    return SearchResult(document=document)


def _json_field_mapper(field: str) -> str:
    path = "$." + ".".join(_json_path_part(part) for part in field.split("."))
    return f"json_extract(data, '{path}')"


def _json_path_part(part: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
        return part
    return json.dumps(part, ensure_ascii=False)


def _regexp(pattern: object, value: object) -> int:
    if pattern is None or value is None:
        return 0
    try:
        return 1 if re.search(str(pattern), str(value)) else 0
    except re.error:
        return 0
