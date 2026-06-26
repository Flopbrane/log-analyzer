# -*- coding: utf-8 -*-
"""ファイルアダプタの型定義。
adapter_types.pyは、ファイルアダプタの型定義を行います。
"""

#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeAlias

RawRecord: TypeAlias = dict[str, Any]
RawRecords: TypeAlias = list[RawRecord]


class FileAdapterFormat(str, Enum):
    """ファイルアダプタのフォーマット"""
    JSON = "json"
    CSV = "csv"
    APACHE = "apache"
    NGINX = "nginx"
    PY_TRACEBACK = "py_traceback"
    SQLITE = "sqlite"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AdapterResult:
    """アダプタの処理結果"""
    records: RawRecords
    format_name: str
    success: bool
    error: str = ""
