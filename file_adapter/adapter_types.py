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
from typing import Any



@dataclass(frozen=True, slots=True)
class AdapterResult:
    records: list[dict[str, Any]]
    format_name: str
    success: bool
    error: str = ""