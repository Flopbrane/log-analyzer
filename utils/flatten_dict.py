# -*- coding: utf-8 -*-
"""辞書をフラット化するユーティリティモジュール。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

__all__: list[str] = [
    "flatten_dict",
]




def flatten_dict(
    data: Mapping[str, Any],
    prefix: str = "",
) -> dict[str, Any]:
    """
    ネストした辞書をドット区切りの
    フラットな辞書へ変換する。

    例:
        {
            "what": {
                "message": "error"
            }
        }

    ↓

        {
            "what.message": "error"
        }
    """

    result: dict[str, Any] = {}

    for key, value in data.items():
        new_key: str = key if not prefix else f"{prefix}.{key}"

        if isinstance(value, Mapping):
            child: Mapping[str, Any] = cast(
                Mapping[str, Any],
                value,
            )

            result.update(
                flatten_dict(
                    child,
                    new_key,
                )
            )
        elif isinstance(value, list):
            result[new_key] = flatten_list(cast(list[Any], value))
        else:
            result[new_key] = value

    return result


def flatten_list(
    values: list[Any],
) -> list[Any]:
    """
    ネストしたリストをフラットなリストへ変換する。

    例:
        [
            {
                "message": "error"
            },
            [
                {
                    "message": "warning"
                }
            ],
        ]

    ↓

        [
            {
                "message": "error"
            },
            {
                "message": "warning"
            },
        ]
    """
    result: list[Any] = []

    for value in values:
        if isinstance(value, list):
            result.extend(flatten_list(cast(list[Any], value)))
        elif isinstance(value, Mapping):
            result.extend(flatten_dict(cast(Mapping[str, Any], value)).values())
        else:
            result.append(value)

    return result
