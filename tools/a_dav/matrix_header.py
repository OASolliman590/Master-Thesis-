"""Bounded first-line reader for compressed and uncompressed matrix objects."""
from __future__ import annotations

import csv
import gzip
import io


def parse_matrix_header(raw: bytes, *, delimiter: str = "\t",
                        max_header_bytes: int = 65_536) -> tuple[str, ...]:
    if delimiter not in {",", "\t"} or type(max_header_bytes) is not int or max_header_bytes <= 0:
        raise ValueError("MATRIX_HEADER_LIMIT")
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
    if not rows or len(rows[0]) < 2 or any(not value for value in rows[0][1:]):
        raise ValueError("MATRIX_HEADER_INVALID")
    return tuple(rows[0])
