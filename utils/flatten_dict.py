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
    "unflatten_dict",
    "flatten_list",
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


def unflatten_dict(
    data: Mapping[str, Any],
) -> dict[str, Any]:
    """ドット区切りのフラットな辞書からネストした辞書へ戻す。
    例:
    {
        "what.message": "error"
    }
    ↓
    {
        "what": {
            "message": "error"
        }
    }
    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        parts: list[str] = key.split(".")
        current: dict[str, Any] = result

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = cast(dict[str, Any], current[part])

        current[parts[-1]] = value

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
            result.extend(
                flatten_list(
                    cast(list[Any], value)
                    )
                )
        elif isinstance(value, Mapping):
            result.append(
                flatten_dict(
                    cast(Mapping[str, Any], value)
                    )
                )
        else:
            result.append(value)

    return result
