"""tzdataを最新版へ更新するための単独実行スクリプト。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from logs.time_utils import TzdataUpdateResult, update_tzdata_if_needed


def main() -> None:
    """tzdataの更新を行い、結果をダイアログで表示する。"""
    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("TimeZoneData")
    dialog.resizable(False, False)
    tk.Label(
        dialog,
        text="現在、最新版のTimeZoneDataに書き換え中です。",
        padx=24,
        pady=18,
    ).pack()
    dialog.update()

    try:
        result: TzdataUpdateResult = update_tzdata_if_needed()
    finally:
        dialog.destroy()

    if result.updated:
        messagebox.showinfo(
            "TimeZoneData",
            f"TimeZoneDataを更新しました。\n{result.reference_version}",
        )
    elif result.checked:
        messagebox.showinfo(
            "TimeZoneData",
            f"TimeZoneDataは最新版です。\n{result.reference_version or result.installed_version}",
        )
    else:
        messagebox.showwarning(
            "TimeZoneData",
            "最新版の確認ができませんでした。ネットワーク接続を確認してください。",
        )

    root.destroy()


if __name__ == "__main__":
    main()
