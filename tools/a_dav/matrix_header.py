"""Bounded first-line reader for compressed and uncompressed matrix objects."""
from __future__ import annotations

import csv
import gzip
import io
from collections.abc import Iterator


def parse_matrix_header(raw: bytes, *, delimiter: str = "\t",
                        max_header_bytes: int = 65_536, allow_empty: bool = False,
                        orientation: str = "samples_as_columns") -> tuple[str, ...]:
    if delimiter not in {",", "\t"} or type(max_header_bytes) is not int or max_header_bytes <= 0:
        raise ValueError("MATRIX_HEADER_LIMIT")
    if orientation not in {"samples_as_columns", "samples_as_rows"}:
        raise ValueError("MATRIX_ORIENTATION_INVALID")
    if orientation == "samples_as_rows":
        try:
            binary = gzip.GzipFile(fileobj=io.BytesIO(raw)) if raw.startswith(b"\x1f\x8b") else io.BytesIO(raw)
            with binary, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, delimiter=delimiter, strict=True)
                header = next(reader)
                if len(header) < 2:
                    raise ValueError("MATRIX_HEADER_INVALID")
                keys = []
                for row in reader:
                    if len(row) != len(header) or not row[0].strip():
                        raise ValueError("MATRIX_HEADER_INVALID")
                    keys.append(row[0])
                    if len(keys) > 100_000:
                        raise ValueError("MATRIX_HEADER_LIMIT")
                if not keys:
                    raise ValueError("MATRIX_HEADER_INVALID")
                return tuple(keys)
        except (OSError, EOFError, UnicodeError, csv.Error, StopIteration):
            raise ValueError("MATRIX_HEADER_INVALID") from None
    try:
        if raw.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                line = stream.readline(max_header_bytes + 1)
        else:
            end = raw.find(b"\n")
            line = raw[:end + 1] if end >= 0 else raw
            if len(line) > max_header_bytes:
                raise ValueError("MATRIX_HEADER_LIMIT")
        if len(line) > max_header_bytes:
            raise ValueError("MATRIX_HEADER_LIMIT")
        text = line.decode("utf-8-sig").rstrip("\r\n")
        rows = list(csv.reader([text], delimiter=delimiter, strict=True))
    except ValueError:
        raise
    except (OSError, EOFError, UnicodeError, csv.Error):
        raise ValueError("MATRIX_HEADER_INVALID") from None
    if not rows or len(rows[0]) < 2 or (not allow_empty and any(not value for value in rows[0][1:])):
        raise ValueError("MATRIX_HEADER_INVALID")
    return tuple(rows[0])


def transpose_sample_rows(rows: Iterator[list[str]]) -> list[list[str]]:
    """Transpose a rectangular sample-by-feature table, retaining source order."""
    data: list[list[str]] = []
    cells = 0
    for row in rows:
        cells += len(row)
        if cells > 50_000_000:
            raise ValueError('MATRIX_HEADER_LIMIT')
        data.append(row)
    if not data or len(data[0]) < 2 or len(data) < 2:
        raise ValueError('MATRIX_HEADER_INVALID')
    width = len(data[0])
    if any(len(row) != width for row in data) or len(data) * width > 50_000_000:
        raise ValueError('MATRIX_ROW_WIDTH_MISMATCH')
    return [list(column) for column in zip(*data)]


from contextlib import contextmanager
from pathlib import Path


@contextmanager
def matrix_rows(path: Path, *, delimiter: str, compressed: bool, source_format: str) -> Iterator[Iterator[list[str]]]:
    """Read delimited or XLSX matrix rows from a verified source path."""
    if source_format == 'XLSX_NUMERIC':
        from .xlsx import read_numeric_xlsx
        header, data = read_numeric_xlsx(path.read_bytes())
        yield iter([list(header)] + [[str(value) for value in row] for row in data])
    elif source_format in {'MATRIX_HEADER_CSV', 'MATRIX_HEADER_TSV'}:
        with (gzip.open(path, 'rt', encoding='utf-8', newline='') if compressed
              else path.open('r', encoding='utf-8', newline='')) as handle:
            yield iter(csv.reader(handle, delimiter=delimiter, strict=True))
    else:
        raise ValueError('MATRIX_FORMAT_UNSUPPORTED')
