from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from logs.log_searcher import collect_logs
from logs.log_storage import load_log
from logs.log_types import LogDict


def test_load_log_falls_back_to_csv_adapter(tmp_path: Path) -> None:
    path: Path = tmp_path / "logs.csv"
    path.write_text(
        "timestamp,level,module,message\n"
        "2026-06-01T09:00:00+00:00,INFO,api,Request processed\n"
        "2026-06-01T09:00:01+00:00,ERROR,database,Connection failed\n",
        encoding="utf-8",
    )

    records: list[dict[str, Any]] = load_log(path)
    logs: list[LogDict] = collect_logs([path])

    assert len(records) == 2
    assert records[0]["event_id"] == "csv:logs.csv:1"
    assert len(logs) == 2
    assert logs[1]["trace_id"] == "csv:logs.csv:2"
    assert "module" in logs[1]["where"]
    assert logs[1]["where"]["module"] == "database"
    assert "message" in logs[1]["what"]
    assert logs[1]["what"]["message"] == "Connection failed"


def test_load_log_falls_back_to_web_log_adapter(tmp_path: Path) -> None:
    path: Path = tmp_path / "access.log"
    path.write_text(
        '192.168.1.1 - - [01/Jun/2026:09:00:00 +0900] "GET /index.html HTTP/1.1" 200 1234\n'
        '192.168.1.2 - - [01/Jun/2026:09:01:02 +0900] "POST /login HTTP/1.1" 401 512\n',
        encoding="utf-8",
    )

    logs: list[LogDict] = collect_logs([path])

    assert len(logs) == 2
    assert logs[1]["level"] == "WARNING"
    assert logs[1]["trace_id"] == "apache:2"
    assert logs[1]["context"]["status"] == 401
    assert logs[1]["context"]["path"] == "/login"


def test_load_log_falls_back_to_traceback_adapter(tmp_path: Path) -> None:
    path: Path = tmp_path / "error.txt"
    path.write_text(
        'Traceback (most recent call last):\n'
        '  File "main.py", line 10, in <module>\n'
        '    func()\n'
        '  File "auth.py", line 25, in func\n'
        '    raise ValueError("invalid user")\n'
        'ValueError: invalid user\n',
        encoding="utf-8",
    )

    logs: list[LogDict] = collect_logs([path])

    assert len(logs) == 1
    assert logs[0]["level"] == "ERROR"
    assert "module" in logs[0]["where"]
    assert logs[0]["where"]["module"] == "auth.py"
    assert "message" in logs[0]["what"]
    assert logs[0]["what"]["message"] == "ValueError: invalid user"
    assert "frames" in logs[0]["context"]
    assert logs[0]["context"]["frames"][-1]["line"] == 25


def test_load_log_falls_back_to_sqlite_adapter(tmp_path: Path) -> None:
    path: Path = tmp_path / "logs.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE logs(timestamp TEXT, level TEXT, module TEXT, message TEXT)")
        conn.execute(
            "INSERT INTO logs VALUES (?, ?, ?, ?)",
            ("2026-06-01T09:00:00+00:00", "INFO", "api", "Request processed"),
        )

    logs: list[LogDict] = collect_logs([path])

    assert len(logs) == 1
    assert logs[0]["trace_id"] == "sqlite:logs:1"
    assert "module" in logs[0]["where"]
    assert logs[0]["where"]["module"] == "api"
