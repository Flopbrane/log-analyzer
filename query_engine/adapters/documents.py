"""一般文書を検索対象のDocumentへ変換するアダプタ。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Mapping

from query_engine.adapters.base import normalize_document
from query_engine.models import Document

WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class TextDocument:
    """検索対象にする一般文書の標準形。"""

    text: str
    title: str = ""
    source: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_document(self) -> Document:
        """評価器へ渡せる辞書形式へ変換する。"""
        return normalize_document(
            {},
            title=self.title,
            text=self.text,
            source=self.source,
            metadata=self.metadata,
        ).to_mapping()


def normalize_text(text: str) -> str:
    """検索前の文章を最小限だけ正規化する。"""
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def from_text(text: str, *, title: str = "", source: str = "", **metadata: Any) -> TextDocument:
    """文字列からTextDocumentを作成する。"""
    return TextDocument(
        text=normalize_text(text),
        title=title,
        source=source,
        metadata=metadata,
    )


def from_text_file(path: str | Path, *, encoding: str = "utf-8", **metadata: Any) -> TextDocument:
    """テキストファイルを読み込み、TextDocumentへ変換する。"""
    file_path = Path(path)
    return from_text(
        file_path.read_text(encoding=encoding),
        title=file_path.stem,
        source=str(file_path),
        **metadata,
    )
