# -*- coding: utf-8 -*-
"""辞書をフラット化するユーティリティモジュール。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from typing import Any, cast

__all__: list[str] = [
    "flatten_dict",
]




def flatten_dict(
    data: dict[str, Any],
    prefix: str = "",
) -> dict[str, Any]:
    """ネストしたdictをドット区切りへ展開する。"""

    result: dict[str, Any] = {}

    for key, value in data.items():
        new_key: str = key if not prefix else f"{prefix}.{key}"

        if isinstance(value, dict):
            child: dict[str, Any] = cast(
                dict[str, Any],
                value,
            )

            result.update(
                flatten_dict(
                    child,
                    new_key,
                )
            )
        else:
            result[new_key] = value

    return result