# -*- coding: utf-8 -*-
"""contextの情報記述の種類定義"""
#########################
# Author: F.Kurokawa
# Description:
# Context types definition
#########################
from __future__ import annotations

from enum import Enum

CUSTOM_TYPES: set[str] = set()

class ContextType(str, Enum):
    DATETIME = "datetime"
    INT = "int"
    STR = "str"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    NONE = "none"
    ANY = "any"


def is_custom_type(type_name: str) -> bool:
    return type_name in CUSTOM_TYPES
