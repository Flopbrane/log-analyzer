from __future__ import annotations

import json
from pathlib import Path

from fv_engine import build_execution_plan, parse_fv_text, run_execution_plan
from fv_engine.fv_types import FVExportFormat, FVSummaryMode
from logs.log_types import LogDict


def _sample_logs() -> list[LogDict]:
    return [
        {
            "level": "ERROR",
            "time": "2026-06-01T00:00:00+00:00",
            "trace_id": "trace-1",
            "where": {"module": "auth", "file": "auth.py", "function": "login"},
            "what": {"message": "login_failed"},
            "context": {"latency_ms": 120},
            "output": "file",
        },
        {
            "level": "INFO",
            "time": "2026-06-01T00:01:00+00:00",
            "trace_id": "trace-2",
            "where": {"module": "billing", "file": "billing.py", "function": "pay"},
            "what": {"message": "payment_ok"},
            "context": {"latency_ms": 80},
            "output": "file",
        },
    ]


def test_parse_fv_text_returns_recipe() -> None:
    recipe = parse_fv_text(
        """
TITLE:
認証エラー調査

QUERY:
level:ERROR
and where.module:auth

SUMMARY:
ON

EXPORT:
JSON
"""
    )

    assert recipe.title == "認証エラー調査"
    assert recipe.query == "level:ERROR\nand where.module:auth"
    assert recipe.summary is FVSummaryMode.ON
    assert recipe.export is FVExportFormat.JSON


def test_run_execution_plan_filters_and_summarizes() -> None:
    recipe = parse_fv_text(
        """
TITLE:
認証エラー調査
QUERY:
level:ERROR
SUMMARY:
ON
EXPORT:
NONE
"""
    )
    plan = build_execution_plan(recipe, execution_id="test-execution")

    result = run_execution_plan(plan, _sample_logs(), timezone="Asia/Tokyo")

    assert result.matched_count == 1
    assert result.summary is not None
    assert result.summary.total_count == 1
    assert result.summary.level_counts["ERROR"] == 1
    assert result.export_file_path is None


def test_run_execution_plan_exports_json(tmp_path: Path) -> None:
    recipe = parse_fv_text(
        """
TITLE:
認証エラー調査
QUERY:
level:ERROR
SUMMARY:
ON
EXPORT:
JSON
"""
    )
    output_path = tmp_path / "fv_result.json"
    plan = build_execution_plan(recipe, output_file_path=str(output_path))

    result = run_execution_plan(plan, _sample_logs())

    assert result.export_file_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["logs"][0]["trace_id"] == "trace-1"
    assert payload["summary"]["condition_text"] == "level:ERROR"
