# -*- coding: utf-8 -*-
# pylint: disable=W0718,C0301
"""表示整形のモジュール"""
#########################
# Author: F.Kurokawa
# Description:
# Display formatter
#########################
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, cast

from zoneinfo import ZoneInfo

from logs.context_types import ContextType, ContextValue
from logs.log_types import Event, LogDict, LogWhere
from logs.log_searcher import normalize_message_type_name
from logs.time_utils import (
    to_world_local_datetime,
)


class LogRenderer:
    """ログ表示専用クラス（整形エンジン🔥）"""

    def __init__(self, *, indent: int = 2, key_width: int = 12) -> None:
        self.indent: str = " " * indent
        self.key_width: int = key_width
        # フォント指定
        self.font_title: tuple[str, int, str] = ("Yu Gothic UI", 12, "bold")
        self.font_normal: tuple[str, int] = ("Yu Gothic UI", 10)
        self.font_bold_normal: tuple[str, int, str] = ("Yu Gothic UI", 10, "bold")
        self.font_mono: tuple[str, int] = ("Cascadia Code", 10)

    # =========================
    # 色付きRenderer
    # =========================
    def get_level_color(self, level: str) -> str:
        """色付き描画"""
        return {
            "DEBUG": "#888888",
            "INFO": "#000000",
            "WARNING": "#d97f00",
            "ERROR": "#d00000",
            "CRITICAL": "#800000",
            "REBOOT": "#0066cc",
        }.get(level, "#000000")

    # =========================
    # 🔹 message整形
    # =========================
    def format_message(self, msg: str) -> str:
        """messageの整形"""
        prefix: str
        rest: str
        # 👉 両対応（安全）
        if "→" in msg:
            sep = "→"
        elif "->" in msg:
            sep = "->"
        else:
            return msg

        prefix, rest = msg.split(sep, 1)

        try:
            # 🔥 シングルクォート対応
            json_like: str = re.sub(r"'", '"', rest.strip())
            data: dict[str, Any] = json.loads(json_like)
            pretty: str = json.dumps(data, indent=2, ensure_ascii=False)
            return f"{prefix.strip()}\n→\n{pretty}"

        except Exception:
            # 🔥 安全フォールバック
            pretty = (
                rest.strip()
                .replace(", '", ",\n  '")
                .replace("{", "{\n  ")
                .replace("}", "\n}")
            )
            return f"{prefix.strip()}\n→ {pretty}"

    # =========================
    # 🔹 時刻整形(Timezone対応)
    # =========================
    def format_time_full(self, value: Any, tz: str | ZoneInfo) -> tuple[str, str]:
        """Local + UTC の完全フォーマット"""

        dt_local: datetime | None = to_world_local_datetime(value, tz)
        if dt_local is None:
            return ("", "")

        # Local
        local_str: str = dt_local.strftime("%Y-%m-%d %H:%M:%S")

        # UTC
        dt_utc: datetime = dt_local.astimezone(timezone.utc)
        utc_str: str = dt_utc.strftime("%Y-%m-%d %H:%M:%S")

        # TZ情報
        tz_name: str = tz if isinstance(tz, str) else tz.key
        tz_abbr: str = dt_local.tzname() or ""

        label: str = f"{tz_name} | {tz_abbr}" if tz_abbr else tz_name

        return (
            f"Time(Local:{label}) : {local_str}",
            f"Time(UTC)          : {utc_str}",
        )

    # =========================
    # 🔹 Context整形
    # =========================
    def build_context_lines(
        self,
        context: dict[str, Any],
        tz: str,
        level: int = 0,
    ) -> list[str]:
        """context整形（ネスト対応・再帰・型安全🔥）"""

        lines: list[str] = []
        indent: str = self.indent * (level + 1)

        for k, v in context.items():
            key_str: str = f"{indent}{k:<{self.key_width}} : "

            # =========================
            # 🟢 型付きデータ
            # =========================
            if isinstance(v, dict) and "type" in v and "value" in v:
                v_typed: ContextValue = cast(ContextValue, v)

                v_type: ContextType = cast(ContextType, v_typed["type"])
                v_value: Any = v_typed["value"]

                # 🔹 datetime
                if v_type == ContextType.DATETIME:
                    dt: datetime | None = to_world_local_datetime(v_value, tz)
                    v_str: str = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else str(v_value)
                    lines.append(f"{key_str}{v_str}")
                    continue

                # 🔹 dict（ネスト）
                if isinstance(v_value, dict):
                    v_dict: dict[str, Any] = cast(dict[str, Any], v_value)

                    lines.append(f"{key_str}{{")
                    lines.extend(self.build_context_lines(v_dict, tz, level + 1))
                    lines.append(f"{indent}}}")
                    continue

                # 🔹 list（ネスト）
                if isinstance(v_value, list):
                    v_list: list[Any] = cast(list[Any], v_value)

                    lines.append(f"{key_str}[")
                    for i, item in enumerate(v_list):
                        item_key: str = f"{indent}{self.indent}[{i}]".ljust(self.key_width + len(indent) + 3)

                        # dict inside list
                        if isinstance(item, dict):
                            item_dict: dict[str, Any] = cast(dict[str, Any], item)

                            lines.append(f"{item_key}{{")
                            lines.extend(self.build_context_lines(item_dict, tz, level + 2))
                            lines.append(f"{indent}{self.indent}}}")
                        else:
                            lines.append(f"{item_key} : {item}")

                    lines.append(f"{indent}]")
                    continue

                # 🔹 その他
                lines.append(f"{key_str}{v_value}")
                continue

            # =========================
            # 🟡 旧形式（安全）
            # =========================
            if isinstance(v, dict):
                v_dict: dict[str, Any] = cast(dict[str, Any], v)

                lines.append(f"{key_str}{{")
                lines.extend(self.build_context_lines(v_dict, tz, level + 1))
                lines.append(f"{indent}}}")
                continue

            if isinstance(v, list):
                v_list: list[Any] = cast(list[Any], v)

                lines.append(f"{key_str}[")
                for i, item in enumerate(v_list):
                    lines.append(f"{indent}{self.indent}[{i}] : {item}")
                lines.append(f"{indent}]")
                continue

            # =========================
            # 🔹 普通の値
            # =========================
            lines.append(f"{key_str}{v}")

        return lines

    # =========================
    # 🔹 Event整形
    # =========================
    def build_event(self, data: dict[str, Any]) -> str:
        """イベント整形"""
        lines: list[str] = []
        for k, v in data.items():
            lines.append(f"{self.indent}{k:<{self.key_width}} : {v}")
        return "\n".join(lines)

    # ==========================
    # 🔹 詳細表示整形
    # ==========================
    def build_summary_parts(self, row: Event, tz: str) -> list[tuple[str, str]]:
        """
        戻り値：[(テキスト, 色), ...]
        """
        raw: LogDict = row.raw

        level: str = row.level.name
        color: str = self.get_level_color(level)

        where: LogWhere = raw.get("where", {})

        time_utc_line: str
        time_local_line: str
        time_local_line, time_utc_line = self.format_time_full(row.time, tz)
        display_type: str = row.type.name if row.type else (
            normalize_message_type_name(raw.get("what", {}).get("message", "")) or level
        )

        parts: list[tuple[str, str]] = [
            (f"Type  : {display_type}", color),
            (f"Level : {level}", color),
            (time_local_line, "#000000"),
            (time_utc_line, "#888888"),
            ("", ""),
        ]

        # 🔹 message
        msg = str(raw.get("what", {}).get("message", ""))
        msg: str = self.format_message(msg)
        parts += [
            ("=== MESSAGE ===", "#0000aa"),
            (msg, "#000000"),
            ("", ""),
        ]

        # 🔹 where情報（これ重要🔥）
        parts += [
            ("--- where ---", "#bb00cc"),
            (f"File : {where.get('file','')}", "#444444"),
            (f"Line : {where.get('line','')}", "#444444"),
            (f"Func : {where.get('function','')}", "#444444"),
            ("", ""),
        ]

        # 🔹 Event
        if row.data:
            parts.append(("--- Event ---", "#0066cc"))
            for k, v in row.data.items():
                parts.append((f"{self.indent}{k:<{self.key_width}} : {v}", "#000000"))
            parts.append(("", ""))

        # 🔹 Context
        context: dict[str, ContextValue | Any] = raw.get("context", {})

        if context:
            parts.append(("--- Context ---", "#1b03a3"))

            lines: list[str] = self.build_context_lines(context, tz)

            for line in lines:
                parts.append((line, "#000000"))

        return parts
    # =========================
    # 🔹 Summary生成🔥
    # =========================
    def build_summary(self, row: Event, tz: str) -> str:
        """Summary整形（表示用テキスト生成）"""
        parts: list[tuple[str, str]] = self.build_summary_parts(row, tz)
        return "\n".join(text for text, _ in parts)

    # =========================
    # 🔹 RAW生成
    # =========================
    def build_raw(self, row: Event) -> dict[str, Any]:
        """RAW整形"""
        raw: LogDict = row.raw

        result: dict[str, Any] = {
            "level": raw.get("level"),
            "time": raw.get("time"),
            "trace_id": raw.get("trace_id"),
            "where": raw.get("where"),
            "what": raw.get("what"),
            "context": raw.get("context"),
        }

        if row.data:
            result |= {"event": row.data}

        return result
