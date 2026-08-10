"""Offline tests for live Property ID row resolution (mocked worksheet)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sheets_data import property_id_row_map, resolve_unique_sheet_row  # noqa: E402


class _MockCell:
    def __init__(self, value: str) -> None:
        self.value = value


class MockWorksheet:
    """Minimal gspread worksheet stand-in for column A scans."""

    def __init__(self, title: str, column_a: list[str]) -> None:
        self.title = title
        self._column_a = column_a

    def col_values(self, col: int) -> list[str]:
        if col != 1:
            raise ValueError("MockWorksheet only supports column 1")
        return list(self._column_a)

    def cell(self, row: int, col: int) -> _MockCell:
        if col != 1:
            raise ValueError("MockWorksheet only supports column 1")
        if row < 1 or row > len(self._column_a):
            return _MockCell("")
        return _MockCell(self._column_a[row - 1])


def test_property_id_found() -> None:
    ws = MockWorksheet(
        "New York",
        ["Property ID", "100_Oak_Street", "200_Pine_Road"],
    )
    row_map = property_id_row_map(ws)
    assert row_map["100_Oak_Street"] == [2]
    assert resolve_unique_sheet_row(ws, "200_Pine_Road", row_map=row_map) == 3


def test_row_moved_after_sorting() -> None:
    """Column A reflects a sorted sheet; positional get_all_records order would differ."""
    ws = MockWorksheet(
        "New York",
        ["Property ID", "Z_Last_Property", "A_First_Property"],
    )
    row_map = property_id_row_map(ws)
    assert resolve_unique_sheet_row(ws, "Z_Last_Property", row_map=row_map) == 2
    assert resolve_unique_sheet_row(ws, "A_First_Property", row_map=row_map) == 3


def test_property_id_missing() -> None:
    ws = MockWorksheet("Chicago", ["Property ID", "Only_One"])
    try:
        resolve_unique_sheet_row(ws, "Missing_ID")
    except ValueError as exc:
        assert "not found" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError for missing Property ID")


def test_duplicate_property_id() -> None:
    ws = MockWorksheet(
        "New York",
        ["Property ID", "Dup_ID", "Other", "Dup_ID"],
    )
    row_map = property_id_row_map(ws)
    assert row_map["Dup_ID"] == [2, 4]
    try:
        resolve_unique_sheet_row(ws, "Dup_ID", row_map=row_map)
    except ValueError as exc:
        assert "appears 2 times" in str(exc)
        assert "rows [2, 4]" in str(exc)
    else:
        raise AssertionError("expected ValueError for duplicate Property ID")


def main() -> int:
    test_property_id_found()
    test_row_moved_after_sorting()
    test_property_id_missing()
    test_duplicate_property_id()
    print("Sheet row-resolution tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
