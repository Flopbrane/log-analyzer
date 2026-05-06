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
from logs.log_types import LogDict, LogWhat

if TYPE_CHECKING:
    from multi_info_logger import AppLogger


def validate_log(
    raw: dict[str, Any],
    logger: "AppLogger" = get_logger()
) -> LogDict | None:
    """Unsafe → Safe変換"""

    # time
    if not isinstance(raw.get("time"), str):  # type: ignore[reportUnnecessaryIsInstance]
        logger.warning(f"invalid log: missing time → {raw}")
        return None

    # trace_id
    if not isinstance(raw.get("trace_id"), str):  # type: ignore[reportUnnecessaryIsInstance]
        logger.warning(f"invalid log: missing trace_id → {raw}")
        return None

    # level
    if not isinstance(raw.get("level"), str):  # type: ignore[reportUnnecessaryIsInstance]
        logger.warning(f"invalid log: missing level → {raw}")
        return None

    # what
    raw_what: object = raw.get("what")
    if not isinstance(raw_what, dict):
        logger.warning(f"invalid log: missing what → {raw}")
        return None
    # 👇 ここが最重要🔥
    raw_what_dict: dict[str, Any] = cast(dict[str, Any], raw_what)
    
    # messageは必須
    message_raw: object = raw_what_dict.get("message")
    if not isinstance(message_raw, str):
        logger.warning(f"invalid log: missing message → {raw}")
        return None
    message: str = message_raw
    what: LogWhat = {"message": message}

    # where
    raw_where: object = raw.get("where")
    if isinstance(raw_where, dict):
        where: dict[str, Any] = cast(dict[str, Any], raw_where)
    else:
        where = {}

    # output（追加🔥）
    output_raw: object = raw.get("output")

    if isinstance(output_raw, str):
        output: str = output_raw
    else:
        output = "both"

    return cast(
        LogDict,
        {
        "level": raw["level"],
        "time": raw["time"],
        "trace_id": raw["trace_id"],
        "where": where,
        "what": what,
        "context": cast(dict[str, Any], raw.get("context", {})),
        "output": output,
    })
