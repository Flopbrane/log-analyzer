from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from logs.display_formatter import LogRenderer
from logs.log_types import LogDict
from logs.log_viewer import LogViewer


class _DummyLogger:
    def debug(self, _message: str, context: dict[str, Any] | None = None) -> None:
        _ = context

    def error(self, _message: str, context: dict[str, Any] | None = None) -> None:
        _ = context


class _DummyVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class _DummyTree:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def get_children(self) -> list[str]:
        return [str(index) for index in range(len(self.rows))]

    def delete(self, *_items: str) -> None:
        self.rows = []

    def insert(
        self,
        _parent: str,
        _index: str,
        *,
        iid: str,
        values: tuple[str, str, str, str],
        tags: tuple[str, ...],
    ) -> None:
        self.rows.append({"iid": iid, "values": values, "tags": tags})

    def identify_row(self, y: int) -> str:
        return str(y)


@dataclass
class _DummyEvent:
    y: int


def _sample_logs() -> list[LogDict]:
    return [
        {
            "level": "INFO",
            "time": "2026-04-23T05:49:41+00:00",
            "trace_id": "old-trace",
            "where": {"module": "system_monitor", "file": "system_monitor.py", "function": "_log_cpu", "line": 87},
            "what": {"message": "system_cpu_percent"},
            "context": {"cpu_percent": 0.0},
            "output": "file",
        },
        {
            "level": "INFO",
            "time": "2026-04-23T05:49:42+00:00",
            "trace_id": "new-trace",
            "where": {"module": "system_monitor", "file": "system_monitor.py", "function": "_log_cpu", "line": 87},
            "what": {"message": "system_cpu_percent"},
            "context": {"cpu_percent": 1.0},
            "output": "file",
        },
    ]


def _build_viewer() -> LogViewer:
    viewer = LogViewer.__new__(LogViewer)
    viewer.logger = _DummyLogger()
    viewer.current_tz = "Asia/Tokyo"
    viewer.trace_var = _DummyVar(LogViewer.TRACE_ALL)
    viewer.type_var = _DummyVar(LogViewer.TYPE_ALL)
    viewer.search_var = _DummyVar("")
    viewer.aggregate_result_var = _DummyVar("")
    viewer.tree = _DummyTree()
    viewer.raw_rows = []
    viewer.filtered_rows = []
    viewer.display_rows = []
    return viewer


def test_trace_jump_is_preserved_in_list_and_detail() -> None:
    viewer = _build_viewer()
    viewer._set_raw_rows(_sample_logs())
    viewer.search_var.set("type:TRACE_JUMP")

    viewer.apply_filter()

    assert len(viewer.display_rows) == 1
    event_row = viewer.display_rows[0]
    assert viewer._get_event_display_type(event_row) == "TRACE_JUMP"
    assert viewer.tree.rows[0]["values"][0] == "TRACE_JUMP"

    clicked = viewer._get_display_row(_DummyEvent(y=0))
    assert clicked is event_row

    detail_text = LogRenderer().build_summary(event_row, viewer.current_tz)
    assert "Type  : TRACE_JUMP" in detail_text
    assert "system_cpu_percent" in detail_text
    assert "from" in detail_text
    assert "to" in detail_text
