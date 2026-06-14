# -*- coding: utf-8 -*-
# pylint: disable=C0301, C0303
"""検索結果と要約結果のエクスポート処理。"""
#########################
# Author: F.Kurokawa
# Description:
# 検索結果と要約結果のエクスポート処理
#########################

from __future__ import annotations

import csv
import json
import tkinter as tk
from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, cast

from logs.log_types import Event, LogDict, LogWhat, LogWhere
from summary_engine.summary_types import NumericStats, RankingItem, SummaryResult

CSV_TEXT_ENCODING = "utf-8-sig"
JSON_TEXT_ENCODING = "utf-8"

EVENT_CSV_HEADERS: tuple[str, ...] = (
    "type",
    "level",
    "time",
    "detected_at",
    "trace_id",
    "message",
    "data",
    "raw",
)

LOG_CSV_HEADERS: tuple[str, ...] = (
    "level",
    "time",
    "trace_id",
    "module",
    "file",
    "function",
    "message",
    "context",
    "output",
)

SUMMARY_CSV_HEADERS: tuple[str, ...] = (
    "exported_at",
    "condition_text",
    "total_count",
    "level_counts",
    "module_ranking",
    "message_ranking",
    "context_numeric_stats",
    "insights",
    "summary_text",
)


def select_save_file(
    *,
    defaultextension: str = ".csv",
    filetypes: Iterable[tuple[str, str]] | None = None,
    title: str = "保存先のファイル名を入力してください",
) -> str:
    """保存先のファイルパスを選択するダイアログを表示する。"""
    root = tk.Tk()
    root.withdraw()
    try:
        return filedialog.asksaveasfilename(
            defaultextension=defaultextension,
            filetypes=list(filetypes or (("CSV files", "*.csv"), ("All files", "*.*"))),
            title=title,
        )
    finally:
        root.destroy()


def export_logs_to_csv(
    logs: Iterable[LogDict],
    save_file_path: str | Path | None = None,
) -> Path | None:
    """フィルタリング後のLogDict一覧をCSVへ出力する。"""
    output_path: Path | None = _resolve_output_path(save_file_path, defaultextension=".csv")
    if output_path is None:
        return None

    rows: list[dict[str, str]] = [_log_to_csv_row(log) for log in logs]
    _write_csv(output_path, LOG_CSV_HEADERS, rows)
    return output_path


# 調査結果保存用（推奨）
def export_event_logs_to_csv(
    events: Iterable[Event],
    save_file_path: str | Path | None = None,
) -> Path | None:
    """Event.rawに保持された有意ログだけをLog形式CSVへ出力する。"""
    return export_logs_to_csv((event.raw for event in events), save_file_path)


# Event構造保存用（デバッグ向け）
def export_events_to_csv(
    events: Iterable[Event],
    save_file_path: str | Path | None = None,
) -> Path | None:
    """Event一覧をCSVへ出力する。"""
    output_path: Path | None = _resolve_output_path(save_file_path, defaultextension=".csv")
    if output_path is None:
        return None

    rows: list[dict[str, str]] = [_event_to_csv_row(event) for event in events]
    _write_csv(output_path, EVENT_CSV_HEADERS, rows)
    return output_path


def export_summary_to_csv(
    summary: SummaryResult,
    save_file_path: str | Path | None = None,
) -> Path | None:
    """SummaryResultをCSVへ出力する。"""
    output_path: Path | None = _resolve_output_path(save_file_path, defaultextension=".csv")
    if output_path is None:
        return None

    _write_csv(output_path, SUMMARY_CSV_HEADERS, [_summary_to_csv_row(summary)])
    return output_path


def export_to_json(
    *,
    logs: Iterable[LogDict] | None = None,
    events: Iterable[Event] | None = None,
    summary: SummaryResult | None = None,
    report: Mapping[str, Any] | None = None,
    save_file_path: str | Path | None = None,
) -> Path | None:
    """ログ・イベント・要約を1つのJSONへ出力する。"""
    output_path: Path | None = _resolve_output_path(
        save_file_path,
        defaultextension=".json",
        filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
    )
    if output_path is None:
        return None

    payload: dict[str, Any] = {
        "exported_at": _utc_now_text(),
        "logs": [_json_safe(log) for log in (logs or ())],
        "events": [_event_to_json(event) for event in (events or ())],
        "summary": None if summary is None else _summary_to_json(summary),
        "report": None if report is None else _json_safe(report),
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding=JSON_TEXT_ENCODING,
    )
    return output_path


def export_search_result_bundle(
    *,
    logs: Iterable[LogDict],
    summary: SummaryResult | None,
    save_file_path: str | Path | None = None,
) -> Path | None:
    """検索結果ログと要約をまとめてJSONへ出力する。"""
    return export_to_json(logs=logs, summary=summary, save_file_path=save_file_path)


def export_investigation_report_json(
    *,
    logs: Iterable[LogDict],
    events: Iterable[Event],
    summary: SummaryResult,
    condition_text: str,
    timezone_name: str,
    source_files: Iterable[str | Path] = (),
    save_file_path: str | Path | None = None,
) -> Path | None:
    """検索結果・Event・要約を調査レポートJSONとして保存する。"""
    report: dict[str, Any] = {
        "kind": "investigation_report",
        "condition_text": condition_text,
        "timezone": timezone_name,
        "source_files": [str(path) for path in source_files],
    }
    return export_to_json(
        logs=logs,
        events=events,
        summary=summary,
        report=report,
        save_file_path=save_file_path,
    )


def _resolve_output_path(
    save_file_path: str | Path | None,
    *,
    defaultextension: str,
    filetypes: Iterable[tuple[str, str]] | None = None,
) -> Path | None:
    if save_file_path is None:
        selected: str = select_save_file(
            defaultextension=defaultextension,
            filetypes=filetypes,
        )
        if not selected:
            return None
        return Path(selected)
    output_path = Path(save_file_path)
    if not output_path.suffix:
        output_path: Path = output_path.with_suffix(defaultextension)
    return output_path


def _write_csv(
    output_path: Path,
    headers: Iterable[str],
    rows: Iterable[Mapping[str, str]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding=CSV_TEXT_ENCODING) as csv_file:
        writer: csv.DictWriter[str] = csv.DictWriter(csv_file, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)


def _event_to_csv_row(event: Event) -> dict[str, str]:
    return {
        "type": "" if event.type is None else event.type.value,
        "level": event.level.value,
        "time": event.time,
        "detected_at": event.detected_at,
        "trace_id": str(event.trace_id),
        "message": event.message,
        "data": _json_text(event.data),
        "raw": _json_text(event.raw),
    }


def _log_to_csv_row(log: LogDict) -> dict[str, str]:
    where: LogWhere = log.get("where", {})
    what: LogWhat = log.get("what", {})
    return {
        "level": str(log.get("level", "")),
        "time": str(log.get("time", "")),
        "trace_id": str(log.get("trace_id", "")),
        "module": str(where.get("module", "")),
        "file": str(where.get("file", "")),
        "function": str(where.get("function", "")),
        "message": str(what.get("message", "")),
        "context": _json_text(log.get("context", {})),
        "output": str(log.get("output", "")),
    }


def _summary_to_csv_row(summary: SummaryResult) -> dict[str, str]:
    return {
        "exported_at": _utc_now_text(),
        "condition_text": summary.condition_text,
        "total_count": str(summary.total_count),
        "level_counts": _json_text(summary.level_counts),
        "module_ranking": _json_text([_ranking_item_to_dict(item) for item in summary.module_ranking]),
        "message_ranking": _json_text([_ranking_item_to_dict(item) for item in summary.message_ranking]),
        "context_numeric_stats": _json_text(
            {
                key: _numeric_stats_to_dict(value)
                for key, value in summary.context_numeric_stats.items()
            }
        ),
        "insights": _json_text(list(summary.insights)),
        "summary_text": summary.text,
    }


def _event_to_json(event: Event) -> dict[str, Any]:
    return {
        "type": None if event.type is None else event.type.value,
        "level": event.level.value,
        "time": event.time,
        "detected_at": event.detected_at,
        "trace_id": str(event.trace_id),
        "message": event.message,
        "data": _json_safe(event.data),
        "raw": _json_safe(event.raw),
    }


def _summary_to_json(summary: SummaryResult) -> dict[str, Any]:
    return {
        "total_count": summary.total_count,
        "condition_text": summary.condition_text,
        "level_counts": dict(summary.level_counts),
        "module_ranking": [_ranking_item_to_dict(item) for item in summary.module_ranking],
        "message_ranking": [_ranking_item_to_dict(item) for item in summary.message_ranking],
        "context_numeric_stats": {
            key: _numeric_stats_to_dict(value)
            for key, value in summary.context_numeric_stats.items()
        },
        "insights": list(summary.insights),
        "text": summary.text,
    }


def _ranking_item_to_dict(item: RankingItem) -> dict[str, Any]:
    return {"key": item.key, "count": item.count}


def _numeric_stats_to_dict(stats: NumericStats) -> dict[str, Any]:
    return {
        "field": stats.field,
        "count": stats.count,
        "minimum": stats.minimum,
        "maximum": stats.maximum,
        "average": stats.average,
        "median": stats.median,
    }


def _json_text(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, default=str)


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_safe(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        mapping_value: Mapping[Any, Any] = cast(Mapping[Any, Any], value)
        return {
            str(key): _json_safe(child)
            for key, child in mapping_value.items()
        }
    if isinstance(value, tuple):
        tuple_value: tuple[Any, ...] = cast(tuple[Any, ...], value)
        return [_json_safe(child) for child in tuple_value]
    if isinstance(value, list):
        list_value: list[Any] = cast(list[Any], value)
        return [_json_safe(child) for child in list_value]
    if isinstance(value, Path):
        return str(value)
    return value


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__: list[str] = [
    "export_logs_to_csv",
    "export_event_logs_to_csv",
    "export_events_to_csv",
    "export_summary_to_csv",
    "export_to_json",
    "export_search_result_bundle",
    "export_investigation_report_json",
]
