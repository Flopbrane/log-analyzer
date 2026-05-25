"""区切り文字/固定幅風のテキスト表をdict/Documentへ変換するアダプタ。"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, cast

from query_engine.adapters.tabular import Record, rows_to_documents
from query_engine.models import Document

Delimiter = Literal[",", "\t", ";", "|"]


class TextTableAdapter:
    """CSV/TSV/セミコロン/パイプ/固定幅スペース表を行ごとのdictとして読み込む。"""

    def __init__(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8-sig",
        delimiter: Delimiter | None = None,
    ) -> None:
        self.path = Path(path)
        self.encoding: str = encoding
        self.delimiter: None | Literal[','] | Literal['\t'] | Literal[';'] | Literal['|'] = delimiter

    def load(self) -> list[Record]:
        return load_text_table(self.path, encoding=self.encoding, delimiter=self.delimiter)

    def documents(self) -> list[Document]:
        return text_table_to_documents(self.path, encoding=self.encoding, delimiter=self.delimiter)


def load_text_table(
    path: str | Path,
    *,
    encoding: str = "utf-8-sig",
    delimiter: Delimiter | None = None,
) -> list[Record]:
    """表形式テキストを読み込む。

    delimiter=None のときは CSV Sniffer で `,`, TAB, `;`, `|` を優先検出し、
    見つからない場合は複数スペースで揃った固定幅風の表として扱います。
    """
    table_path = Path(path)

    with table_path.open("r", encoding=encoding, newline="") as file:
        sample = file.read(4096)
        file.seek(0)

        detected_delimiter: None | Literal[','] | Literal['\t'] | Literal[';'] | Literal['|'] = delimiter or _detect_delimiter(sample)
        if detected_delimiter is None:
            return _load_space_aligned_table(file.readlines())

        reader = csv.DictReader(file, delimiter=detected_delimiter)
        return [{str(key): value for key, value in row.items()} for row in reader]


def text_table_to_documents(
    path: str | Path,
    *,
    encoding: str = "utf-8-sig",
    delimiter: Delimiter | None = None,
) -> list[Document]:
    """表形式テキストの各行をQuery Engineで検索できるDocumentへ変換する。"""
    table_path = Path(path)
    return rows_to_documents(
        load_text_table(table_path, encoding=encoding, delimiter=delimiter),
        source=str(table_path),
        table=table_path.stem,
    )


def _detect_delimiter(sample: str) -> Delimiter | None:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        return None

    delimiter: str = dialect.delimiter
    if delimiter in {",", "\t", ";", "|"}:
        return cast(Delimiter, delimiter)
    return None


def _load_space_aligned_table(lines: list[str]) -> list[Record]:
    rows: list[str] = [line.rstrip("\r\n") for line in lines if line.strip()]
    if not rows:
        return []

    header: str = rows[0]
    columns: list[str | Any] = [column.strip() for column in re.split(r"\s{2,}", header.strip()) if column.strip()]
    if len(columns) <= 1:
        columns = header.split()
        data_rows = [row.split() for row in rows[1:]]
    else:
        data_rows: list[list[str | Any]] = [
            [value.strip() for value in re.split(r"\s{2,}", row.strip(), maxsplit=len(columns) - 1)]
            for row in rows[1:]
        ]

    records: list[Record] = []
    for values in data_rows:
        record: Record = {}
        for index, column in enumerate(columns):
            record[column] = values[index] if index < len(values) else ""
        records.append(record)

    return records


CsvAdapter = TextTableAdapter
TabularAdapter = TextTableAdapter
load_csv: Callable[..., list[dict[str, Any]]] = load_text_table
csv_to_documents: Callable[..., list[Mapping[str, Any]]] = text_table_to_documents
