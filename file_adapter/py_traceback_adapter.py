# -*- coding: utf-8 -*-
"""Pythonのトレースバックを処理するためのアダプター。
py_traceback_adapter.pyは、Pythonのトレースバックを解析し、必要な情報を抽出して、
要約エンジンやUI層で利用できる形式に変換する役割を担います。
また、将来的には、他の形式のトレースバックにも対応できるように、柔軟な設計を目指しています。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from file_adapter.adapter_types import AdapterResult, FileAdapterFormat, RawRecord

FRAME_PATTERN = re.compile(r'^\s*File "(?P<file>[^"]+)", line (?P<line>\d+)')


def load_py_traceback_records(path: Path) -> AdapterResult:
    """Python tracebackテキストを1件のERROR raw recordへ変換する。"""
    try:
        text = path.read_text(encoding="utf-8-sig")
        record = parse_traceback_text(text, source_name=path.name)
        return AdapterResult(
            records=[] if record is None else [record],
            format_name=FileAdapterFormat.PY_TRACEBACK.value,
            success=record is not None,
        )
    except Exception as exc:
        return AdapterResult(records=[], format_name=FileAdapterFormat.PY_TRACEBACK.value, success=False, error=str(exc))


def parse_traceback_text(text: str, *, source_name: str) -> RawRecord | None:
    if "Traceback (most recent call last):" not in text:
        return None

    frames: list[dict[str, object]] = []
    for line in text.splitlines():
        match = FRAME_PATTERN.match(line)
        if match is not None:
            frames.append({"file": match.group("file"), "line": int(match.group("line"))})

    message = _last_non_empty_line(text)
    last_frame = frames[-1] if frames else {}
    return {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "level": "ERROR",
        "module": str(last_frame.get("file", source_name)),
        "event_id": f"traceback:{source_name}",
        "message": message,
        "frames": frames,
        "source_format": FileAdapterFormat.PY_TRACEBACK.value,
        "traceback": text,
    }


def _last_non_empty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return "Python traceback"
