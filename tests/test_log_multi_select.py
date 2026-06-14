from __future__ import annotations

from dataclasses import dataclass

from logs.log_multi_select import LogFileSelector


class _DummyTree:
    def __init__(self) -> None:
        self._selected: list[str] = []
        self.focused: str | None = None

    def identify_row(self, y: int) -> str:
        return "" if y < 0 else str(y)

    def selection(self) -> tuple[str, ...]:
        return tuple(self._selected)

    def selection_add(self, row_id: str) -> None:
        if row_id not in self._selected:
            self._selected.append(row_id)

    def selection_remove(self, row_id: str) -> None:
        self._selected = [value for value in self._selected if value != row_id]

    def focus(self, row_id: str) -> None:
        self.focused = row_id


@dataclass
class _DummyEvent:
    y: int


def test_tree_click_toggles_selection() -> None:
    selector = LogFileSelector.__new__(LogFileSelector)
    selector.tree = _DummyTree()

    result = selector._on_tree_click(_DummyEvent(y=1))
    assert result == "break"
    assert selector.tree.selection() == ("1",)
    assert selector.tree.focused == "1"

    selector._on_tree_click(_DummyEvent(y=2))
    assert selector.tree.selection() == ("1", "2")

    selector._on_tree_click(_DummyEvent(y=1))
    assert selector.tree.selection() == ("2",)


def test_tree_click_ignores_blank_area() -> None:
    selector = LogFileSelector.__new__(LogFileSelector)
    selector.tree = _DummyTree()

    result = selector._on_tree_click(_DummyEvent(y=-1))
    assert result == "break"
    assert selector.tree.selection() == ()
