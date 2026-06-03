# -*- coding: utf-8 -*-
"""LOGに記録された値の状態を確認する"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from logs.log_app import get_logger
from logs.log_analysis import LogType, detect_log_type, normalize_external_log
from logs.log_types import LogDict, LogWhat

if TYPE_CHECKING:
    from multi_info_logger import AppLogger


def validate_log(
    raw: dict[str, Any],
    logger: "AppLogger" = get_logger()
) -> LogDict | None:
    """Unsafe → Safe変換"""
    log_type: LogType = detect_log_type(raw)
    normalized: dict[str, Any] = (
        dict(raw)
        if log_type == LogType.LOGGER_PROJECT
        else normalize_external_log(raw)
    )

    # time
    if not isinstance(normalized.get("time"), str):  # type: ignore[reportUnnecessaryIsInstance]
        _warn_invalid_log(logger, "missing time", raw)
        return None

    # trace_id
    if not isinstance(normalized.get("trace_id"), str):  # type: ignore[reportUnnecessaryIsInstance]
        _warn_invalid_log(logger, "missing trace_id", raw)
        return None

    # level
    if not isinstance(normalized.get("level"), str):  # type: ignore[reportUnnecessaryIsInstance]
        _warn_invalid_log(logger, "missing level", raw)
        return None

    # what
    raw_what: object = normalized.get("what")
    if not isinstance(raw_what, dict):
        _warn_invalid_log(logger, "missing what", raw)
        return None
    # 👇 ここが最重要🔥
    raw_what_dict: dict[str, Any] = cast(dict[str, Any], raw_what)
    
    # messageは必須
    message_raw: object = raw_what_dict.get("message")
    if not isinstance(message_raw, str):
        _warn_invalid_log(logger, "missing message", raw)
        return None
    message: str = message_raw
    what: LogWhat = {"message": message}

    # where
    raw_where: object = normalized.get("where")
    if isinstance(raw_where, dict):
        where: dict[str, Any] = cast(dict[str, Any], raw_where)
    else:
        where = {}

    # output（追加🔥）
    output_raw: object = normalized.get("output")

    if isinstance(output_raw, str):
        output: str = output_raw
    else:
        output = "both"

    return cast(
        LogDict,
        {
        "level": normalized["level"],
        "time": normalized["time"],
        "trace_id": normalized["trace_id"],
        "where": where,
        "what": what,
        "context": _get_context(normalized),
        "output": output,
    })


def _get_context(normalized: dict[str, Any]) -> dict[str, Any]:
    raw_context: object = normalized.get("context", {})
    if isinstance(raw_context, dict):
        return dict(cast(dict[str, Any], raw_context))
    return {}


def _warn_invalid_log(logger: "AppLogger", reason: str, raw: dict[str, Any]) -> None:
    """invalid警告では元ログをmessageへ埋め込まずcontextへ残す。"""
    logger.warning(
        f"invalid log: {reason}",
        context={
            "reason": reason,
            "raw": raw,
        },
    )
