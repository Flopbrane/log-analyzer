# -*- coding: utf-8 -*-
# pylint: disable=W0718
"""ログ表示GUI（安定版）"""
#########################
# Author: F.Kurokawa
# Description:
# log_viewer
#########################

from __future__ import annotations

import ast
import json
import subprocess
import tkinter as tk
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Final, TypeGuard, cast

from logs.display_formatter import LogRenderer
from logs.language_selector import LanguageCode, build_timezone_label, normalize_language, translate, translate_timezone_area
from logs.log_app import get_logger
from logs.log_config import load_viewer_config, save_viewer_config
from logs.log_multi_select import LogFileSelector
from logs.log_paths import LOGS_DIR
from logs.log_searcher import collect_logs, summarize
from logs.log_storage import load_log
from logs.log_types import Event, LogDict, LogWhere
from logs.log_validator import validate_log
from logs.multi_info_logger import AppLogger
from logs.openai_key_store import delete_openai_api_key, has_openai_api_key, is_keyring_available, save_openai_api_key
from logs.query_error_bridge import build_query_error_text
from logs.search_matcher import apply_result_modifiers, match_search_query, run_aggregate_query
from logs.search_models import AggregateResult, SearchQuery
from logs.search_text_analysis import parse_query
from logs.search_text_preprocessor import build_search_text_datetime
from logs.summary_bridge import summarize_logs_for_viewer
from logs.time_utils import to_world_local_datetime
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
        # ----元ログ (raw)----
        self.raw_rows: list[LogDict] = []
        # ----検索後ログ (filtered)----
        self.filtered_rows: list[LogDict] = []
        # ----表示用Event (rows)----
        self.event_rows: list[Event] = []

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
        self.search_var = tk.StringVar()
        self.aggregate_result_var = tk.StringVar()

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
                self.raw_rows = logs
                self.event_rows = summarize(logs)
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
        if not self.filtered_rows:
            messagebox.showinfo(self._t("summary_no_logs_title"), self._t("summary_no_logs_message"))
            return

        result: SummaryResult = summarize_logs_for_viewer(
            self.filtered_rows,
            self.search_var.get(),
            self.current_tz,
        )
        SummaryWindow(self.root, result, self.language)

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

        self.search_label = tk.Label(filter_frame, text=self._t("label_search"))
        self.search_label.pack(side=tk.LEFT)
        tk.Entry(
            filter_frame,
            textvariable=self.search_var,
            width=30,
        ).pack(side=tk.LEFT, padx=(4, 12))

        self.search_button = tk.Button(filter_frame, text=self._t("button_search"), command=self.apply_filter)
        self.search_button.pack(side=tk.LEFT)

        self.summary_button = tk.Button(
            filter_frame,
            text=self._t("button_summary"),
            command=self.open_summary_window,
        )
        self.summary_button.pack(side=tk.LEFT, padx=(8, 0))
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

        self.tree.bind("<ButtonRelease-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double_click)

    def _build_menu(self) -> None:
        """メインメニューを構築する。"""
        menu_bar = tk.Menu(self.root)
        app_menu = tk.Menu(menu_bar, tearoff=False)
        app_menu.add_command(
            label=self._t("menu_register_api_key"),
            command=self.open_openai_api_key_dialog,
        )
        app_menu.add_command(label=self._t("menu_options"), command=self.open_options_dialog)
        app_menu.add_separator()
        app_menu.add_command(label=self._t("menu_exit"), command=self.exit_app)

        language_menu = tk.Menu(menu_bar, tearoff=False)
        language_menu.add_command(label=self._t("language_japanese"), command=lambda: self.set_language("ja"))
        language_menu.add_command(label=self._t("language_english"), command=lambda: self.set_language("en"))

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

        # Event化
        events: list[Event] = summarize(safe_logs)

        # ③ Viewerにセット
        self.raw_rows = safe_logs
        self.event_rows: list[Event] = events

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

        self.raw_rows = logs
        self.event_rows = summarize(logs)
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
        self.raw_rows = logs
        self.event_rows = summarize(logs)
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
                self._get_log_type(row)
                for row in self.raw_rows
            }
        )

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


    def _searchtext_datetime_builder(
        self,
        search_text: str,
    ) -> str:
        """時間だけの検索文字列をdatetime形式へ補完する"""
        return build_search_text_datetime(search_text, self.raw_rows, self.current_tz)


    def apply_filter(self, _event: tk.Event | None = None) -> None:
        """フィルタに応じて表示内容を更新する"""
        # logger:"AppLogger" = get_logger()
        trace_filter: str = self.trace_var.get()
        type_filter: str = self.type_var.get()
        search_text: str = self.search_var.get().strip()
        tz: str = self.current_tz
        search_text = self._searchtext_datetime_builder(search_text)
        search_query: SearchQuery = parse_query(search_text, tz)
        self.aggregate_result_var.set("")
        self.filtered_rows = []

        # debag用
        self.logger.debug(
            "apply_filter start",
            context={
                "start_time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "search": search_text,
                "raw_rows": len(self.raw_rows),
                "event_rows": len(self.event_rows),
            },
        )

        # 🔹 画面クリア
        self.tree.delete(*self.tree.get_children())

        for row in self.raw_rows:
            row_trace_id: str = self._get_log_trace_id(row)
            row_type: str = self._get_log_type(row)

            # 🔹 TRACEフィルタ
            if trace_filter != self.TRACE_ALL and row_trace_id != trace_filter:
                continue

            # 🔹 TYPEフィルタ
            if type_filter != self.TYPE_ALL and row_type != type_filter:
                continue
            
            # debag用
            # print(f"search_query: {search_query}")
            # print(f"time: {row['time']}")
            # print(f"row: {row}")
            # print(f"match_search_query: {match_search_query(row, search_query, tz)}")
            
            if not match_search_query(row, search_query, tz):
                continue

            # 🔹 表示
            self.filtered_rows.append(row)

        # debag用
        self.logger.debug(
            "filter completed",
            context={
                "filtered_count": len(self.filtered_rows),
                },
        )

        self.filtered_rows = apply_result_modifiers(self.filtered_rows, search_query, tz)

        # debag用
        try:
            self.logger.debug(
                "filtered_rows prepared",
                context={
                    "display_rows": len(self.filtered_rows),
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
        for row in self.filtered_rows:
            row_trace_id = self._get_log_trace_id(row)
            row_type = self._get_log_type(row)
            self.tree.insert(
                "",
                "end",
                iid=str(display_index),
                values=(
                    row_type,
                    self._format_world_local_time(row["time"]),
                    row_trace_id,
                    self._get_log_message(row),
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
        log_row: LogDict | None = self._get_row(event)
        if log_row is None:
            return
        self._cancel_pending_single_click()
        self._single_click_after_id = self.root.after(
            200,
            lambda: self._open_detail(log_row),
        )


    def on_double_click(self, event: tk.Event) -> None:
        """ダブルクリックでVSCodeを開く"""
        self._cancel_pending_single_click()
        filtered_row: LogDict | None = self._get_row(event)
        if filtered_row is None:
            return
        # 🔥 LogDict → raw → where
        raw: LogDict = filtered_row
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
    # 🔹 TreeからLogDict取得
    # ===============================
    def _get_row(
        self,
        event: tk.Event,
    ) -> LogDict | None:
        """クリック位置からLogDict取得"""
        row_id: str = self.tree.identify_row(event.y)
        if not row_id:
            return None
        try:
            index = int(row_id)
        except ValueError:
            return None
        if index < 0 or index >= len(self.filtered_rows):
            return None
        return self.filtered_rows[index]


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

        return build_query_error_text(query, error, self.raw_rows, self.current_tz)

    def _get_event(
        self,
        event: tk.Event,
    ) -> Event | None:
        """クリック位置からEvent取得"""

        row_id: str = self.tree.identify_row(event.y)

        if not row_id:
            return None

        try:
            index = int(row_id)
        except ValueError:
            return None

        if index < 0 or index >= len(self.event_rows):
            return None

        return self.event_rows[index]

    # ===============================
    # 🔹 詳細ウィンドウ表示
    # ===============================
    def _open_detail(
        self,
        filtered_row: LogDict,
    ) -> None:
        """選択されたログの詳細を表示する"""

        raw: LogDict = filtered_row

        # =========================
        # 🔹 Event化
        # =========================
        event_row: Event | None = self._build_event(raw)

        if event_row is None:
            return

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
        self.result = result
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


if __name__ == "__main__":
    root = tk.Tk()
    latest_candidates: list[Path] = sorted(
        list(LOGS_DIR.glob("*.jsonl")) +
        list(LOGS_DIR.glob("*.log"))
    )
    initial_path: Path | None = latest_candidates[-1] if latest_candidates else None
    LogViewer(root, initial_path)
    root.mainloop()
