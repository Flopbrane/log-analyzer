"""解析済みクエリと検索結果の公開データ型。"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from query_engine.ast import QueryNode

JsonObject: TypeAlias = Mapping[str, Any]
JsonDocument: TypeAlias = JsonObject  # ドメイン意味のない任意のドキュメントを表すための型エイリアス
Document: TypeAlias = JsonDocument
SortDirection: TypeAlias = Literal["asc", "desc"]

def _empty_mapping() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True)
class QueryDocument:
    """アダプタと評価器が使用する安定したドキュメントスキーマ。"""

    id: str = ""
    title: str = ""
    text: str = ""
    source: str = ""
    fields: Mapping[str, Any] = field(default_factory=_empty_mapping)  # 型定義上はMappingだが、実装上はdictを想定
    metadata: Mapping[str, Any] = field(default_factory=_empty_mapping)

    def to_mapping(self) -> JsonDocument:
        """既存の評価器との互換性のためにマッピングを返す。"""
        fields: dict[str, Any] = dict(self.fields)
        metadata: dict[str, Any] = dict(self.metadata)
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
    """ソート仕様。"""
    field: str
    direction: SortDirection = "asc"


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """検索クエリ。"""
    raw_text: str
    ast: QueryNode
    sort: SortSpec | None = None
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    """検索結果。"""
    document: JsonDocument
    score: float = 1.0
    highlights: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GrammarSpec:
    """ドキュメントとテストで共有する文法説明。"""
    name: str
    version: str
    rules: tuple[str, ...]
