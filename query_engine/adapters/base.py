"""アダプタプロトコルおよびドキュメント正規化ヘルパーを共有する。"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Mapping, Protocol, cast, runtime_checkable

from query_engine.models import Document, QueryDocument
from query_engine.utils import flatten_text


@runtime_checkable
class DocumentAdapter(Protocol):
    """Query Engineのドキュメントを公開するアダプタの共通API。"""

    def documents(self) -> Iterable[Document]:
        """ドキュメントを返すまたはストリームする。"""
        ...


def normalize_document(
    value: Mapping[str, Any] | QueryDocument,
    *,
    id: str = "",
    title: str = "",
    text: str = "",
    source: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> QueryDocument:
    """任意のマッピングを安定したQueryDocumentスキーマに変換する。"""
    if isinstance(value, QueryDocument):
        return value

    fields: dict[str, Any] = dict(value)
    doc_id = str(fields.pop("id", id) or "")
    doc_title = str(fields.pop("title", title) or "")
    doc_text = str(fields.pop("text", text) or "")
    doc_source = str(fields.pop("source", source) or "")
    merged_metadata: dict[str, Any] = {}
    existing_metadata: object = fields.pop("metadata", {})
    if isinstance(existing_metadata, Mapping):
        metadata_mapping: Mapping[str, Any] = cast(
            Mapping[str, Any],
            existing_metadata,
        )
        merged_metadata.update(dict(metadata_mapping))
    existing_metadata: object = fields.pop("metadata", {})
    if metadata is not None:
        merged_metadata.update(dict(metadata))
    if not doc_text:
        doc_text: str = flatten_text(fields)
    if not doc_title:
        doc_title: str = _first_non_empty_text(fields)
    return QueryDocument(
        id=doc_id,
        title=doc_title[:120],
        text=doc_text,
        source=doc_source,
        fields=fields,
        metadata=merged_metadata,
    )


def iter_document_mappings(
    documents: Iterable[Mapping[str, Any] | QueryDocument],
) -> Iterator[Document]:
    """正規化されたドキュメントから後方互換のマッピングを生成する。"""
    for document in documents:
        yield normalize_document(document).to_mapping()


def _first_non_empty_text(fields: Mapping[str, Any]) -> str:
    """フィールドの中から最初の非空テキストを返す。"""
    for value in fields.values():
        if value not in (None, ""):
            return str(value)
    return ""
