# -*- coding: utf-8 -*-
"""contextの情報記述の種類定義"""
#########################
# Author: F.Kurokawa
# Description:
# Context types definition
#########################
from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict

CUSTOM_TYPES: set[str] = set()

class ContextType(str, Enum):
    DATETIME = "datetime"
    INT = "int"
    STR = "str"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    ANY = "any" # 不明な型やカスタム型はANYとして扱う


class ContextValue(TypedDict):
    type: ContextType | str  # カスタム型もあるのでstrも許容
    value: Any

def is_custom_type(type_name: str) -> bool:
    return type_name in CUSTOM_TYPES