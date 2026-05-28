"""解析済みクエリと検索結果の公開データ型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypeAlias

from query_engine.ast import QueryNode

Document: TypeAlias = Mapping[str, Any]
SortDirection: TypeAlias = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class QueryDocument:
    """Stable document schema used by adapters and evaluators."""

    id: str = ""
    title: str = ""
    text: str = ""
    source: str = ""
    fields: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_mapping(self) -> Document:
        """Return a backward-compatible mapping for existing evaluators."""
        fields = dict(self.fields)
        metadata = dict(self.metadata)
        return {
            **fields,
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "source": self.source,
            "fields": fields,
            "metadata": metadata,
        }


@dataclass(frozen=True, slots=True)
class SortSpec:
    field: str
    direction: SortDirection = "asc"


@dataclass(frozen=True, slots=True)
class SearchQuery:
    raw_text: str
    ast: QueryNode
    sort: SortSpec | None = None
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    document: Document
    score: float = 1.0
    highlights: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GrammarSpec:
    """ドキュメントとテストで共有する文法説明。"""

    name: str
    version: str
    rules: tuple[str, ...]
