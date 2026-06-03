from __future__ import annotations

from pathlib import Path

from logs.log_searcher import collect_logs
from logs.log_analysis import LogType, detect_log_type
from logs.log_validator import validate_log


def test_validate_log_keeps_logger_project_log_unchanged() -> None:
    row = {
        "level": "WARNING",
        "time": "2026-06-03T03:59:52+00:00",
        "trace_id": "trace-1",
        "where": {"module": "logs/log_validator.py"},
        "what": {"message": "invalid log: missing time"},
        "context": {"reason": "missing time"},
        "output": "both",
    }

    log = validate_log(row)

    assert detect_log_type(row) == LogType.LOGGER_PROJECT
    assert log is not None
    assert log["what"]["message"] == "invalid log: missing time"
    assert log["context"] == {"reason": "missing time"}
    assert "original_row" not in log["context"]


def test_validate_log_accepts_flat_production_log() -> None:
    row = {
        "timestamp": "2026-06-01T09:00:00+00:00",
        "level": "INFO",
        "module": "api",
        "event_id": "EVT-000000",
        "message": "Configuration loaded",
    }

    log = validate_log(row)

    assert detect_log_type(row) == LogType.FLAT_PRODUCTION
    assert log is not None
    assert log["time"] == "2026-06-01T09:00:00+00:00"
    assert log["trace_id"] == "EVT-000000"
    assert log["level"] == "INFO"
    assert log["where"]["module"] == "api"
    assert log["what"]["message"] == "Configuration loaded"
    assert log["what"]["message"] != str(row)
    assert log["context"]["original_row"] == row
    assert log["context"]["original_row"]["module"] == "api"


def test_collect_logs_loads_sample_production_logs() -> None:
    path = Path("extra_sample_file/sample_production_logs_3000.jsonl")

    logs = collect_logs([path])

    assert len(logs) == 3000
    assert logs[0]["trace_id"].startswith("EVT-")
    assert logs[0]["where"]["module"]
    assert logs[0]["what"]["message"]
    assert logs[0]["context"]["original_row"]["event_id"].startswith("EVT-")
