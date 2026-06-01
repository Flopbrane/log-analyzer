from __future__ import annotations

import ast
import unittest
from pathlib import Path

from logs.log_types import LogDict
from logs.summary_bridge import summarize_logs_for_viewer, summarize_text_for_viewer


class SummaryBridgeTests(unittest.TestCase):
    def test_summary_engine_does_not_import_logs_layer(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for path in (root / "summary_engine").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name == "logs" or alias.name.startswith("logs."),
                            f"{path} imports logs layer",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    self.assertFalse(
                        node.module == "logs" or node.module.startswith("logs."),
                        f"{path} imports logs layer",
                    )

    def test_bridge_returns_condition_summary(self) -> None:
        rows: list[LogDict] = [
            {
                "level": "ERROR",
                "time": "2026-06-01T00:00:00+00:00",
                "trace_id": "trace-1",
                "where": {"module": "auth", "file": "auth.py", "function": "login"},
                "what": {"message": "login_failed"},
                "context": {"latency_ms": 120, "user": "alice"},
                "output": "file",
            },
            {
                "level": "INFO",
                "time": "2026-06-01T00:01:00+00:00",
                "trace_id": "trace-2",
                "where": {"module": "auth", "file": "auth.py", "function": "login"},
                "what": {"message": "login_ok"},
                "context": {"latency_ms": 80, "user": "bob"},
                "output": "file",
            },
        ]

        result = summarize_logs_for_viewer(rows, "module:auth", "Asia/Tokyo")

        self.assertEqual(2, result.total_count)
        self.assertEqual({"ERROR": 1, "INFO": 1}, dict(result.level_counts))
        self.assertEqual("auth", result.module_ranking[0].key)
        self.assertIn("条件: module:auth", result.text)
        self.assertIn("context.latency_ms avg=100", result.text)

    def test_text_bridge_handles_empty_result(self) -> None:
        text = summarize_text_for_viewer([], "level:ERROR", "Asia/Tokyo")

        self.assertIn("件数: 0", text)
        self.assertIn("該当ログはありません。", text)


if __name__ == "__main__":
    unittest.main()
