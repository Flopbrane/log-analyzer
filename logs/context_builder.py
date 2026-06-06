# -*- coding: utf-8 -*-
"""contextの情報を構築するヘルパー関数群"""

#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import inspect
import traceback
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, TypeAlias

from logs.context_types import CUSTOM_TYPES, ContextType

ContextDict: TypeAlias = dict[str, Any]
WrappedContextValue: TypeAlias = dict[str, Any]
WrappedContextDict: TypeAlias = dict[str, WrappedContextValue]


def detect_context_type(value: Any) -> ContextType:
    """値からContextTypeを推定する。"""
    if value is None:
        return ContextType.NONE
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

    CUSTOM_TYPES.add(type(value).__name__)
    return ContextType.ANY


def ctx(**kwargs: Any) -> WrappedContextDict:
    """Logger保存用のtype/value付きcontextを作る。"""
    return wrap_context(kwargs)


def plain_context(**kwargs: Any) -> ContextDict:
    """type/valueを付けない普通のcontextを作る。"""
    return dict(kwargs)


def wrap_context_value(value: Any) -> WrappedContextValue:
    """値を表示・分析用のContext形式に変換する。"""
    v_type: ContextType = detect_context_type(value)

    if v_type == ContextType.DATETIME and isinstance(value, (datetime, date)):
        value = value.isoformat()

    return {
        "type": v_type.value,
        "value": value,
    }


def wrap_context(context: Mapping[str, Any]) -> WrappedContextDict:
    """普通のcontextを、type/value付きcontextへ変換する。"""
    return {key: wrap_context_value(value) for key, value in context.items()}


def get_caller_context(depth: int = 2) -> ContextDict:
    """呼び出し元のmodule/class/function/file_path/line_noを取得する。"""
    frame: FrameType | None = inspect.currentframe()

    for _ in range(depth):
        if frame is None:
            return {}
        frame = frame.f_back

    if frame is None:
        return {}

    module: ModuleType | None = inspect.getmodule(frame)
    module_name: str = module.__name__ if module is not None else ""

    class_name: str = ""

    self_obj: Any | None = frame.f_locals.get("self")
    if self_obj is not None:
        class_name = self_obj.__class__.__name__

    cls_obj: Any | None = frame.f_locals.get("cls")
    if isinstance(cls_obj, type):
        class_name = cls_obj.__name__

    return {
        "module": module_name,
        "class": class_name,
        "function": frame.f_code.co_name,
        "file_path": str(Path(frame.f_code.co_filename)),
        "line_no": frame.f_lineno,
    }

# =================================
# 便利なcontext構築関数群
# =================================
def context_for_program(
    state: str,
    detail: str | None = None,
    caller_depth: int = 2,
    **extra: Any,
) -> ContextDict:
    """プログラム状態用のcontextを作る。"""
    context: ContextDict = get_caller_context(depth=caller_depth)
    context["state"] = state
    if detail:
        context["detail"] = detail
    context.update(extra)
    return context


def context_for_loader(
    load_file_path: str,
    encoding: str = "",
    format_name: str = "",
    record_count: int | None = None,
    **extra: Any,
) -> ContextDict:
    """読み込み処理用のcontextを作る。"""
    context: ContextDict = {
        "load_file_path": load_file_path,
        "encoding": encoding,
        "format_name": format_name,
        "record_count": record_count,
    }
    context.update(extra)
    return context


def context_for_saver(
    save_file_path: str,
    encoding: str = "utf-8",
    record_count: int | None = None,
    **extra: Any,
) -> ContextDict:
    """保存処理用のcontextを作る。"""
    context: ContextDict = {
        "save_file_path": save_file_path,
        "encoding": encoding,
        "record_count": record_count,
    }
    context.update(extra)
    return context


def context_for_adapter(
    adapter_name: str,
    format_name: str,
    success: bool,
    load_file_path: str = "",
    record_count: int | None = None,
    error: str = "",
    **extra: Any,
) -> ContextDict:
    """ファイルアダプタ用のcontextを作る。"""
    context: ContextDict = {
        "adapter_name": adapter_name,
        "format_name": format_name,
        "success": success,
        "load_file_path": load_file_path,
        "record_count": record_count,
        "error": error,
    }
    context.update(extra)
    return context


def context_for_validation_error(
    reason: str,
    raw: Mapping[str, Any],
    **extra: Any,
) -> ContextDict:
    """ログ検証エラー用のcontextを作る。"""
    context: ContextDict = {
        "reason": reason,
        "raw": dict(raw),
    }
    context.update(extra)
    return context


def context_for_exception(
    error: BaseException,
    state: str = "exception",
    detail: str = "",
    include_traceback: bool = False,
    caller_depth: int = 2,
    **extra: Any,
) -> ContextDict:
    """例外情報をcontext化する。"""

    context: ContextDict = context_for_program(
        state=state,
        detail=detail,
        caller_depth=caller_depth,
        error_type=type(error).__name__,
        error_message=str(error),
    )

    if include_traceback:
        context["traceback"] = traceback.format_exc()

    context.update(extra)
    return context


def context_for_viewer(
    action: str,
    selected_count: int | None = None,
    filter_text: str = "",
    **extra: Any,
) -> ContextDict:
    """ビューア用のcontextを作る。"""
    context: ContextDict = {
        "action": action,
        "selected_count": selected_count,
        "filter_text": filter_text,
    }
    context.update(extra)
    return context


def context_for_summary(
    condition_text: str,
    input_count: int,
    output_count: int | None = None,
    **extra: Any,
) -> ContextDict:
    """サマリー用のcontextを作る。"""
    context: ContextDict = {
        "condition_text": condition_text,
        "input_count": input_count,
        "output_count": output_count,
    }
    context.update(extra)
    return context


def context_for_query(
    query_text: str,
    result_count: int | None = None,
    error: str = "",
    **extra: Any,
) -> ContextDict:
    """クエリ用のcontextを作る。"""
    context: ContextDict = {
        "query_text": query_text,
        "result_count": result_count,
        "error": error,
    }
    context.update(extra)
    return context


def context_for_http_access(
    ip: str = "",
    method: str = "",
    path: str = "",
    status: int | None = None,
    bytes_sent: int | None = None,
    user_agent: str = "",
    server: str = "",
    **extra: Any,
) -> ContextDict:
    """HTTPアクセス用のcontextを作る。"""
    context: ContextDict = {
        "ip": ip,
        "method": method,
        "path": path,
        "status": status,
        "bytes_sent": bytes_sent,
        "user_agent": user_agent,
        "server": server,
    }
    context.update(extra)
    return context


def context_for_apache_access(
    ip: str = "",
    method: str = "",
    path: str = "",
    status: int | None = None,
    bytes_sent: int | None = None,
    user_agent: str = "",
    **extra: Any,
) -> ContextDict:
    """Apacheアクセス用のcontextを作る。"""
    return context_for_http_access(
        ip=ip,
        method=method,
        path=path,
        status=status,
        bytes_sent=bytes_sent,
        user_agent=user_agent,
        server="apache",
        **extra,
    )


def context_for_nginx_access(
    ip: str = "",
    method: str = "",
    path: str = "",
    status: int | None = None,
    bytes_sent: int | None = None,
    user_agent: str = "",
    **extra: Any,
) -> ContextDict:
    """Nginxアクセス用のcontextを作る。"""
    return context_for_http_access(
        ip=ip,
        method=method,
        path=path,
        status=status,
        bytes_sent=bytes_sent,
        user_agent=user_agent,
        server="nginx",
        **extra,
    )


def context_for_csv(
    file_path: str,
    delimiter: str = ",",
    quotechar: str = '"',
    **extra: Any,
) -> ContextDict:
    """CSV用のcontextを作る。"""
    context: ContextDict = {
        "file_path": file_path,
        "delimiter": delimiter,
        "quotechar": quotechar,
    }
    context.update(extra)
    return context


def context_for_json(
    file_path: str,
    **extra: Any,
) -> ContextDict:
    """JSON用のcontextを作る。"""
    context: ContextDict = {
        "file_path": file_path,
    }
    context.update(extra)
    return context


def context_for_sqlite(
    file_path: str,
    table_name: str = "",
    **extra: Any,
) -> ContextDict:
    """SQLite用のcontextを作る。"""
    context: ContextDict = {
        "file_path": file_path,
        "table_name": table_name,
    }
    context.update(extra)
    return context


def context_for_traceback(
    exception_type: str,
    message: str,
    file_path: str = "",
    line_no: int | None = None,
    **extra: Any,
) -> ContextDict:
    """Python traceback用のcontextを作る。"""
    context: ContextDict = {
        "exception_type": exception_type,
        "message": message,
        "file_path": file_path,
        "line_no": line_no,
    }
    context.update(extra)
    return context
