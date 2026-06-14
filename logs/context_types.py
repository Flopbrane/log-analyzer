# -*- coding: utf-8 -*-
"""contextの情報記述の種類定義"""
#########################
# Author: F.Kurokawa
# Description:
# Context types definition
#########################
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import TypeAlias, TypedDict

CUSTOM_TYPES: set[str] = set()


ContextValue: TypeAlias = Mapping[str, object]

class ContextType(str, Enum):
    """コンテキストの値の型定義"""
    DATETIME = "datetime"
    INT = "int"
    STR = "str"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    NONE = "none"
    ANY = "any"


class TypedContextValue(TypedDict):
    """型付きコンテキスト値"""
    type: str
    value: object


def is_custom_type(type_name: str) -> bool:
    """カスタム型かどうかを判定する"""
    return type_name in CUSTOM_TYPES


__all__: list[str] = [
    "ContextValue",
    "ContextType",
    "TypedContextValue",
    "is_custom_type",
]
