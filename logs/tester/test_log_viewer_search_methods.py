# -*- coding: utf-8 -*-
"""LogViewer の検索テキストボックスを実メソッドで検証するテストScript。

目的:
- 独自の検索ロジックではなく、logs.log_viewer.LogViewer.apply_filter() を実際に呼ぶ
- 検索欄へ文字列を入れた時、TreeView に何件表示されるかを確認する
- 期待件数との差分を [OK] / [NG] で表示する

置き場所例:
    logs/tester/test_log_viewer_search_methods.py

実行例:
    python logs\tester\test_log_viewer_search_methods.py

ログファイルを明示する場合:
    python logs\tester\test_log_viewer_search_methods.py ^
      logs\tester\alarm_2026-04-22.jsonl ^
      logs\tester\alarm_2026-04-23.jsonl ^
      logs\tester\alarm_2026-04-24.jsonl
"""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

import logs.log_viewer as lv
from logs.log_searcher import collect_logs, summarize
from logs.log_types import LogDict

print("DEBUG IMPORT:", lv.__file__)

DEFAULT_FILENAMES: Final[list[str]] = [
    "alarm_2026-04-22.jsonl",
    "alarm_2026-04-23.jsonl",
    "alarm_2026-04-24.jsonl",
]


@dataclass(frozen=True)
class SearchCase:
    """検索欄テスト1件分"""

    query: str
    expected: int
    note: str


def find_default_log_files() -> list[Path]:
    """ログファイルを探す。

    優先順:
    1. コマンドライン引数
    2. このScriptと同じフォルダ
    3. カレント/logs/tester
    4. カレント/logs
    5. カレント
    """

    if len(sys.argv) >= 2:
        return [Path(arg).resolve() for arg in sys.argv[1:]]

    script_dir: Path = Path(__file__).resolve().parent
    cwd: Path = Path.cwd().resolve()

    candidate_dirs: list[Path] = [
        script_dir,
        cwd / "logs" / "tester",
        cwd / "logs",
        cwd,
    ]

    for base_dir in candidate_dirs:
        paths: list[Path] = [base_dir / name for name in DEFAULT_FILENAMES]
        if all(path.exists() for path in paths):
            return paths

    return []


def build_viewer_with_logs(paths: list[Path]) -> tuple[tk.Tk, lv.LogViewer]:
    """LogViewerを作成し、実際のViewerと同じrowsへログをセットする。"""

    root = tk.Tk()
    root.withdraw()  # テストなので画面は出さない


    viewer = lv.LogViewer(root)

        # 🔥 応急処置
    if not hasattr(viewer, "current_tz"):
        viewer.current_tz = "Asia/Tokyo"

    logs: list[LogDict] = collect_logs(paths)

    print(f"loaded logs: {len(logs)}")

    # 🔥 summarizeしない
    viewer.raw_rows = logs

    viewer.rows = summarize(logs)  # ここは summarize を通す（Event化）

    viewer.update_filters()
    viewer.apply_filter()
    root.update_idletasks()

    return root, viewer


def run_one_case(viewer: lv.LogViewer, case: SearchCase) -> tuple[bool, int]:
    """検索欄に値を入れて、LogViewer.apply_filter() の実結果を数える。"""

    viewer.trace_var.set(viewer.TRACE_ALL)
    viewer.type_var.set(viewer.TYPE_ALL)
    viewer.search_var.set(case.query)

    # ここが最重要:
    # 独自検索ではなく、LogViewer本体の apply_filter() を直接使う
    viewer.apply_filter()

    actual: int = len(viewer.tree.get_children())
    ok: bool = actual == case.expected
    return ok, actual


def debug_range_parse(viewer: lv.LogViewer, query: str) -> str:
    """範囲検索文字列を LogViewer.parse_range() がどう解釈しているか表示する。"""

    if ".." not in query and " - " not in query:
        return ""
    start: datetime | None = None
    end: datetime | None = None
    
    try:
        start, end = viewer.parse_range(query)
        return f"parse_range -> start={start!s}, end={end!s}"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return f"parse_range ERROR -> {exc!r}"


def main() -> int:
    paths: list[Path] = find_default_log_files()

    if not paths:
        print("[ERROR] ログファイルが見つかりません。")
        print("コマンドライン引数で jsonl ファイルを指定してください。")
        return 1

    print("=== load files ===")
    for path in paths:
        print(path)

    root: tk.Tk
    viewer: lv.LogViewer

    root, viewer = build_viewer_with_logs(paths)

    print()
    print(f"loaded raw logs: {len(viewer.raw_rows)}")
    print(f"loaded filtered logs: {len(viewer.filtered_rows)}")
    print(f"loaded events: {len(viewer.rows)}")
    print(f"timezone: {viewer.current_tz}")
    print()

    # 前回の独自テスターで期待していた件数。
    # 今回は LogViewer.apply_filter() の実結果と照合する。
    cases: list[SearchCase] = [
        SearchCase("", 69, "空欄なら全件"),
        SearchCase("2026-04-22", 3, "年月日検索"),
        SearchCase("2026-04-23", 30, "年月日検索"),
        SearchCase("2026-04-24", 36, "年月日検索"),
        SearchCase("2026-04-23..2026-04-24", 66, "日付期間検索"),
        SearchCase("2026-04-23..2026-04-23", 30, "単日を期間形式で検索"),
        SearchCase("2026-04-23 14:49..2026-04-23 14:49", 12, "分単位の期間検索"),
        SearchCase("2026-04-23 15:00:31..2026-04-23 15:00:37", 18, "秒単位の期間検索"),
        SearchCase("2026-04-23 - 2026-04-24", 66, "互換形式の日付期間検索"),
        SearchCase("10:15", 18, "時刻検索 HH:MM"),
        SearchCase("10:16", 18, "時刻検索 HH:MM"),
        SearchCase("2026-04-24 10:16", 18, "日時プレフィックス検索"),
        SearchCase("level:ERROR", 4, "level指定 ※現在のViewerが対応しているか確認"),
        SearchCase("level:WARNING", 11, "level指定 ※現在のViewerが対応しているか確認"),
        SearchCase("message:test_error", 4, "message指定 ※現在のViewerが対応しているか確認"),
        SearchCase("message:system_cpu_percent", 24, "message指定 ※現在のViewerが対応しているか確認"),
        SearchCase("message:system_gpu_status", 18, "message指定 ※現在のViewerが対応しているか確認"),
        SearchCase("function:run_test", 20, "where.function指定 ※現在のViewerが対応しているか確認"),
        SearchCase("file:system_monitor.py", 46, "where.file指定 ※現在のViewerが対応しているか確認"),
        SearchCase("context:cpu_percent", 24, "contextキー検索 ※現在のViewerが対応しているか確認"),
        SearchCase("context:gpu_mem_total_mb", 18, "contextキー検索 ※現在のViewerが対応しているか確認"),
        SearchCase("trace_id:fc036f388b7542c48117d55c8ec1728c", 3, "trace_id指定 ※現在のViewerが対応しているか確認"),
    ]

    print("=== LogViewer.apply_filter() tests ===")

    ng_count = 0
    ok: bool
    actual: int
    status: str

    for case in cases:
        ok, actual = run_one_case(viewer, case)
        status = "OK" if ok else "NG"

        if not ok:
            ng_count += 1

        print(
            f"[{status}] query={case.query!r:<54} "
            f"expected={case.expected:<3} actual={actual:<3} {case.note}"
        )

        debug_text: str = debug_range_parse(viewer, case.query)
        if debug_text and not ok:
            print(f"     {debug_text}")

    print()
    print("=== result ===")
    if ng_count == 0:
        print("ALL OK")
    else:
        print(f"NG: {ng_count} 件")
        print()
        print("NOTE:")
        print("- このテストは LogViewer.apply_filter() の実動作を使っています。")
        print("- NG が出た場合、前回の独自テスターの仕様と、現在の Viewer 実装がズレています。")
        print("- 特に level: / message: / file: / function: / context: は、現在の Viewer 側で未対応の可能性があります。")
        print("- 日付範囲がズレる場合、検索入力を UTC として扱うか、表示中の TimeZone として扱うかの設計確認が必要です。")

    root.destroy()
    return 0 if ng_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
