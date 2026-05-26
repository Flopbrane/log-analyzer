"""検索対象をQuery EngineのDocumentへ変換するアダプタ群。"""
from __future__ import annotations

from query_engine.adapters.documents import TextDocument, from_text, from_text_file, normalize_text
from query_engine.adapters.extractors import extract_text_file
from query_engine.adapters.json_adapter import JsonAdapter, json_to_documents, load_json
from query_engine.adapters.logs import log_to_document
from query_engine.adapters.sqlite_adapter import (
    SQLiteDocumentStore,
    SQLiteSearchBatch,
    documents_to_sqlite,
)
from query_engine.adapters.tabular import Record, row_to_document, rows_to_documents
from query_engine.adapters.text_table_adapter import (
    CsvAdapter,
    TextTableAdapter,
    csv_to_documents,
    load_csv,
    load_text_table,
    text_table_to_documents,
)

__all__: list[str] = [
    "CsvAdapter",
    "JsonAdapter",
    "Record",
    "SQLiteDocumentStore",
    "SQLiteSearchBatch",
    "TextDocument",
    "TextTableAdapter",
    "csv_to_documents",
    "extract_text_file",
    "from_text",
    "from_text_file",
    "json_to_documents",
    "load_csv",
    "load_json",
    "load_text_table",
    "log_to_document",
    "normalize_text",
    "row_to_document",
    "rows_to_documents",
    "documents_to_sqlite",
    "text_table_to_documents",
]
