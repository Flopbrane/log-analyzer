# -*- coding: utf-8 -*-
# pylint: disable=W0718,C0301,C0302
# ruff: noqa: E501
"""ログ表示GUI（安定版）"""
#########################
# Author: F.Kurokawa
# Description:
# log_viewer
#########################

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tkinter as tk
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Final, TypeGuard, cast

from fv_engine.fv_interpreter import build_execution_plan
from fv_engine.fv_parser import parse_fv_text
from fv_engine.fv_plan import ExecutionPlan

# from fv_engine.fv_result import format_fv_result
from fv_engine.fv_runner import run_execution_plan
from fv_engine.fv_types import FVExportFormat, FVRecipe, FVResult
from logs.display_formatter import LogRenderer
from logs.language_selector import LanguageCode, build_timezone_label, normalize_language, translate, translate_timezone_area
from logs.log_app import get_logger
from logs.log_config import load_viewer_config, save_viewer_config
from logs.log_multi_select import LogFileSelector
from logs.log_paths import LOGS_DIR
from logs.log_searcher import (
    collect_logs,
    flatten_message_text,
    summarize,
)
from logs.log_storage import load_log
from logs.log_types import Event, EventType, LogDict, LogWhere
from logs.log_validator import validate_log
from logs.multi_info_logger import AppLogger
from logs.openai_key_store import delete_openai_api_key, has_openai_api_key, is_keyring_available, save_openai_api_key
from logs.result_exporter import (
    export_event_logs_to_csv,
    export_investigation_report_json,
    export_summary_to_csv,
    export_to_json,
)
from logs.search_ast import AndNode, EmptyNode, FieldNode, NotNode, OrNode, QueryNode
from logs.search_matcher import apply_result_modifiers, match_search_query, run_aggregate_query
from logs.search_models import AggregateResult, SearchQuery
from logs.search_text_analysis import parse_query
from logs.search_text_preprocessor import build_search_text_datetime
from logs.summary_bridge import summarize_logs_for_viewer
from logs.time_utils import to_world_local_datetime
from logs.traceql_bridge import build_traceql_query_error_text
from logs.tzinfo_formatter import TimeZoneData, TimeZoneItem, build_timezone_data
from summary_engine.summary_types import SummaryResult

WindowWidget = tk.Tk | tk.Toplevel
ParentWidget = tk.Tk | tk.Toplevel | tk.Frame | ttk.Frame
TypedContextValue = Mapping[str, object]


def _is_typed_context_value(value: object) -> TypeGuard[TypedContextValue]:
    """Loggerの {"type": ..., "value": ...} context値か判定する。"""
    if not isinstance(value, Mapping):
        return False
    mapping: Mapping[object, object] = cast(Mapping[object, object], value)
    return "type" in mapping and "value" in mapping


class LogViewer:
    """ログファイルを表示するGUI"""

    TRACE_ALL: Final[str] = "trace.id_ALL"
    TYPE_ALL: Final[str] = "type_ALL"
    def __init__(
        self,
        parent: tk.Tk,
        initial_log_path: Path | None = None,
        logger: AppLogger | None = None,
        language: LanguageCode = "ja",
    ) -> None:
        self.root: tk.Tk = parent
        self.viewer_config: dict[str, Any] = load_viewer_config()
        self.language: LanguageCode = normalize_language(
            str(self.viewer_config.get("language", language))
        )
        self.root.title(self._t("viewer_title"))
        self.root.geometry(self._load_window_geometry())
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        # 基本設定
        self.log_dir: Path = LOGS_DIR
        self.logger: AppLogger = logger or get_logger()

        # Viewer state responsibilities:
        # - raw_rows: 読み込んだ元ログの母集団。検索前の LogDict 全件。
        # - filtered_rows: raw_rows から LogDict 条件で絞った結果。集計や要約の入力。
        # - display_rows: Treeview / 詳細 / 出力が参照する唯一の表示本流 Event 群。
        #   一覧と詳細で Type 表示を一致させるため、表示系は必ず display_rows を参照する。
        # ----元ログ (raw)----
        # 正しく 読み込んだ元ログ LogDict 全件
        self.raw_rows: list[LogDict] = []
        # ----検索後ログ (filtered)----
        self.filtered_rows: list[LogDict] = []
        # ----Treeview表示用Event (display)----
        self.display_rows: list[Event] = []

        # ----- シングルクリックとダブルクリックの区別用 -----
        self._single_click_after_id: str | None = None
        # 仕様別フィルタ
        self.trace_var = tk.StringVar(value=self.TRACE_ALL)
        self.type_var = tk.StringVar(value=self.TYPE_ALL)
        # フォント指定
        self.font_title: tuple[str, int, str] = ("Yu Gothic UI", 12, "bold")
        self.font_normal: tuple[str, int] = ("Yu Gothic UI", 10)
        self.font_bold_normal: tuple[str, int, str] = ("Yu Gothic UI", 10, "bold")
        self.font_mono: tuple[str, int] = ("Cascadia Code", 10)
        # 型だけ宣言
        self.trace_dropdown: ttk.Combobox
        self.type_dropdown: ttk.Combobox
        self.tree: ttk.Treeview
        self.area_label: tk.Label
        self.city_label: tk.Label
        self.open_log_button: tk.Button
        self.open_logs_button: tk.Button
        self.reset_filters_button: tk.Button
        self.trace_label: tk.Label
        self.type_label: tk.Label
        self.search_label: tk.Label
        self.search_button: tk.Button
        self.summary_button: tk.Button
        self.export_csv_button: tk.Button
        self.export_json_button: tk.Button
        self.export_report_button: tk.Button
        self.search_var = tk.StringVar()
        self.aggregate_result_var = tk.StringVar()
        self.area_combo: ttk.Combobox
        self.city_combo: ttk.Combobox

        # ===== TimeZoneデータ =====
        self.tz_data: TimeZoneData = self._build_timezone_data_with_dialog()
        self.current_tz: str = self._load_timezone()
        self.current_area: str = self.current_tz.split("/", 1)[0]
        self._area_label_to_area: dict[str, str] = {}
        self._tz_label_to_zone: dict[str, str] = {}
        self.last_log_paths: list[Path] = []
        # area
        self.area_var = tk.StringVar()
        # city
        self.tz_var = tk.StringVar()
        # debag用
        print("DEBUG filtered_rows exists")
        # ===== 全体UI構築 =====
        self._build_ui()

        def get_latest_log_file(log_dir: Path) -> Path | None:
            """最新ログ取得"""

            log_files: list[Path] = sorted(
                [
                    p
                    for p in (
                        list(log_dir.glob("*.jsonl"))
                        + list(log_dir.glob("*.log"))
                    )
                    if p.stat().st_size > 0
                ],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            return log_files[0] if log_files else None

        configured_log_paths: list[Path] = self._load_log_paths_from_config()
        loaded_configured_logs = False
        if initial_log_path is None and configured_log_paths:
            if len(configured_log_paths) == 1:
                initial_log_path = configured_log_paths[0]
            else:
                logs: list[LogDict] = collect_logs(configured_log_paths)
                self._set_raw_rows(logs)
                self.last_log_paths = configured_log_paths
                self.update_filters()
                self.apply_filter()
                loaded_configured_logs = True

        latest_log: Path | None = get_latest_log_file(self.log_dir)
        print(f"DEBUG latest_log: {latest_log}")
        if not loaded_configured_logs and initial_log_path is None and latest_log is not None:
            initial_log_path = latest_log

        if not loaded_configured_logs and initial_log_path is not None:
            self.reload_log(initial_log_path)

    def _build_timezone_data_with_dialog(self) -> TimeZoneData:
        """TimezoneData更新中であることをユーザーに表示してから構築する。"""
        dialog = tk.Toplevel(self.root)
        dialog.title("TimeZoneData")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(
            dialog,
            text="現在、最新版のTimeZoneDataに書き換え中です。",
            padx=24,
            pady=18,
        ).pack()
        dialog.update_idletasks()

        root_x: int = self.root.winfo_rootx()
        root_y: int = self.root.winfo_rooty()
        root_width: int = max(self.root.winfo_width(), 1)
        root_height: int = max(self.root.winfo_height(), 1)
        dialog_width: int = dialog.winfo_width()
        dialog_height: int = dialog.winfo_height()
        x: int = root_x + (root_width - dialog_width) // 2
        y: int = root_y + (root_height - dialog_height) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.update()

        try:
            return build_timezone_data()
        finally:
            dialog.grab_release()
            dialog.destroy()

    def _load_window_geometry(self) -> str:
        """設定ファイルからウィンドウ位置/サイズを取得する。"""
        geometry: Any | None = self.viewer_config.get("window_geometry")
        if isinstance(geometry, str) and geometry:
            return geometry
        return "1200x650+100+100"

    def _load_timezone(self) -> str:
        """設定ファイルからTimezoneを取得する。"""
        timezone_name: Any | None = self.viewer_config.get("timezone")
        if isinstance(timezone_name, str) and timezone_name in {
            item.zone
            for items in self.tz_data.area_map.values()
            for item in items
        }:
            return timezone_name

        area: Any | None = self.viewer_config.get("timezone_area")
        city: Any | None = self.viewer_config.get("timezone_city")
        if isinstance(area, str) and isinstance(city, str):
            legacy_timezone: str = f"{area}/{city}"
            if legacy_timezone in {
                item.zone
                for items in self.tz_data.area_map.values()
                for item in items
            }:
                return legacy_timezone

        return "Asia/Tokyo" if "Asia" in self.tz_data.area_map else self.tz_data.area_list[0]

    def _load_log_paths_from_config(self) -> list[Path]:
        """設定ファイルから前回開いていたログファイル一覧を取得する。"""
        paths_value: Any | None = self.viewer_config.get("last_log_paths")
        if not isinstance(paths_value, list):
            legacy_path: Any | None = self.viewer_config.get("last_log_path")
            paths_value = [legacy_path] if isinstance(legacy_path, str) else []

        paths_value = cast(list[Any], paths_value)

        paths: list[Path] = []
        for value in paths_value:
            if not isinstance(value, str):
                continue
            path = Path(value)
            if path.exists() and path.is_file():
                paths.append(path)
        return paths

    def _save_current_config(self) -> None:
        """現在のViewer設定をJSONへ保存する。"""
        config: dict[str, Any] = dict(self.viewer_config)
        area:str
        city:str
        area, city = (
            self.current_tz.split("/", 1)
            if "/" in self.current_tz
            else (self.current_tz, "")
        )
        config.update(
            {
                "language": self.language,
                "timezone": self.current_tz,
                "timezone_area": area,
                "timezone_city": city,
                "window_geometry": self.root.geometry(),
                "last_log_paths": [str(path) for path in self.last_log_paths],
            }
        )
        save_viewer_config(config)
        self.viewer_config = config

    def _t(self, key: str) -> str:
        """現在の表示言語に合わせたUI文字列を返す。"""
        return translate(key, self.language)

    def set_language(self, language: LanguageCode) -> None:
        """LogViewerの操作UI表示言語を切り替える。"""
        self.language = language
        self._build_menu()
        self._refresh_ui_text()
        self._refresh_timezone_dropdown()

    def set_timezone(self, timezone_name: str) -> None:
        """表示TimezoneをIANA名で切り替える。"""
        if "/" not in timezone_name:
            return
        area: str = timezone_name.split("/", 1)[0]
        if area not in self.tz_data.area_map:
            return
        if not any(item.zone == timezone_name for item in self.tz_data.area_map[area]):
            return
        self.current_tz = timezone_name
        self.current_area = area
        self._refresh_timezone_dropdown()

    def _refresh_ui_text(self) -> None:
        """既に作成済みの操作UI文字列を更新する。"""
        self.root.title(self._t("viewer_title"))
        self.area_label.config(text=self._t("label_area"))
        self.city_label.config(text=self._t("label_city"))
        self.open_log_button.config(text=self._t("button_open_single_log"))
        self.open_logs_button.config(text=self._t("button_open_multiple_logs"))
        self.reset_filters_button.config(text=self._t("button_reset_filters"))
        self.trace_label.config(text=self._t("label_trace"))
        self.type_label.config(text=self._t("label_type"))
        self.search_label.config(text=self._t("label_search"))
        self.search_button.config(text=self._t("button_search"))
        self.tree.heading("type", text=self._t("column_type"))
        self.tree.heading("time", text=self._t("column_time"))
        self.tree.heading("trace_id", text=self._t("column_trace_id"))
        self.tree.heading("message", text=self._t("column_message"))

    def _area_label(self, area: str) -> str:
        """現在の表示言語に合わせたTimezoneエリア名を返す。"""
        return translate_timezone_area(area, self.language)

    def _tz_label(self, item: TimeZoneItem) -> str:
        """現在の表示言語に合わせたTimezone都市名を返す。"""
        return build_timezone_label(item.zone, self.language)

    def _refresh_timezone_dropdown(self) -> None:
        """Timezoneドロップダウンの表示言語を更新する。"""
        if not hasattr(self, "area_combo") or not hasattr(self, "city_combo"):
            return

        self._area_label_to_area = {
            self._area_label(area): area
            for area in self.tz_data.area_list
        }
        self.area_combo["values"] = list(self._area_label_to_area.keys())
        self.area_var.set(self._area_label(self.current_area))
        self._set_timezone_city_values(self.current_area, self.current_tz)

    def _set_timezone_city_values(
        self,
        area: str,
        selected_zone: str | None = None,
    ) -> None:
        """選択中エリアに合わせて都市リストを更新する。"""
        items: list[TimeZoneItem] = self.tz_data.area_map.get(area, [])
        self._tz_label_to_zone = {
            self._tz_label(item): item.zone
            for item in items
        }
        labels: list[str] = list(self._tz_label_to_zone.keys())
        self.city_combo["values"] = labels

        if not labels:
            self.tz_var.set("")
            return

        selected_label: str = next(
            (
                self._tz_label(item)
                for item in items
                if item.zone == selected_zone
            ),
            labels[0],
        )
        self.tz_var.set(selected_label)

    # =======================
    # TZ DropDown List
    # =======================
    def _build_timezone_dropdown(
        self,
        parent_frame: ParentWidget,
    ) -> None:
        """TimeZoneドロップダウン作成"""

        frame = tk.Frame(parent_frame)
        frame.pack(pady=5)

        # ======================
        # Area
        # ======================
        self.area_label = tk.Label(frame, text=self._t("label_area"))
        self.area_label.pack(side=tk.LEFT)

        if self.current_area not in self.tz_data.area_map:
            self.current_area = "Asia" if "Asia" in self.tz_data.area_map else self.tz_data.area_list[0]
        self.area_var.set(self._area_label(self.current_area))
        self._area_label_to_area = {
            self._area_label(area): area
            for area in self.tz_data.area_list
        }

        self.area_combo = ttk.Combobox(
            frame,
            textvariable=self.area_var,
            values=list(self._area_label_to_area.keys()),
            state="readonly",
            width=15,
        )

        self.area_combo.pack(side=tk.LEFT, padx=(4, 12))

        # ======================
        # City
        # ======================
        self.city_label = tk.Label(frame, text=self._t("label_city"))
        self.city_label.pack(side=tk.LEFT)

        self.city_combo = ttk.Combobox(
            frame,
            textvariable=self.tz_var,
            values=[],
            state="readonly",
            width=35,
        )

        self.city_combo.pack(side=tk.LEFT, padx=(4, 12))

        # ======================
        # Event
        # ======================
        self.area_combo.bind(
            "<<ComboboxSelected>>",
            self._on_area_changed,
        )

        self.city_combo.bind(
            "<<ComboboxSelected>>",
            self._on_timezone_changed,
        )
        self._set_timezone_city_values(self.current_area, self.current_tz)

    def _on_area_changed(
        self,
        _event: tk.Event,
    ) -> None:
        """Area変更時"""
        selected_area_label: str = self.area_var.get()
        selected_area: str = (
            self._area_label_to_area.get(selected_area_label, selected_area_label)
        )
        self.current_area = selected_area
        self._set_timezone_city_values(selected_area)
        self._on_timezone_changed(_event)

    def _on_timezone_changed(
        self,
        _event: tk.Event,
    ) -> None:
        """TimeZone変更時"""

        selected_label: str = self.tz_var.get()

        self.current_tz = self._tz_label_to_zone.get(
            selected_label,
            self.current_tz,
        )

        # 👉 ここで再描画（重要）
        self.apply_filter()

    def open_summary_window(self) -> None:
        """要約ウインドウを開く"""
        summary_logs: list[LogDict] = self._display_raw_rows()
        if not summary_logs:
            messagebox.showinfo(self._t("summary_no_logs_title"), self._t("summary_no_logs_message"))
            return

        result: SummaryResult = summarize_logs_for_viewer(
            summary_logs,
            self.search_var.get(),
            self.current_tz,
        )
        SummaryWindow(self.root, result, self.language)

    def export_filtered_events_csv(self) -> None:
        """検索結果からEvent化できた有意ログをCSVへ保存する。"""
        events: list[Event] = list(self.display_rows)
        if not events:
            messagebox.showinfo(self._t("export_no_events_title"), self._t("export_no_events_message"))
            return

        output_path: Path | None = export_event_logs_to_csv(events)
        if output_path is None:
            return
        messagebox.showinfo(
            self._t("export_complete_title"),
            self._t("export_complete_message").format(path=output_path),
        )

    def export_filtered_bundle_json(self) -> None:
        """検索結果Eventと要約をJSONへ保存する。"""
        events: list[Event] = list(self.display_rows)
        if not events:
            messagebox.showinfo(self._t("export_no_events_title"), self._t("export_no_events_message"))
            return

        logs: list[LogDict] = self._display_raw_rows()
        summary: SummaryResult = summarize_logs_for_viewer(
            logs,
            self.search_var.get(),
            self.current_tz,
        )
        output_path: Path | None = export_to_json(
            logs=logs,
            events=events,
            summary=summary,
        )
        if output_path is None:
            return
        messagebox.showinfo(
            self._t("export_complete_title"),
            self._t("export_complete_message").format(path=output_path),
        )

    def export_investigation_report(self) -> None:
        """検索条件・Event・要約を調査レポートJSONへ保存する。"""
        events: list[Event] = list(self.display_rows)
        if not events:
            messagebox.showinfo(self._t("export_no_events_title"), self._t("export_no_events_message"))
            return

        logs: list[LogDict] = self._display_raw_rows()
        summary: SummaryResult = summarize_logs_for_viewer(
            logs,
            self.search_var.get(),
            self.current_tz,
        )
        output_path: Path | None = export_investigation_report_json(
            logs=logs,
            events=events,
            summary=summary,
            condition_text=self.search_var.get(),
            timezone_name=self.current_tz,
            source_files=self.last_log_paths,
        )
        if output_path is None:
            return
        messagebox.showinfo(
            self._t("export_complete_title"),
            self._t("export_complete_message").format(path=output_path),
        )

    # =======================
    # UI構築(メイン・ウインド)
    # =======================
    def _build_ui(self) -> None:
        """UIを構築する"""
        self._build_menu()

        # =========================
        # 🔹 上部ボタン
        # =========================
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        self.open_log_button = tk.Button(top_frame, text=self._t("button_open_single_log"), command=self.open_log_file)
        self.open_log_button.pack(side=tk.LEFT)
        self.open_logs_button = tk.Button(top_frame, text=self._t("button_open_multiple_logs"), command=self.open_logs)
        self.open_logs_button.pack(side=tk.LEFT, padx=8)
        self.reset_filters_button = tk.Button(top_frame, text=self._t("button_reset_filters"), command=self.reset_filters)
        self.reset_filters_button.pack(side=tk.LEFT)
        #=====Timezone Dropdown=====
        self._build_timezone_dropdown(top_frame)
        # =========================
        # 🔹 フィルタ
        # =========================
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        # trace_idのドロップダウン
        self.trace_label = tk.Label(filter_frame, text=self._t("label_trace"))
        self.trace_label.pack(side=tk.LEFT)
        self.trace_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.trace_var,
            state="readonly",
            width=35,
        )
        self.trace_dropdown.pack(side=tk.LEFT, padx=(4, 12))
        self.trace_dropdown.bind("<<ComboboxSelected>>", self.apply_filter)
        # typeのドロップダウン
        self.type_label = tk.Label(filter_frame, text=self._t("label_type"))
        self.type_label.pack(side=tk.LEFT)
        self.type_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.type_var,
            state="readonly",
            width=20,
        )
        self.type_dropdown.pack(side=tk.LEFT, padx=(4, 12))
        self.type_dropdown.bind("<<ComboboxSelected>>", self.apply_filter)

        # 検索窓と検索ボタン
        self.search_label = tk.Label(filter_frame, text=self._t("label_search"))
        self.search_label.pack(side=tk.LEFT)
        # Enterキーで検索実行
        self.search_entry = tk.Entry(
            filter_frame,
            textvariable=self.search_var,
            width=30,
        )
        self.search_entry.pack(
            side=tk.LEFT,
            padx=(4, 12),
        )
        self.search_entry.bind(
            "<Return>",
            lambda _event: self.apply_filter(),
        )

        # 検索ボタンで検索実行
        self.search_button = tk.Button(filter_frame, text=self._t("button_search"), command=self.apply_filter)
        self.search_button.pack(side=tk.LEFT)

        # 要約ボタン
        self.summary_button = tk.Button(
            filter_frame,
            text=self._t("button_summary"),
            command=self.open_summary_window,
        )
        self.summary_button.pack(side=tk.LEFT, padx=(8, 0))
        # エクスポートボタン
        self.export_csv_button = tk.Button(
            filter_frame,
            text=self._t("button_export_result_csv"),
            command=self.export_filtered_events_csv,
        )
        self.export_csv_button.pack(side=tk.LEFT, padx=(8, 0))
        # JSONエクスポート
        self.export_json_button = tk.Button(
            filter_frame,
            text=self._t("button_export_result_json"),
            command=self.export_filtered_bundle_json,
        )
        self.export_json_button.pack(side=tk.LEFT, padx=(8, 0))
        # 調査レポートエクスポート
        self.export_report_button = tk.Button(
            filter_frame,
            text=self._t("button_export_report"),
            command=self.export_investigation_report,
        )
        self.export_report_button.pack(side=tk.LEFT, padx=(8, 0))
        # 集計結果表示用ラベル
        tk.Label(
            filter_frame,
            textvariable=self.aggregate_result_var,
            anchor="w",
            fg="#005a9e",
        ).pack(side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True)

        # =========================
        # 🔥 Tree専用フレーム（重要）
        # =========================
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # 🔹 Scrollbar
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # 🔹 Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "time", "trace_id", "message"),
            show="headings",
            yscrollcommand=scrollbar.set,
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.tree.yview)  # type: ignore[arg-type]

        # =========================
        # 🔹 カラム設定
        # =========================
        self.tree.heading("type", text=self._t("column_type"))
        self.tree.heading("time", text=self._t("column_time"))
        self.tree.heading("trace_id", text=self._t("column_trace_id"))
        self.tree.heading("message", text=self._t("column_message"))

        self.tree.column("type", width=120, anchor="w")
        self.tree.column("time", width=180, anchor="w")
        self.tree.column("trace_id", width=250, anchor="w")
        self.tree.column("message", width=640, anchor="w")
        # 通常（INFO）
        self.tree.tag_configure(
            "INFO",
            foreground="#222222",
            font=self.font_normal,
            background="#ffffff",
        )

        # WARNING（注意）
        self.tree.tag_configure(
            "WARNING",
            foreground="#b26a00",
            font=self.font_normal,
            background="#fff4cc",
        )

        # ERROR（エラー）
        self.tree.tag_configure(
            "ERROR",
            foreground="#b00020",
            font=self.font_bold_normal,
            background="#ffe5e5",
        )

        # CRITICAL（致命）
        self.tree.tag_configure(
            "CRITICAL",
            foreground="#ffffff",
            font=self.font_bold_normal,
            background="#d32f2f",
        )

        # REPEAT_ERROR（繰り返しエラー）
        self.tree.tag_configure(
            "REPEAT_ERROR",
            foreground="#ffe0b2",
            font=self.font_bold_normal,
            background="#e65100",  # オレンジ強め🔥
        )

        # TRACE_JUMP（分析系）
        self.tree.tag_configure(
            "TRACE_JUMP",
            foreground="#5e35b1",
            font=self.font_normal,
            background="#f3e8ff",
        )

        # REBOOT（システム系）
        self.tree.tag_configure(
            "REBOOT",
            foreground="#6d4c41",
            font=self.font_normal,
            background="#efebe9",
        )
        # 初期フォーカスを検索窓へ
        self.search_entry.focus_set()

        self.tree.bind("<ButtonRelease-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double_click)


    def open_fv_recipe(self) -> None:
        """FVレシピを読み込む。"""

        file_path_str: str = filedialog.askopenfilename(
            title=self._t("dialog_select_fv_recipe"),
            initialdir=str(self.log_dir),
            filetypes=[
                ("FV Recipe", "*.fv"),
                ("Markdown", "*.md"),
                ("All Files", "*.*"),
            ],
        )

        if not file_path_str:
            return

        recipe_path: Path = Path(file_path_str)

        if not recipe_path.exists():
            messagebox.showerror(
                self._t("fv_recipe_not_found_title"),
                self._t("fv_recipe_not_found_message").format(path=recipe_path),
            )
            return

        try:
            recipe_text: str = recipe_path.read_text(encoding="utf-8")

            recipe: FVRecipe = parse_fv_text(recipe_text)

            execution_plan: ExecutionPlan = build_execution_plan(recipe)

            self.search_var.set(execution_plan.query)
            self.apply_filter()

            # messagebox.showinfo(
            #     "FV Recipe Loaded",
            #     (f"TITLE : {recipe.title}\n\n" f"QUERY :\n{recipe.query}\n\n" f"SUMMARY : {recipe.summary.value}\n" f"EXPORT : {recipe.export.value}"),
            # )
            # print(f"DEBUG execution_plan: {execution_plan}")

            result: FVResult
            if self._query_uses_event_type(search_query=parse_query(execution_plan.query, self.current_tz)):
                result = self._build_fv_result_from_display_rows(execution_plan)
            else:
                result = run_execution_plan(
                    execution_plan,
                    self.raw_rows,
                    timezone=self.current_tz,
                )

            if result.summary is not None:
                SummaryWindow(
                    self.root,
                    result.summary,
                    self.language,
                )
            print(f"DEBUG fv_result: {result}")

        except Exception as e:
            messagebox.showerror(
                self._t("fv_recipe_open_error_title"),
                str(e),
            )

    def _open_external_file(self, file_path: Path) -> None:
        """OSの関連付けでファイルを開く。"""
        if os.name == "nt":
            os.startfile(file_path)  # type: ignore[attr-defined]
            return

        opener: str = "open" if sys.platform == "darwin" else "xdg-open"
        if subprocess.run([opener, str(file_path)], check=False).returncode != 0:
            raise RuntimeError(f"Failed to open {file_path}")

    def _build_menu(self) -> None:
        """メインメニューを構築する。"""
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label=self._t("menu_open_log"), command=self.open_log_file)
        file_menu.add_command(label=self._t("menu_open_multiple_logs"), command=self.open_logs)
        file_menu.add_command(label=self._t("menu_open_fv_recipe"), command=self.open_fv_recipe)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_exit"), command=self.exit_app)

        app_menu = tk.Menu(menu_bar, tearoff=False)
        app_menu.add_command(
            label=self._t("menu_register_api_key"),
            command=self.open_openai_api_key_dialog,
        )
        app_menu.add_command(label=self._t("menu_options"), command=self.open_options_dialog)

        language_menu = tk.Menu(menu_bar, tearoff=False)
        language_menu.add_command(label=self._t("language_japanese"), command=lambda: self.set_language("ja"))
        language_menu.add_command(label=self._t("language_english"), command=lambda: self.set_language("en"))

        menu_bar.add_cascade(label=self._t("menu_file"), menu=file_menu)
        menu_bar.add_cascade(label=self._t("menu_app"), menu=app_menu)
        menu_bar.add_cascade(label=self._t("menu_language"), menu=language_menu)
        self.root.config(menu=menu_bar)

    def open_openai_api_key_dialog(self) -> None:
        """OpenAI API Key登録ダイアログを開く。"""
        window = tk.Toplevel(self.root)
        window.title(self._t("dialog_api_key_title"))
        window.geometry("520x220")
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        status_text: str = (
            self._t("dialog_api_key_saved_status")
            if has_openai_api_key()
            else self._t("dialog_api_key_missing_status")
        )

        tk.Label(window, text=status_text, anchor="w").pack(
            fill=tk.X,
            padx=16,
            pady=(14, 8),
        )
        tk.Label(
            window,
            text=self._t("dialog_api_key_storage_note"),
            anchor="w",
            fg="#555555",
        ).pack(fill=tk.X, padx=16, pady=(0, 10))

        input_frame = tk.Frame(window)
        input_frame.pack(fill=tk.X, padx=16)

        tk.Label(input_frame, text=self._t("dialog_api_key_label")).pack(side=tk.LEFT)
        key_var = tk.StringVar()
        key_entry = tk.Entry(input_frame, textvariable=key_var, show="*", width=54)
        key_entry.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        key_entry.focus_set()

        button_frame = tk.Frame(window)
        button_frame.pack(fill=tk.X, padx=16, pady=18)

        def on_save() -> None:
            """API Key保存処理"""
            api_key: str = key_var.get().strip()
            if not api_key:
                messagebox.showwarning(self._t("dialog_input_check"), self._t("dialog_api_key_required"), parent=window)
                return
            if not is_keyring_available():
                messagebox.showerror(
                    self._t("dialog_keyring_required_title"),
                    self._t("dialog_keyring_required_save"),
                    parent=window,
                )
                return
            save_openai_api_key(api_key)
            messagebox.showinfo(self._t("dialog_save_complete"), self._t("dialog_api_key_saved"), parent=window)
            window.destroy()

        def on_delete() -> None:
            """API Key削除処理"""
            if not is_keyring_available():
                messagebox.showerror(
                    self._t("dialog_keyring_required_title"),
                    self._t("dialog_keyring_required_delete"),
                    parent=window,
                )
                return
            delete_openai_api_key()
            messagebox.showinfo(self._t("dialog_delete_complete"), self._t("dialog_api_key_deleted"), parent=window)
            window.destroy()

        tk.Button(button_frame, text=self._t("button_save"), command=on_save).pack(side=tk.LEFT)
        tk.Button(button_frame, text=self._t("button_delete"), command=on_delete).pack(side=tk.LEFT, padx=8)
        tk.Button(button_frame, text=self._t("button_cancel"), command=window.destroy).pack(side=tk.RIGHT)

        window.wait_window()

    def open_options_dialog(self) -> None:
        """検索オプションダイアログを開く。"""
        window = tk.Toplevel(self.root)
        window.title(self._t("dialog_options_title"))
        window.geometry("520x180")
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        key_status: str = self._t("option_api_key_registered") if has_openai_api_key() else self._t("option_api_key_missing")
        messages: list[str] = [
            self._t("option_similar_search"),
            self._t("option_api_key_status").format(status=key_status),
            self._t("option_local_similarity_note"),
            self._t("option_embeddings_future"),
        ]
        for message in messages:
            tk.Label(window, text=message, anchor="w").pack(fill=tk.X, padx=16, pady=3)

        tk.Button(window, text=self._t("button_close"), command=window.destroy).pack(pady=14)
        window.wait_window()

    def exit_app(self) -> None:
        """アプリを終了する。"""
        self._save_current_config()
        self.root.destroy()

    def reload_log(self, path: Path) -> None:
        """単一ログファイルを再読み込み"""
        self.last_log_paths = [path]

        # ① 生ログ（dict）
        raw_logs: list[dict[str, Any]] = load_log(path)

        # 🔥 ここが重要
        safe_logs: list[LogDict] = []
        for raw in raw_logs:
            log: LogDict | None = validate_log(raw)
            if log is not None:
                safe_logs.append(log)

        # ③ Viewerにセット
        self._set_raw_rows(safe_logs)

        self.update_filters()
        self.apply_filter()

    def open_log_file(self) -> None:
        """ファイルダイアログから単一ログを開く"""

        file_path_str: str = filedialog.askopenfilename(
            title=self._t("dialog_select_log_file"),
            initialdir=str(self.log_dir),
            filetypes=[("Log Files", "*.jsonl *.log"), ("All Files", "*.*")],
        )

        if not file_path_str:
            return

        # 🔹 searcher経由で取得（統一）
        logs: list[LogDict] = collect_logs([Path(file_path_str)])

        self._set_raw_rows(logs)
        self.last_log_paths = [Path(file_path_str)]
        self.update_filters()
        self.apply_filter()

    def open_logs(self) -> None:
        """複数ログを選択して開く"""
        selector = LogFileSelector(self.root, self.log_dir)
        paths: list[Path] | None = selector.show()

        if paths is None:
            return

        # 🔹 データ取得はsearcherに任せる
        logs: list[LogDict] = collect_logs(paths)

        # 🔹 Viewerは表示だけ
        self._set_raw_rows(logs)
        self.last_log_paths = paths
        self.update_filters()
        self.apply_filter()

    def update_filters(self) -> None:
        """フィルタ候補を更新する"""
        trace_ids: list[str] = sorted(
            {
                self._get_log_trace_id(row)
                for row in self.raw_rows
            }
        )
        types: list[str] = sorted(
            {
                candidate
                for row in self.raw_rows
                for candidate in self._get_log_type_candidates(row)
            }
        )
        event_types: list[str] = sorted(
            {
                candidate
                for event in summarize(self.raw_rows)
                for candidate in self._get_event_type_candidates(event)
            }
        )
        types = sorted(set(types) | set(event_types))

        self.trace_dropdown["values"] = [self.TRACE_ALL] + trace_ids
        self.type_dropdown["values"] = [self.TYPE_ALL] + types

        self.trace_var.set(self.TRACE_ALL)
        self.type_var.set(self.TYPE_ALL)

    def reset_filters(self) -> None:
        """フィルタを解除する"""
        self.trace_var.set(self.TRACE_ALL)
        self.type_var.set(self.TYPE_ALL)
        self.apply_filter()

    def _get_log_trace_id(
        self,
        row: LogDict,
    ) -> str:
        """LogDictからtrace_id取得"""
        return row["trace_id"]

    def _get_log_message(
        self,
        row: LogDict,
    ) -> str:
        """LogDictからmessage取得"""
        return row["what"]["message"]

    def _get_log_type(
        self,
        row: LogDict,
    ) -> str:
        """LogDictからlevel取得"""
        return row["level"]

    def _get_log_type_candidates(
        self,
        row: LogDict,
    ) -> set[str]:
        """LogDictが type 候補として持つ値を返す。"""
        candidates: set[str] = {self._get_log_type(row)}
        message_text: str = flatten_message_text(row.get("what", {}).get("message", ""))
        if message_text:
            candidates.add(message_text)
        return candidates

    def _get_event_display_type(
        self,
        row: Event,
    ) -> str:
        """TreeviewのType列に表示する種別を取得する。"""
        if row.type is not None:
            return row.type.name
        message_text: str = flatten_message_text(row.raw.get("what", {}).get("message", ""))
        return message_text or row.level.name

    def _get_event_type_candidates(
        self,
        row: Event,
    ) -> set[str]:
        """Eventが type 条件で一致できる候補を返す。"""
        candidates: set[str] = {self._get_event_display_type(row)}
        message_text: str = flatten_message_text(row.raw.get("what", {}).get("message", ""))
        if row.type is None and message_text:
            candidates.add(message_text)
        return candidates

    def _set_raw_rows(
        self,
        logs: list[LogDict],
    ) -> None:
        """元ログを差し替え、分析キャッシュを無効化する。"""
        self.raw_rows = logs
        self.filtered_rows = []
        self.display_rows = []

    def _filter_event_rows(
        self,
        event_rows: list[Event],
        trace_filter: str,
        type_filter: str,
        search_query: SearchQuery,
        tz: str,
    ) -> list[Event]:
        """Eventベース検索を適用する。"""
        display_rows: list[Event] = []
        for event_row in event_rows:
            row_trace_id: str = str(event_row.trace_id)
            if trace_filter != self.TRACE_ALL and row_trace_id != trace_filter:
                continue
            if type_filter != self.TYPE_ALL and type_filter not in self._get_event_type_candidates(event_row):
                continue
            if not self._match_event_search_query(event_row, search_query, tz):
                continue
            display_rows.append(event_row)
        return display_rows

    def _match_event_search_query(
        self,
        row: Event,
        query: SearchQuery,
        tz: str,
    ) -> bool:
        """表示Eventを検索条件で判定する。"""
        if not query.raw_text.strip():
            return True
        if query.aggregate is not None:
            return match_search_query(row.raw, query, tz)
        if query.ast_root is None:
            return match_search_query(row.raw, query, tz)
        return self._match_event_query_node(row, query.ast_root, query, tz)

    def _match_event_query_node(
        self,
        row: Event,
        node: QueryNode,
        query: SearchQuery,
        tz: str,
    ) -> bool:
        """Event.type を含む検索ASTを判定する。"""
        if isinstance(node, EmptyNode):
            return True
        if isinstance(node, FieldNode):
            field: str = node.field.lower()
            value: str = node.value.lower()
            if field == "type":
                return any(candidate.lower() == value for candidate in self._get_event_type_candidates(row))
            if field == "level":
                return row.level.name.lower() == value
        if isinstance(node, NotNode):
            return not self._match_event_query_node(row, node.child, query, tz)
        if isinstance(node, AndNode):
            return self._match_event_query_node(row, node.left, query, tz) and self._match_event_query_node(row, node.right, query, tz)
        if isinstance(node, OrNode):
            return self._match_event_query_node(row, node.left, query, tz) or self._match_event_query_node(row, node.right, query, tz)

        node_query = SearchQuery(raw_text=query.raw_text, ast_root=node)
        return match_search_query(row.raw, node_query, tz)

    def _build_fv_result_from_display_rows(
        self,
        plan: ExecutionPlan,
    ) -> FVResult:
        """Event.type検索時のFVResultをViewer表示結果から生成する。"""
        matched_events: list[Event] = list(self.display_rows)
        matched_logs: list[LogDict] = self._display_raw_rows()
        summary: SummaryResult | None = None
        if plan.run_summary:
            summary = summarize_logs_for_viewer(
                matched_logs,
                plan.query,
                self.current_tz,
            )

        export_file_path: Path | None = None
        if plan.export_format is FVExportFormat.CSV:
            export_file_path = export_event_logs_to_csv(
                matched_events,
                plan.output_file_path,
            )
        elif plan.export_format is FVExportFormat.JSON:
            export_file_path = export_to_json(
                logs=matched_logs,
                events=matched_events,
                summary=summary,
                save_file_path=plan.output_file_path,
            )
        elif plan.export_format is not FVExportFormat.NONE:
            raise ValueError(f"未対応のEXPORT形式です: {plan.export_format}")

        return FVResult(
            recipe=plan.recipe,
            matched_count=len(matched_events),
            summary=summary,
            export_file_path=export_file_path,
        )

    def _searchtext_datetime_builder(
        self,
        search_text: str,
    ) -> str:
        """時間だけの検索文字列をdatetime形式へ補完する"""
        return build_search_text_datetime(search_text, self.raw_rows, self.current_tz)


    def apply_filter(self, _event: tk.Event | None = None) -> None:
        """フィルタに応じて表示内容を更新する"""
        trace_filter: str = self.trace_var.get()
        type_filter: str = self.type_var.get()
        search_text: str = self.search_var.get().strip()
        tz: str = self.current_tz
        search_text = self._searchtext_datetime_builder(search_text)
        search_query: SearchQuery = parse_query(search_text, tz)
        self.aggregate_result_var.set("")
        self.filtered_rows = []
        self.display_rows = []

        # debag用
        self.logger.debug(
            "apply_filter start",
            context={
                "start_time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "search": search_text,
                "raw_rows": len(self.raw_rows),
                "display_rows": len(self.display_rows),
            },
        )

        # 🔹 画面クリア
        self.tree.delete(*self.tree.get_children())

        event_rows: list[Event] = summarize(self.raw_rows)
        self.display_rows = self._filter_event_rows(
            event_rows,
            trace_filter,
            type_filter,
            search_query,
            tz,
        )
        self.filtered_rows = self._display_raw_rows()

        self.logger.debug(
            "filter completed",
            context={
                "filtered_count": len(self.filtered_rows),
                "display_count": len(self.display_rows),
            },
        )

        # debag用
        try:
            self.logger.debug(
                "filtered_rows prepared",
                context={
                    "filtered_rows": len(self.filtered_rows),
                },
            )

        except Exception as e:
            self.logger.error(
                "apply_result_modifiers failed",
                context={
                    "error": str(e),
                    },
                )

        # 🔹 表示
        display_index = 0
        for row in self.display_rows:
            row_trace_id = str(row.trace_id)
            row_type = self._get_event_display_type(row)
            self.tree.insert(
                "",
                "end",
                iid=str(display_index),
                values=(
                    row_type,
                    self._format_world_local_time(row.time),
                    row_trace_id,
                    row.message,
                ),
                tags=(row_type,),
            )
            display_index += 1

        if search_query.aggregate is not None:
            result: AggregateResult = run_aggregate_query(self.filtered_rows, search_query.aggregate, tz)
            self.aggregate_result_var.set(result.message)
        else:
            self.aggregate_result_var.set("")


    def _format_world_local_time(self, value: Any) -> str:
        """UTCをworld_local時間文字列へ変換する"""
        dt: datetime | None = to_world_local_datetime(value, self.current_tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt is not None else str(value)


    def on_click(self, event: tk.Event) -> None:
        """シングルクリックで詳細表示"""
        event_row: Event | None = self._get_display_row(event)
        if event_row is None:
            return
        self._cancel_pending_single_click()
        self._single_click_after_id = self.root.after(
            200,
            lambda: self._open_detail(event_row),
        )


    def on_double_click(self, event: tk.Event) -> None:
        """ダブルクリックでVSCodeを開く"""
        self._cancel_pending_single_click()
        event_row: Event | None = self._get_display_row(event)
        if event_row is None:
            return
        # 🔥 LogDict → raw → where
        raw: LogDict = event_row.raw
        where: LogWhere = raw.get("where", {})
        file_path: str = str(where.get("file", ""))
        line_no: int = int(where.get("line", 1))
        self.open_in_vscode(file_path, line_no)


    def _cancel_pending_single_click(self) -> None:
        """予約済みのシングルクリック処理を取り消す"""
        if self._single_click_after_id is None:
            return
        self.root.after_cancel(self._single_click_after_id)
        self._single_click_after_id = None


    # ===============================
    # 🔹 Treeから表示Event取得
    # ===============================
    def _get_display_row(
        self,
        event: tk.Event,
    ) -> Event | None:
        """クリック位置から表示Event取得"""
        row_id: str = self.tree.identify_row(event.y)
        if not row_id:
            return None
        try:
            index = int(row_id)
        except ValueError:
            return None
        if index < 0 or index >= len(self.display_rows):
            return None
        return self.display_rows[index]


    # ===============================
    # 🔹 LogDict → Event変換
    # ===============================
    def _build_event(
        self,
        row: LogDict,
    ) -> Event | None:
        """単発LogDictからEvent生成"""
        events: list[Event] = summarize([row])
        if not events:
            return None
        return events[0]


    # ===============================
    # 🔹 複数LogDict → Event群
    # ===============================
    def _build_events(
        self,
        rows: list[LogDict],
    ) -> list[Event]:
        """複数LogDictからEvent群生成"""

        return summarize(rows)

    def _display_raw_rows(self) -> list[LogDict]:
        """表示中Eventから重複しないLogDictを取り出す。"""
        logs: list[LogDict] = []
        seen: set[int] = set()
        for event in self.display_rows:
            raw_id: int = id(event.raw)
            if raw_id in seen:
                continue
            seen.add(raw_id)
            logs.append(event.raw)
        return logs


    def extract_source_file(self, msg: str) -> tuple[str | None, int]:
        """messageから、filenameを抽出する"""
        _: str
        rest: str
        try:
            # ① 分割
            if "→" in msg:
                _, rest = msg.split("→", 1)
            elif "->" in msg:
                _, rest = msg.split("->", 1)
            else:
                return None, 1

            text: str = rest.strip()

            # ② Python辞書として評価（安全）
            data: dict[str, Any] = ast.literal_eval(text)

            # ③ where取得
            where: LogWhere = data.get("where", {})

            file_path: str | None = where.get("file")
            line_no: int = where.get("line", 1)

            return file_path, int(line_no)

        except Exception as e:
            print(f"extract error: {e}")  # デバッグ🔥
            return None, 1

    def _unwrap_context_value(self, value: object) -> object:
        """Loggerの型付きcontext値から実値を取り出す。"""

        if _is_typed_context_value(value):
            return value["value"]

        return value

    def _extract_context_source_file(self, raw: LogDict) -> tuple[str | None, int]:
        """context.row.where から実際の発生元sourceを抽出する。"""
        context: dict[str, Any] = raw.get("context", {})

        row: object = self._unwrap_context_value(context.get("row"))
        if not isinstance(row, dict):
            return None, 1
        row_dict: dict[str, Any] = cast(dict[str, Any], row)

        where_dict: dict[str, Any] = cast(dict[str, Any], row_dict.get("where", {}))

        file_path: Any | None = where_dict.get("file")
        line_no: int | None = where_dict.get("line", 1)
        if not file_path:
            return None, 1

        try:
            return str(file_path), int(line_no or 1)
        except (TypeError, ValueError):
            return str(file_path), 1

    def _build_query_error_text(self, raw: LogDict) -> str:
        """TraceQL/parser系エラーを人間向けに見やすく整形する。"""
        context: dict[str, Any] = raw.get("context", {})

        query: object = self._unwrap_context_value(context.get("search_text"))
        error: object = self._unwrap_context_value(context.get("error"))
        if not isinstance(query, str) or not query:
            return ""
        if not isinstance(error, str) or not error:
            return ""

        return build_traceql_query_error_text(query, error, self.raw_rows, self.current_tz)

    # ===============================
    # 🔹 詳細ウィンドウ表示
    # ===============================
    def _open_detail(
        self,
        event_row: Event,
    ) -> None:
        """選択されたログの詳細を表示する"""

        raw: LogDict = event_row.raw

        renderer = LogRenderer()

        # =========================
        # 🔹 ウィンドウ
        # =========================
        detail = tk.Toplevel(self.root)
        detail.title(self._t("dialog_detail_title"))
        detail.geometry("1000x800")

        # =========================
        # 🔹 メインフレーム
        # =========================
        frame = tk.Frame(detail)
        frame.pack(fill=tk.BOTH, expand=True)

        # =========================
        # 🔹 ボタンフレーム
        # =========================
        btn_frame = tk.Frame(frame)
        btn_frame.pack(anchor="w", padx=10, pady=10)

        # =========================
        # 🔹 where情報
        # =========================
        where: LogWhere = raw.get("where", {})

        file_path: str = str(where.get("file", ""))
        line_no: int = int(where.get("line", 1) or 1)

        # =========================
        # 🔹 Loggerボタン
        # =========================
        tk.Button(
            btn_frame,
            text=self._t("button_open_logger_vscode"),
            fg="#0066cc",
            cursor="hand2",
            width=24,
            command=lambda: self.open_in_vscode(
                file_path,
                line_no,
            ),
        ).pack(side=tk.LEFT, padx=5)

        # =========================
        # 🔹 Sourceボタン
        # =========================
        message: str = str(
            raw.get("what", {}).get("message", "")
        )

        src_file: str | None
        src_line: int

        src_file, src_line = self.extract_source_file(message)
        if not src_file:
            src_file, src_line = self._extract_context_source_file(raw)

        if src_file:

            tk.Button(
                btn_frame,
                text=self._t("button_open_source_vscode"),
                cursor="hand2",
                width=24,
                command=lambda: self.open_in_vscode(
                    src_file,
                    src_line,
                ),
            ).pack(side=tk.LEFT, padx=5)

        # =========================
        # 🔹 Textエリアフレーム
        # =========================
        text_frame = tk.Frame(frame)
        text_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10,
        )

        # =========================
        # 🔹 Scrollbar
        # =========================
        y_scrollbar = tk.Scrollbar(text_frame)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        x_scrollbar = tk.Scrollbar(
            text_frame,
            orient="horizontal",
        )
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # =========================
        # 🔹 Text Widget
        # =========================
        text_area = tk.Text(
            text_frame,
            wrap="none",
            font=("Consolas", 11),
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        text_area.pack(fill=tk.BOTH, expand=True)

        y_scrollbar.config(command=text_area.yview) # type: ignore[union-attr]
        x_scrollbar.config(command=text_area.xview) # type: ignore[union-attr]

        # =========================
        # 🔹 Summary
        # =========================
        summary_text: str = renderer.build_summary(
            event_row,
            self.current_tz,
        )
        query_error_text: str = self._build_query_error_text(raw)

        # =========================
        # 🔹 RAW
        # =========================
        display_raw: dict[str, Any] = renderer.build_raw(
            event_row
        )

        raw_text: str = json.dumps(
            display_raw,
            indent=2,
            ensure_ascii=False,
        )

        # =========================
        # 🔹 表示文字列
        # =========================
        detail_sections: list[str] = [summary_text]
        if query_error_text:
            detail_sections.append(query_error_text)
        detail_sections.append(
            "=" * 60
            + "\nRAW DATA\n"
            + "=" * 60
            + "\n\n"
            + raw_text
        )
        detail_text: str = "\n\n".join(detail_sections)

        # =========================
        # 🔹 Text挿入
        # =========================
        text_area.insert("1.0", detail_text)

        # =========================
        # 🔹 読み取り専用
        # =========================
        text_area.config(state="disabled")

    def open_in_vscode(self, file_path: str, line_no: int) -> None:
        """VSCodeで該当ファイルを開く"""
        if not file_path:
            return
        subprocess.run(["code", "-g", f"{file_path}:{line_no}"], check=False)


class SummaryWindow:
    """検索結果の要約をコピー可能なTextで表示するウィンドウ。"""

    def __init__(self, parent: WindowWidget, result: SummaryResult, language: LanguageCode) -> None:
        self.parent = parent
        self.result: SummaryResult = result
        self.language = language
        self.window = tk.Toplevel(parent)
        self.window.title(self._t("dialog_summary_title"))
        self.window.geometry("820x520")
        self.window.transient(parent)
        self._build_ui()

    def _t(self, key: str) -> str:
        return translate(key, self.language)

    def _build_ui(self) -> None:
        frame = tk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            button_frame,
            text=self._t("button_close"),
            command=self.window.destroy,
        ).pack(side=tk.RIGHT)
        tk.Button(
            button_frame,
            text=self._t("button_copy_summary"),
            command=self._copy_summary,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        tk.Button(
            button_frame,
            text=self._t("button_export_summary_json"),
            command=self._export_summary_json,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        tk.Button(
            button_frame,
            text=self._t("button_export_summary_csv"),
            command=self._export_summary_csv,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        y_scrollbar = tk.Scrollbar(frame)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = tk.Scrollbar(frame, orient="horizontal")
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        text_area = tk.Text(
            frame,
            wrap="none",
            font=("Consolas", 11),
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
            undo=False,
        )
        text_area.pack(fill=tk.BOTH, expand=True)
        y_scrollbar.config(command=text_area.yview)  # type: ignore[union-attr]
        x_scrollbar.config(command=text_area.xview)  # type: ignore[union-attr]

        text_area.insert("1.0", self.result.text)
        text_area.config(state="disabled")
        text_area.focus_set()

    def _copy_summary(self) -> None:
        self.window.clipboard_clear()
        self.window.clipboard_append(self.result.text)

    def _export_summary_csv(self) -> None:
        output_path: Path | None = export_summary_to_csv(self.result)
        if output_path is None:
            return
        messagebox.showinfo(
            self._t("export_complete_title"),
            self._t("export_complete_message").format(path=output_path),
            parent=self.window,
        )

    def _export_summary_json(self) -> None:
        output_path: Path | None = export_to_json(summary=self.result)
        if output_path is None:
            return
        messagebox.showinfo(
            self._t("export_complete_title"),
            self._t("export_complete_message").format(path=output_path),
            parent=self.window,
        )


if __name__ == "__main__":
    root = tk.Tk()
    latest_candidates: list[Path] = sorted(
        list(LOGS_DIR.glob("*.jsonl")) +
        list(LOGS_DIR.glob("*.log"))
    )
    initial_path: Path | None = latest_candidates[-1] if latest_candidates else None
    LogViewer(root, initial_path)
    root.mainloop()
