"""外部文書ファイルから検索用TextDocumentを作成する抽出器。"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from query_engine.adapters.documents import TextDocument, from_text, normalize_text

TEXT_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".rst", ".csv", ".json", ".jsonl", ".log", ".py", ".js", ".ts"})
HTML_EXTENSIONS: frozenset[str] = frozenset({".html", ".htm", ".xhtml"})
PDF_EXTENSIONS: frozenset[str] = frozenset({".pdf"})
DOCX_EXTENSIONS: frozenset[str] = frozenset({".docx"})


def extract_text_file(path: str | Path, **metadata: Any) -> TextDocument:
    """拡張子に応じて文書を読み込み、TextDocumentへ変換する。"""
    file_path: Path = Path(path)
    suffix: str = file_path.suffix.casefold()
    if suffix in TEXT_EXTENSIONS:
        return _extract_plain_text(file_path, **metadata)
    if suffix in HTML_EXTENSIONS:
        return _extract_html(file_path, **metadata)
    if suffix in PDF_EXTENSIONS:
        return _extract_pdf(file_path, **metadata)
    if suffix in DOCX_EXTENSIONS:
        return _extract_docx(file_path, **metadata)
    raise ValueError(f"未対応のファイル形式です: {suffix or file_path.name}")


def _extract_plain_text(path: Path, **metadata: Any) -> TextDocument:
    charset_normalizer: Any = _import_charset_normalizer()
    raw: bytes = path.read_bytes()
    detected: Any = charset_normalizer.from_bytes(raw).best()
    text: str = "" if detected is None else str(detected)
    return from_text(text, title=path.stem, source=str(path), **metadata)


def _extract_html(path: Path, **metadata: Any) -> TextDocument:
    charset_normalizer: Any = _import_charset_normalizer()
    raw: bytes = path.read_bytes()
    detected: Any = charset_normalizer.from_bytes(raw).best()
    html: str = "" if detected is None else str(detected)
    try:
        bs4: Any = _import_bs4()
    except RuntimeError:
        title: str
        text: str
        title, text = _extract_html_with_stdlib(html, default_title=path.stem)
        return from_text(text, title=title, source=str(path), **metadata)
    soup: Any = bs4.BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = normalize_text(soup.title.get_text(" ")) if soup.title else path.stem
    text = normalize_text(soup.get_text(" "))
    return from_text(text, title=title or path.stem, source=str(path), **metadata)


def _extract_html_with_stdlib(html: str, *, default_title: str) -> tuple[str, str]:
    parser: _PlainTextHTMLParser = _PlainTextHTMLParser()
    parser.feed(html)
    return parser.title or default_title, normalize_text(" ".join(parser.parts))


class _PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text: str = normalize_text(data)
        if not text:
            return
        if self._in_title:
            self.title: str = text
        self.parts.append(text)


def _extract_pdf(path: Path, **metadata: Any) -> TextDocument:
    pypdf: Any = _import_pypdf()
    reader: Any = pypdf.PdfReader(str(path))
    parts: list[str] = [page.extract_text() or "" for page in reader.pages]
    return from_text("\n".join(parts), title=path.stem, source=str(path), **metadata)


def _extract_docx(path: Path, **metadata: Any) -> TextDocument:
    docx: Any = _import_docx()
    document: Any = docx.Document(str(path))
    parts: list[str] = [paragraph.text for paragraph in document.paragraphs]
    return from_text("\n".join(parts), title=path.stem, source=str(path), **metadata)


def _import_charset_normalizer() -> Any:
    try:
        import charset_normalizer
    except ImportError as exc:
        raise RuntimeError("charset-normalizer が必要です。pip install charset-normalizer を実行してください。") from exc
    return charset_normalizer


def _import_bs4() -> Any:
    try:
        import bs4
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 が必要です。pip install beautifulsoup4 を実行してください。") from exc
    return bs4


def _import_pypdf() -> Any:
    try:
        import pypdf
    except ImportError as exc:
        raise RuntimeError("pypdf が必要です。pip install pypdf を実行してください。") from exc
    return pypdf


def _import_docx() -> Any:
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("python-docx が必要です。pip install python-docx を実行してください。") from exc
    return docx
