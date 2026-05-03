# -*- coding: utf-8 -*-

#########################
# Author: F.Kurokawa
# Description:
#
#########################

from datetime import datetime, date
from typing import Any

from logs.context_types import ContextType, CUSTOM_TYPES


def detect_type(value: Any) -> ContextType:
    """値からContextTypeを推定"""

    if isinstance(value, datetime):
        return ContextType.DATETIME
    if isinstance(value, date):
        return ContextType.DATETIME
    if isinstance(value, bool):
        return ContextType.BOOL
    if isinstance(value, int):
        return ContextType.INT
    if isinstance(value, float):
        return ContextType.FLOAT
    if isinstance(value, str):
        return ContextType.STR
    if isinstance(value, list):
        return ContextType.LIST
    if isinstance(value, dict):
        return ContextType.DICT
    
    # カスタム型や不明な型はANYとして扱う
    CUSTOM_TYPES.add(type(value).__name__)
    return ContextType.ANY


def wrap_value(value: Any) -> dict[str, Any]:
    """値をContext形式に変換"""
    v_type: ContextType = detect_type(value)

    if v_type == ContextType.DATETIME and isinstance(value, datetime):
        value = value.isoformat()

    return {
        "type": v_type,
        "value": value,
    }


def ctx(**kwargs: Any) -> dict[str, dict[str, Any]]:
    """
    context自動生成ヘルパー

    例:
    ctx(a=1, b="test")
    """

    return {k: wrap_value(v) for k, v in kwargs.items()}
