from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import cast

from logs.log_types import Event, EventType, LogDict, LogLevel, TraceId
from logs.result_exporter import (
    export_event_logs_to_csv,
    export_events_to_csv,
    export_investigation_report_json,
    export_logs_to_csv,
    export_summary_to_csv,
    export_to_json,
)
from summary_engine.summary_types import NumericStats, RankingItem, SummaryResult


def _sample_log() -> LogDict:
    return cast(
        LogDict,
        {
            "level": "ERROR",
            "time": "2026-06-01T09:00:00+00:00",
            "trace_id": "trace-1",
            "where": {"module": "auth", "file": "auth.py", "function": "login"},
            "what": {"message": "Login Failed"},
            "context": {"retry": 3},
            "output": "file",
        },
    )


def _sample_summary() -> SummaryResult:
    return SummaryResult(
        total_count=1,
        condition_text="level:ERROR",
        level_counts={"ERROR": 1},
        module_ranking=(RankingItem("auth", 1),),
        message_ranking=(RankingItem("Login Failed", 1),),
        context_numeric_stats={
            "retry": NumericStats(
                field="context.retry",
                count=1,
                minimum=3,
                maximum=3,
                average=3,
                median=3,
            )
        },
        insights=("ERROR/CRITICAL が 1 件あります。",),
        text="検索条件\n  条件: level:ERROR",
    )


def test_export_logs_to_csv(tmp_path: Path) -> None:
    path = tmp_path / "logs.csv"

    result = export_logs_to_csv([_sample_log()], path)

    assert result == path
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["level"] == "ERROR"
    assert rows[0]["module"] == "auth"
    assert rows[0]["message"] == "Login Failed"
    assert '"retry": 3' in rows[0]["context"]


def test_export_events_to_csv(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    event = Event(
        type=EventType.ERROR,
        level=LogLevel.ERROR,
        time="2026-06-01T09:00:00+00:00",
        detected_at="2026-06-01T09:00:01+00:00",
        trace_id=TraceId("trace-1"),
        message="Login Failed",
        data={"retry": 3},
        raw=_sample_log(),
    )

    export_events_to_csv([event], path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["type"] == "error"
    assert rows[0]["level"] == "ERROR"
    assert '"retry": 3' in rows[0]["data"]


def test_export_event_logs_to_csv_uses_event_raw(tmp_path: Path) -> None:
    path = tmp_path / "event_logs.csv"
    selected_log = _sample_log()
    event = Event(
        type=EventType.ERROR,
        level=LogLevel.ERROR,
        time="2026-06-01T09:00:00+00:00",
        detected_at="2026-06-01T09:00:01+00:00",
        trace_id=TraceId("trace-1"),
        message="Login Failed",
        data={"retry": 3},
        raw=selected_log,
    )

    export_event_logs_to_csv([event], path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["trace_id"] == "trace-1"
    assert rows[0]["message"] == "Login Failed"


def test_export_summary_to_csv(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"

    export_summary_to_csv(_sample_summary(), path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["condition_text"] == "level:ERROR"
    assert rows[0]["total_count"] == "1"
    assert "ERROR/CRITICAL" in rows[0]["insights"]


def test_export_to_json(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"

    export_to_json(logs=[_sample_log()], summary=_sample_summary(), save_file_path=path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["logs"][0]["trace_id"] == "trace-1"
    assert payload["summary"]["condition_text"] == "level:ERROR"


def test_export_investigation_report_json(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    event = Event(
        type=EventType.ERROR,
        level=LogLevel.ERROR,
        time="2026-06-01T09:00:00+00:00",
        detected_at="2026-06-01T09:00:01+00:00",
        trace_id=TraceId("trace-1"),
        message="Login Failed",
        data={"retry": 3},
        raw=_sample_log(),
    )

    export_investigation_report_json(
        logs=[event.raw],
        events=[event],
        summary=_sample_summary(),
        condition_text="level:ERROR",
        timezone_name="Asia/Tokyo",
        source_files=[Path("logs/sample.jsonl")],
        save_file_path=path,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["report"]["kind"] == "investigation_report"
    assert payload["report"]["timezone"] == "Asia/Tokyo"
    assert payload["events"][0]["raw"]["trace_id"] == "trace-1"
