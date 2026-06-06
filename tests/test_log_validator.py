from __future__ import annotations

from pathlib import Path

from logs.log_normalizer import LogType, detect_log_type, normalize_log_record
from logs.log_searcher import collect_logs
from logs.log_types import LogDict
from logs.log_validator import validate_log


def test_validate_log_keeps_logger_project_log_unchanged() -> None:
    row: dict[str, str | dict[str, str]] = {
        "level": "WARNING",
        "time": "2026-06-03T03:59:52+00:00",
        "trace_id": "trace-1",
        "where": {"module": "logs/log_validator.py"},
        "what": {"message": "invalid log: missing time"},
        "context": {"reason": "missing time"},
        "output": "both",
    }

    log: LogDict | None = validate_log(row)

    assert detect_log_type(row) == LogType.LOGGER_PROJECT
    assert log is not None
    assert log["what"]["message"] == "invalid log: missing time"
    assert log["context"] == {"reason": "missing time"}
    assert "original_row" not in log["context"]


def test_validate_log_accepts_flat_production_log() -> None:
    row: dict[str, str] = {
        "timestamp": "2026-06-01T09:00:00+00:00",
        "level": "INFO",
        "module": "api",
        "event_id": "EVT-000000",
        "message": "Configuration loaded",
    }

    log: LogDict | None = validate_log(row)

    assert detect_log_type(row) == LogType.FLAT_PRODUCTION
    assert log is not None
    assert log["time"] == "2026-06-01T09:00:00+00:00"
    assert log["trace_id"] == "EVT-000000"
    assert log["level"] == "INFO"
    assert "module" in log["where"]
    assert log["where"]["module"] == "api"
    assert "message" in log["what"]
    assert log["what"]["message"] == "Configuration loaded"
    assert log["what"]["message"] != str(row)
    assert log["context"]["original_row"] == row
    assert log["context"]["original_row"]["module"] == "api"


def test_collect_logs_loads_sample_production_logs() -> None:
    path = Path("extra_sample_file/sample_production_logs_3000.jsonl")

    logs = collect_logs([path])

    assert len(logs) == 3000
    assert logs[0]["trace_id"].startswith("EVT-")
    assert "module" in logs[0]["where"]
    assert logs[0]["where"]["module"]
    assert "message" in logs[0]["what"]
    assert logs[0]["what"]["message"]
    assert logs[0]["context"]["original_row"]["event_id"].startswith("EVT-")


def test_normalizer_accepts_nested_json_log() -> None:
    row = {
        "time": "2026-06-01T09:00:00+00:00",
        "severity": "ERROR",
        "service": {"name": "auth"},
        "event": {"id": "AUTH-001", "message": "Login Failed"},
        "user": {"id": "user001"},
    }

    normalized = normalize_log_record(row)
    log = validate_log(row)

    assert detect_log_type(row) == LogType.NESTED_JSON
    assert normalized["where"]["module"] == "auth"
    assert log is not None
    assert log["trace_id"] == "AUTH-001"
    assert log["what"]["message"] == "Login Failed"
    assert log["context"]["original_row"]["user"]["id"] == "user001"


def test_normalizer_accepts_windows_event_log() -> None:
    row = {
        "EventID": 4625,
        "Level": "Error",
        "Provider": "Microsoft-Windows-Security-Auditing",
        "Message": "An account failed to log on.",
        "TimeCreated": "2026-06-01T09:00:00+00:00",
    }

    log = validate_log(row)

    assert detect_log_type(row) == LogType.WINDOWS_EVENT
    assert log is not None
    assert log["level"] == "ERROR"
    assert log["trace_id"] == "4625"
    assert log["where"]["module"] == "Microsoft-Windows-Security-Auditing"
