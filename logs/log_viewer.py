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
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Final

from logs.display_formatter import LogRenderer
from logs.log_paths import LOGS_DIR
from logs.log_searcher import collect_logs, summarize
from logs.log_storage import load_log
from logs.log_types import Event, LogDict, LogWhere
from logs.log_validator import validate_log
from logs.openai_key_store import (
    delete_openai_api_key,
    has_openai_api_key,
    is_keyring_available,
    save_openai_api_key,
)
from logs.search_matcher import (
    apply_result_modifiers,
    match_search_query,
    run_aggregate_query,
)
from logs.search_models import SearchQuery
from logs.search_text_analysis import parse_query
from logs.time_utils import (
    to_world_local_datetime,
)
from logs.tzinfo_formatter import (
    TimeZoneData,
    TimeZoneItem,
    build_timezone_data,
)

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
        self.aggregate_result_var = tk.StringVar()

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

    def _build_menu(self) -> None:
        """メインメニューを構築する。"""
        menu_bar = tk.Menu(self.root)
        app_menu = tk.Menu(menu_bar, tearoff=False)
        app_menu.add_command(
            label="OPEN API Keyの登録",
            command=self.open_openai_api_key_dialog,
        )
        app_menu.add_command(label="オプション", command=self.open_options_dialog)
        app_menu.add_separator()
        app_menu.add_command(label="終了", command=self.exit_app)

        menu_bar.add_cascade(label="メニュー", menu=app_menu)
        self.root.config(menu=menu_bar)

    def open_openai_api_key_dialog(self) -> None:
        """OpenAI API Key登録ダイアログを開く。"""
        window = tk.Toplevel(self.root)
        window.title("OPEN API Keyの登録")
        window.geometry("520x220")
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        status_text = (
            "登録済みです。保存し直すか、削除できます。"
            if has_openai_api_key()
            else "未登録です。高精度な意味検索を使う場合のみ登録してください。"
        )

        tk.Label(window, text=status_text, anchor="w").pack(
            fill=tk.X,
            padx=16,
            pady=(14, 8),
        )
        tk.Label(
            window,
            text="API KeyはScriptには保存せず、このPCの資格情報ストアへ保存します。",
            anchor="w",
            fg="#555555",
        ).pack(fill=tk.X, padx=16, pady=(0, 10))

        input_frame = tk.Frame(window)
        input_frame.pack(fill=tk.X, padx=16)

        tk.Label(input_frame, text="API Key").pack(side=tk.LEFT)
        key_var = tk.StringVar()
        key_entry = tk.Entry(input_frame, textvariable=key_var, show="*", width=54)
        key_entry.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        key_entry.focus_set()

        button_frame = tk.Frame(window)
        button_frame.pack(fill=tk.X, padx=16, pady=18)

        def on_save() -> None:
            api_key = key_var.get().strip()
            if not api_key:
                messagebox.showwarning("入力確認", "API Keyを入力してください。", parent=window)
                return
            if not is_keyring_available():
                messagebox.showerror(
                    "keyringが必要です",
                    "安全に保存するため、keyringをインストールしてください。\n\npip install keyring",
                    parent=window,
                )
                return
            save_openai_api_key(api_key)
            messagebox.showinfo("保存完了", "API KeyをこのPCに保存しました。", parent=window)
            window.destroy()

        def on_delete() -> None:
            if not is_keyring_available():
                messagebox.showerror(
                    "keyringが必要です",
                    "keyringが無いため資格情報ストアを操作できません。",
                    parent=window,
                )
                return
            delete_openai_api_key()
            messagebox.showinfo("削除完了", "保存済みAPI Keyを削除しました。", parent=window)
            window.destroy()

        tk.Button(button_frame, text="保存", command=on_save).pack(side=tk.LEFT)
        tk.Button(button_frame, text="削除", command=on_delete).pack(side=tk.LEFT, padx=8)
        tk.Button(button_frame, text="キャンセル", command=window.destroy).pack(side=tk.RIGHT)

        window.wait_window()

    def open_options_dialog(self) -> None:
        """検索オプションダイアログを開く。"""
        window = tk.Toplevel(self.root)
        window.title("オプション")
        window.geometry("520x180")
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        key_status = "登録済み" if has_openai_api_key() else "未登録"
        messages = [
            "現在の similar 検索: ローカル近似検索",
            f"OPEN API Key: {key_status}",
            "Key未登録時はAPIを使わず、TF-IDF/文字n-gram近似検索で動作します。",
            "embeddingsによる高精度検索は将来の切替予定です。",
        ]
        for message in messages:
            tk.Label(window, text=message, anchor="w").pack(fill=tk.X, padx=16, pady=3)

        tk.Button(window, text="閉じる", command=window.destroy).pack(pady=14)
        window.wait_window()

    def exit_app(self) -> None:
        """アプリを終了する。"""
        self.root.destroy()

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

    def apply_filter(self, _event: tk.Event | None = None) -> None:
        """フィルタに応じて表示内容を更新する"""
        # logger:"AppLogger" = get_logger()
        trace_filter: str = self.trace_var.get()
        type_filter: str = self.type_var.get()
        search_text: str = self.search_var.get().strip()
        tz: str = self.current_tz
        search_query: SearchQuery = parse_query(search_text, tz)
        self.aggregate_result_var.set("")

        self.filtered_rows = []

        # 🔹 画面クリア
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for row in self.raw_rows:
            row_trace_id: str = self._get_log_trace_id(row)
            row_type: str = self._get_log_type(row)

            # 🔹 TRACEフィルタ
            if trace_filter != self.TRACE_ALL and row_trace_id != trace_filter:
                continue

            # 🔹 TYPEフィルタ
            if type_filter != self.TYPE_ALL and row_type != type_filter:
                continue

            if not match_search_query(row, search_query, tz):
                continue

            # 🔹 表示
            self.filtered_rows.append(row)

        self.filtered_rows = apply_result_modifiers(self.filtered_rows, search_query, tz)

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
            result = run_aggregate_query(self.filtered_rows, search_query.aggregate, tz)
            self.aggregate_result_var.set(result.message)


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
