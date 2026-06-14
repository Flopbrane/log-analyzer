# -*- coding: utf-8 -*-
"""複数のログファイルを選択するためのGUI"""
#########################
# Author: F.Kurokawa
# Description:
# 複数のログファイルを選択するためのGUI
#########################
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk


class LogFileSelector:
    """複数のログファイルを選択するためのGUIクラス"""
    def __init__(
        self,
        parent: tk.Misc,
        log_dir: Path,
    ) -> None:

        self.parent: tk.Misc = parent
        self.log_dir: Path = log_dir
        self.result: list[Path] | None = None # 選択されたファイルの返却用リスト
        self.files: list[Path] = [] # ログファイルの下書き用リスト
        self.window: tk.Toplevel = tk.Toplevel(parent)
        self.window.title("ログ選択")
        self.window.geometry("800x500")

        # 🔥 親子化
        self.window.transient(parent)  # type: ignore

        # 🔥 モーダル化
        self.window.grab_set()

        self._build_ui()


    def _build_ui(self) -> None:
        """UIを構築する"""
        # 選択されたログファイルのリストを取得
        self.files: list[Path] = sorted(
            list(self.log_dir.glob("*.jsonl")) +
            list(self.log_dir.glob("*.log")),
            key=lambda p: p.name
        )

        if not self.files:
            tk.Label(self.window, text="ログファイルが見つかりません").pack(
                padx=12,
                pady=12,
                anchor="w",
            )
            tk.Button(self.window, text="閉じる", command=self.window.destroy).pack(pady=8)
            self.window.wait_window()
            return None

        scrollbar = tk.Scrollbar(self.window, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # ログファイルのリストを表示する
        # 🔹 Treeview
        self.tree = ttk.Treeview(
            self.window,
            columns=("date", "filename"),
            show="headings",
            selectmode="none",
            yscrollcommand=scrollbar.set,
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("filename", text="File")
        for i, file_path in enumerate(self.files):
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    file_path.stem,
                    file_path.name,
                ),
            )
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)  # type: ignore[arg-type]
        self.tree.bind("<Button-1>", self._on_tree_click)

        # ボタンフレーム
        button_frame: ttk.Frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # OKボタン
        ok_button: ttk.Button = ttk.Button(button_frame, text="OK", command=self._on_ok)
        ok_button.pack(side=tk.RIGHT)

        # キャンセルボタン
        cancel_button: ttk.Button = ttk.Button(button_frame, text="キャンセル", command=self._on_cancel)
        cancel_button.pack(side=tk.RIGHT, padx=(0, 10))


    def show(self) -> list[Path] | None:
        """ウィンドウを表示して、選択されたファイルのリストを返す
        このfileの全ての出入り口はこの関数であるべき
        """
        self.window.wait_window()
        return self.result

    def _on_tree_click(self, event: tk.Event[tk.Widget]) -> str:
        """1クリックで選択、再クリックで選択解除する。"""
        row_id: str = self.tree.identify_row(event.y)
        if not row_id:
            return "break"

        selected_items: tuple[str, ...] = self.tree.selection()
        if row_id in selected_items:
            self.tree.selection_remove(row_id)
        else:
            self.tree.selection_add(row_id)
            self.tree.focus(row_id)
        return "break"


    def _on_ok(self) -> None:
        """OKボタンが押されたときの処理"""
        selected_items: tuple[str, ...] = self.tree.selection()

        self.files: list[Path] = sorted(
                    list(self.log_dir.glob("*.jsonl"))
                    + list(self.log_dir.glob("*.log")),
                    key=lambda p: p.name,
                )

        self.result = [
            self.files[int(i)]
            for i in selected_items
        ]

        self.window.destroy()


    def _on_cancel(self) -> None:
        """キャンセルボタンが押されたときの処理"""
        self.result = None
        self.window.destroy()
