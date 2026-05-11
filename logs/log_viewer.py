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
import re
import subprocess
import tkinter as tk
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any, Final, Literal

from zoneinfo import ZoneInfo

from logs.display_formatter import LogRenderer
from logs.log_paths import LOGS_DIR
from logs.log_searcher import collect_logs, summarize
from logs.log_storage import load_log
from logs.log_types import Event, LogDict, LogWhere
from logs.log_validator import validate_log
from logs.time_utils import (
    now_utc,
    to_world_local_datetime,
)
from logs.tzinfo_formatter import (
    TimeZoneData,
    TimeZoneItem,
    build_timezone_data,
)
from logs.viewer_searcher import match_search_query

WindowWidget = tk.Tk | tk.Toplevel
ParentWidget = tk.Tk | tk.Toplevel | tk.Frame | ttk.Frame

class LogFileSelector:
    """ログファイル一覧を表示し、複数選択させるダイアログ"""

    def __init__(self, parent: WindowWidget, log_dir: Path) -> None:
        self.parent = parent
        self.log_dir: Path = log_dir

    def show(self) -> list[Path] | None:
        """ログファイル一覧を表示し、選択結果を返す"""
        window = tk.Toplevel(self.parent)
        window.title("ログ選択")
        window.geometry("700x500")
        window.transient(self.parent) # window系のプロパティなので、Frameが入るとエラーになる
        window.grab_set()

        files: list[Path] = sorted(
            list(self.log_dir.glob("*.jsonl")) +
            list(self.log_dir.glob("*.log")),
            key=lambda p: p.name
        )

        if not files:
            tk.Label(window, text="ログファイルが見つかりません").pack(
                padx=12,
                pady=12,
                anchor="w",
            )
            tk.Button(window, text="閉じる", command=window.destroy).pack(pady=8)
            window.wait_window()
            return None

        listbox = tk.Listbox(
            window,
            selectmode=tk.MULTIPLE,
            width=100,
            height=20,
            exportselection=False,
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        for file_path in files:
            listbox.insert(tk.END, file_path.name)

        selected_paths: list[Path] = []

        def on_open() -> None:
            """選択したLog_Pathを読み込む"""
            indices: tuple[int, ...] = listbox.curselection() # type: ignore
            for index in indices:  # type: ignore
                selected_paths.append(files[index])
            window.destroy()

        def on_cancel() -> None:
            """キャンセルボタン処理"""
            window.destroy()

        button_frame = tk.Frame(window)
        button_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        tk.Button(button_frame, text="開く", command=on_open).pack(side=tk.LEFT)
        tk.Button(button_frame, text="キャンセル", command=on_cancel).pack(
            side=tk.LEFT,
            padx=8,
        )

        window.wait_window()
        return selected_paths if selected_paths else None


class LogViewer:
    """ログファイルを表示するGUI"""

    TRACE_ALL: Final[str] = "trace.id_ALL"
    TYPE_ALL: Final[str] = "type_ALL"

    def __init__(self, parent: tk.Tk, initial_log_path: Path | None = None) -> None:
        self.root: tk.Tk = parent
        self.root.title("Log Viewer")
        self.root.geometry("1200x650+100+100")
        # 基本設定
        self.log_dir: Path = LOGS_DIR

        # ----元ログ (raw)----
        self.raw_rows: list[LogDict] = []
        # ----検索後ログ (filtered)----
        self.filtered_rows: list[LogDict] = []
        # ----表示用Event (rows)----
        self.rows: list[Event] = []

        # ----- シングルクリックとダブルクリックの区別用 -----
        self._single_click_after_id: str | None = None
        # ------現在のUTC日時------
        self.base_utc_dt: datetime = now_utc() # UTCで運用
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
        self.search_var = tk.StringVar()

        # ===== TimeZoneデータ =====
        self.tz_data: TimeZoneData = build_timezone_data()
        self.current_tz: str = "Asia/Tokyo"
        # area
        self.area_var = tk.StringVar()
        # city
        self.tz_var = tk.StringVar()
        # debag用
        print("DEBUG filtered_rows exists")
        # ===== 全体UI構築 =====
        self._build_ui()


        if initial_log_path is not None:
            self.reload_log(initial_log_path)

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
        tk.Label(frame, text="Area:").pack(side=tk.LEFT)

        self.area_var.set("Asia")

        self.area_combo = ttk.Combobox(
            frame,
            textvariable=self.area_var,
            values=self.tz_data.area_list,
            state="readonly",
            width=15,
        )

        self.area_combo.pack(side=tk.LEFT, padx=(4, 12))

        # ======================
        # City
        # ======================
        tk.Label(frame, text="City:").pack(side=tk.LEFT)

        asia_items: list[TimeZoneItem] = self.tz_data.area_map["Asia"]

        tz_labels: list[str] = [item.label for item in asia_items]

        self.tz_var.set(
            next(
                (item.label for item in asia_items if item.zone == "Asia/Tokyo"),
                tz_labels[0],
            )
        )

        self.city_combo = ttk.Combobox(
            frame,
            textvariable=self.tz_var,
            values=tz_labels,
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

    def _on_area_changed(
        self,
        _event: tk.Event,
    ) -> None:
        """Area変更時"""
        selected_area: str = self.area_var.get()
        items: list[TimeZoneItem] = (
            self.tz_data.area_map.get(
                selected_area,
                [],
            )
        )
        labels: list[str] = [
            item.label
            for item in items
        ]
        self.city_combo["values"] = labels
        if labels:
            self.tz_var.set(labels[0])
        self._on_timezone_changed(_event)

    def _on_timezone_changed(
        self,
        _event: tk.Event,
    ) -> None:
        """TimeZone変更時"""

        selected_label: str = self.tz_var.get()

        for items in self.tz_data.area_map.values():
            for item in items:
                if item.label == selected_label:
                    self.current_tz = item.zone
                    break

        # 👉 ここで再描画（重要）
        self.apply_filter()

    # =======================
    # 内部の比較は、全てUTCで運用
    # =======================
    def to_utc_search_dt(self, dt: datetime | None) -> datetime | None:
        """内部日時は全てUTCで運用するための変換関数(一覧はJST表示)"""
        if dt is None:
            return None

        # 🔹 timeのみ（1900年）対応
        if dt.year == 1900:
            return datetime.combine(
                self.base_utc_dt.date(),
                dt.time(),
                tzinfo=timezone.utc,
            )

        # 🔹 naive → UTC
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    # =======================
    # UI構築(メイン・ウインド)
    # =======================
    def _build_ui(self) -> None:
        """UIを構築する"""

        # =========================
        # 🔹 上部ボタン
        # =========================
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(top_frame, text="単一ログを開く", command=self.open_log_file).pack(side=tk.LEFT)
        tk.Button(top_frame, text="複数ログを開く", command=self.open_logs).pack(side=tk.LEFT, padx=8)
        tk.Button(top_frame, text="フィルタ解除", command=self.reset_filters).pack(side=tk.LEFT)
        #=====Timezone Dropdown=====
        self._build_timezone_dropdown(top_frame)
        # =========================
        # 🔹 フィルタ
        # =========================
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        tk.Label(filter_frame, text="TRACE").pack(side=tk.LEFT)
        self.trace_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.trace_var,
            state="readonly",
            width=35,
        )
        self.trace_dropdown.pack(side=tk.LEFT, padx=(4, 12))
        self.trace_dropdown.bind("<<ComboboxSelected>>", self.apply_filter)

        tk.Label(filter_frame, text="TYPE").pack(side=tk.LEFT)
        self.type_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.type_var,
            state="readonly",
            width=20,
        )
        self.type_dropdown.pack(side=tk.LEFT, padx=(4, 12))
        self.type_dropdown.bind("<<ComboboxSelected>>", self.apply_filter)

        tk.Label(filter_frame, text="SEARCH").pack(side=tk.LEFT)
        tk.Entry(
            filter_frame,
            textvariable=self.search_var,
            width=30,
        ).pack(side=tk.LEFT, padx=(4, 12))

        tk.Button(filter_frame, text="検索", command=self.apply_filter).pack(side=tk.LEFT)

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
        self.tree.heading("type", text="TYPE")
        self.tree.heading("time", text="TIME")
        self.tree.heading("trace_id", text="TRACE_ID")
        self.tree.heading("message", text="MESSAGE")

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

    def reload_log(self, path: Path) -> None:
        """単一ログファイルを再読み込み"""

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
        self.rows = events

        self.update_filters()
        self.apply_filter()

    def open_log_file(self) -> None:
        """ファイルダイアログから単一ログを開く"""

        file_path_str: str = filedialog.askopenfilename(
            title="ログファイルを選択",
            initialdir=str(self.log_dir),
            filetypes=[("Log Files", "*.jsonl *.log"), ("All Files", "*.*")],
        )

        if not file_path_str:
            return

        # 🔹 searcher経由で取得（統一）
        logs: list[LogDict] = collect_logs([Path(file_path_str)])

        self.raw_rows = logs
        self.rows = summarize(logs)
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
        self.rows = summarize(logs)
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

    def parse_datetime(self, value: str, tz: str) -> datetime | None:
        """文字列 → datetime（UTC or Local対応）"""
        value = value.strip()

        if not value:
            return None

        # 🔴 UTC（Z）
        if value.endswith("Z"):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None

        # 🔵 offset付き
        if "+" in value or "-" in value[10:]:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        # 🟢 ISO（ローカル）
        try:
            dt: datetime = datetime.fromisoformat(value)
            return dt.replace(tzinfo=self.get_local_tz(tz))
        except ValueError:
            pass

        # 🟡 YYYYMMDD
        if re.fullmatch(r"\d{8}", value):
            try:
                dt: datetime = datetime.strptime(value, "%Y%m%d")
                return dt.replace(tzinfo=self.get_local_tz(tz))
            except ValueError:
                return None

        # 🟡 HH:MM
        if re.fullmatch(r"\d{1,2}:\d{1,2}", value):
            try:
                dt: datetime = datetime.strptime(value, "%H:%M")
                return dt.replace(tzinfo=self.get_local_tz(tz))
            except ValueError:
                return None

        # 🟡 HHMM
        if re.fullmatch(r"\d{3,4}", value):
            try:
                dt: datetime = datetime.strptime(value.zfill(4), "%H%M")
                return dt.replace(tzinfo=self.get_local_tz(tz))
            except ValueError:
                return None

        return None
    
    def get_local_tz(self, tz_name: str) -> tzinfo:
        """ローカルタイムゾーンを取得する"""
        try:
            # Python 3.9+
            return ZoneInfo(tz_name)
        except Exception:
            # Python 3.8以下の場合はUTCを返す（簡易対応）
            return timezone.utc

    def parse_datetime_with_semantics(
        self,
        value: str) -> tuple[None, None] | tuple[Literal['date'], datetime] | tuple[Literal['datetime'], datetime]:
        """日時文字列を解析し、date-onlyかdatetimeかを区別して返す「意味付け」"""
        dt: datetime | None = self.parse_datetime(value, self.current_tz)

        if dt is None:
            return None, None

        if self.is_date_only(dt):
            return ("date", dt)

        return ("datetime", dt)


    def is_date_only(self, dt: datetime) -> bool:
        """日時が日付のみ（時間部分が00:00:00）か判定する"""
        return dt.hour == 0 and dt.minute == 0 and dt.second == 0


    def parse_range(self, text: str) -> tuple[datetime | None, datetime | None]:
        """範囲検索文字列を解析し、UTC datetimeのタプルを返す"""
        text = text.strip()
        start_str: str = ""
        end_str: str = ""
        
        if ".." in text:
            start_str, end_str = text.split("..", 1)
        elif " - " in text:
            start_str, end_str = text.split(" - ", 1)
        else:
            return None, None

        start_str = start_str.strip()
        end_str = end_str.strip()

        start: datetime | None = self.parse_datetime(start_str, self.current_tz) if start_str else None
        end: datetime | None = self.parse_datetime(end_str, self.current_tz) if end_str else None

        # 🔥 ここだけで意味を確定させる
        if start is not None and self.is_date_only(start):
            start = start.replace(hour=0, minute=0, second=0)

        if end is not None and self.is_date_only(end):
            end = end.replace(hour=23, minute=59, second=59)

        # 🔥 UTC変換は最後に1回だけ
        start_utc: datetime | None = self.to_utc_search_dt(start) if start else None
        end_utc: datetime | None = self.to_utc_search_dt(end) if end else None

        return start_utc, end_utc

    def apply_filter(self, _event: tk.Event | None = None) -> None:
        """フィルタに応じて表示内容を更新する"""
        # logger:"AppLogger" = get_logger()
        trace_filter: str = self.trace_var.get()
        type_filter: str = self.type_var.get()
        search_text: str = self.search_var.get().strip()
        tz: str = self.current_tz

        self.filtered_rows = []

        # 🔹 画面クリア
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        # 🔹 メインループ
        display_index = 0
        
        for row in self.raw_rows:

            row_trace_id: str = self._get_log_trace_id(row)
            row_type: str = self._get_log_type(row)

            # 🔹 TRACEフィルタ
            if trace_filter != self.TRACE_ALL and row_trace_id != trace_filter:
                continue

            # 🔹 TYPEフィルタ
            if type_filter != self.TYPE_ALL and row_type != type_filter:
                continue

            if not match_search_query(row, search_text, tz):
                continue

            # 🔹 表示
            self.filtered_rows.append(row)
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


    def _format_world_local_time(self, value: Any) -> str:
        """UTCをworld_local時間文字列へ変換する"""
        dt: datetime | None = to_world_local_datetime(value, self.current_tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt is not None else str(value)

    def on_click(self, event: tk.Event) -> None:
        """シングルクリックで詳細表示"""
        row: Event | None = self._get_row(event)
        if row is None:
            return

        self._cancel_pending_single_click()
        self._single_click_after_id = self.root.after(
            200,
            lambda: self._open_detail(row),
        )

    def on_double_click(self, event: tk.Event) -> None:
        """ダブルクリックでVSCodeを開く"""
        self._cancel_pending_single_click()

        row: Event | None = self._get_row(event)
        if row is None:
            return

        # 🔥 Event → raw → where
        raw: LogDict = row.raw
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

    def _get_row(self, event: tk.Event) -> Event | None:
        """クリック位置から行データを取得する"""
        row_id: str = self.tree.identify_row(event.y)
        if not row_id:
            return None

        try:
            index = int(row_id)
        except ValueError:
            return None

        if index < 0 or index >= len(self.rows):
            return None

        return self.rows[index]

    def extract_source_file(self, msg: str) -> tuple[str | None, int]:
        """messageから、filenameを抽出する"""
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

    # ===============================
    # 🔹 詳細ウィンドウ表示
    # ===============================
    def _open_detail(self, row: Event) -> None:
        """選択されたログの詳細を表示する"""
        raw: LogDict = row.raw
        renderer = LogRenderer()
        # =========================
        # 🔹 ウィンドウ
        # =========================
        detail = tk.Toplevel(self.root)
        detail.title("詳細情報")
        detail.geometry("900x1200")

        frame = tk.Frame(detail)
        frame.pack(fill=tk.BOTH, expand=True)

        # =========================
        # 🔹 基本情報
        # =========================
        where: LogWhere = raw.get("where", {})
        file_path: str = str(where.get("file", ""))
        line_no: int = int(where.get("line", 1) or 1)
        # =========================
        # 🔹 上部（色付き表示）
        # =========================
        parts: list[tuple[str, str]] = renderer.build_summary_parts(row, self.current_tz)

        for text, color in parts:
            if not text:
                tk.Label(frame, text="").pack(anchor="w")
                continue

            tk.Label(
                frame,
                text=text,
                fg=color or "#000000",  # ← 保険🔥
                justify="left",
                font=self.font_mono,
                anchor="w",
            ).pack(anchor="w", padx=10)

        tk.Frame(frame, height=2, bg="#ccc").pack(fill="x", padx=10, pady=5)
        # =========================
        # 🔹 VSCodeボタン
        # =========================
        # ======ボタン専用フレーム====
        btn_frame = tk.Frame(frame)
        btn_frame.pack(anchor="w", padx=10, pady=(0, 8))
        message = str(raw.get("what", {}).get("message", ""))

        # 🔹 Logger（ログを書いた場所）
        tk.Button(
            btn_frame,
            text="Open Logger(VSCode)",
            fg="#0066cc",
            cursor="hand2",
            width=20,
            command=lambda f=file_path, line=line_no: self.open_in_vscode(f, line),
        ).pack(side=tk.LEFT, padx=5)

        # 🔹 Source（実際の原因）
        src_file: str | None
        src_line: int
        src_file, src_line = self.extract_source_file(message)

        if src_file:
            tk.Button(
                btn_frame,
                text="Open Source(VSCode)",
                cursor="hand2",
                width=20,
                command=lambda f=src_file, line=src_line: self.open_in_vscode(f, line),
            ).pack(side=tk.LEFT, padx=(0, 10))
        # =========================
        # 🔹 RAW
        # =========================
        display_raw: dict[str, Any] = renderer.build_raw(row)

        text_widget = tk.Text(
            frame,
            wrap="word",
            font=self.font_mono,
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget.insert("1.0", "=== RAW DATA ===\n\n")
        text_widget.insert("end", json.dumps(display_raw, indent=2, ensure_ascii=False))
        text_widget.config(state="disabled")

    def open_in_vscode(self, file_path: str, line_no: int) -> None:
        """VSCodeで該当ファイルを開く"""
        if not file_path:
            return
        subprocess.run(["code", "-g", f"{file_path}:{line_no}"], check=False)


if __name__ == "__main__":
    root = tk.Tk()
    latest_candidates: list[Path] = sorted(
        list(LOGS_DIR.glob("*.jsonl")) +
        list(LOGS_DIR.glob("*.log"))
    )
    initial_path: Path | None = latest_candidates[-1] if latest_candidates else None
    LogViewer(root, initial_path)
    root.mainloop()
