# -*- coding: utf-8 -*-
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import Any, cast

from logs.log_types import LogDict
from logs.traceql_bridge import TraceQLLogResult, analyze_logs_for_viewer, filter_logs_for_viewer

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]


class TraceQLBridgeBoundaryTests(unittest.TestCase):
    def test_logs_import_query_engine_only_from_bridge(self) -> None:
        offenders: list[str] = []
        logs_dir: Path = PROJECT_ROOT / "logs"
        for path in logs_dir.rglob("*.py"):
            if path.name == "traceql_bridge.py":
                continue
            tree: ast.Module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "query_engine" or alias.name.startswith("query_engine."):
                            offenders.append(str(path.relative_to(PROJECT_ROOT)))
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "query_engine" or str(node.module).startswith("query_engine."):
                        offenders.append(str(path.relative_to(PROJECT_ROOT)))

        self.assertEqual([], offenders)

    def test_bridge_returns_viewer_ready_results(self) -> None:
        logs: list[LogDict] = [
            cast(
                LogDict,
                {
                    "level": "ERROR",
                    "time": "2026-05-26T01:23:45+00:00",
                    "trace_id": "trace-1",
                    "where": {"function": "run", "file": "worker.py"},
                    "what": {"message": "disk failure"},
                    "context": {"retry": {"type": "int", "value": 3}},
                    "output": "file",
                },
            ),
            cast(
                LogDict,
                {
                    "level": "INFO",
                    "time": "2026-05-26T01:24:45+00:00",
                    "trace_id": "trace-2",
                    "where": {"function": "run", "file": "worker.py"},
                    "what": {"message": "healthy"},
                    "context": {},
                    "output": "file",
                },
            ),
        ]

        results: list[TraceQLLogResult] = analyze_logs_for_viewer(logs, "level:ERROR", "Asia/Tokyo")
        self.assertEqual([True, False], [result.matched for result in results])
        self.assertEqual("disk failure", results[0].document["message"])
        self.assertEqual(3, cast(dict[str, Any], results[0].document["context"])["retry"])

        filtered: list[LogDict] = filter_logs_for_viewer(logs, "level:ERROR", "Asia/Tokyo")
        self.assertEqual([logs[0]], filtered)


if __name__ == "__main__":
    unittest.main()
