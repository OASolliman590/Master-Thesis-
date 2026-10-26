"""Bounded CSV/TSV reader that preserves duplicate and positional headers."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass


class DelimitedTableError(ValueError):
    """Safe code for malformed or over-limit delimited tables."""


@dataclass(frozen=True)
class DelimitedTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def column(self, position: int) -> tuple[str, ...]:
        if type(position) is not int or not 0 <= position < len(self.headers):
            raise DelimitedTableError("TABLE_COLUMN_INVALID")
        return tuple(row[position] for row in self.rows)


def read_delimited_table(raw: bytes, *, delimiter: str, max_bytes: int = 64 * 1024 * 1024,
                         max_rows: int = 100_000, max_columns: int = 1_000,
                         max_cells: int = 50_000_000) -> DelimitedTable:
    if delimiter not in {",", "\t"} or len(raw) > max_bytes:
        raise DelimitedTableError("TABLE_LIMIT_OR_DELIMITER_INVALID")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        parsed: list[tuple[str, ...]] = []
        for row in reader:
            if len(parsed) >= max_rows + 1 or len(row) > max_columns:
                raise DelimitedTableError("TABLE_LIMIT_EXCEEDED")
            parsed.append(tuple(row))
    except (UnicodeError, csv.Error):
        raise DelimitedTableError("TABLE_FORMAT_INVALID") from None
    if len(parsed) < 2 or len(parsed[0]) < 2:
        raise DelimitedTableError("TABLE_SHAPE_INVALID")
    width = len(parsed[0])
    if any(len(row) != width for row in parsed[1:]):
        raise DelimitedTableError("TABLE_RAGGED")
    if (len(parsed) - 1) * width > max_cells:
        raise DelimitedTableError("TABLE_LIMIT_EXCEEDED")
    return DelimitedTable(parsed[0], tuple(parsed[1:]))
