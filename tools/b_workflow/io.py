"""Deterministic hashing, TSV/JSON serialization and atomic publication."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class PipelineFailure(Exception):
    def __init__(self, message: str, code: int = 3, stage: str | None = None):
        super().__init__(message)
        self.code = code
        self.stage = stage


def utc_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def json_no_dups(raw: bytes) -> dict[str, Any]:
    def dedupe(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise PipelineFailure(f"schema reason=duplicate-json-key {key}", 3)
            out[key] = value
        return out

    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=dedupe)
    except UnicodeDecodeError as exc:
        raise PipelineFailure("input file must be UTF-8", 3) from exc
    except json.JSONDecodeError as exc:
        raise PipelineFailure(f"invalid json: {exc}", 3) from exc
    if not isinstance(payload, dict):
        raise PipelineFailure("json root must be an object", 3)
    return payload


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".b_pipeline_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_bytes(path, canonical_json_bytes(payload))


def format_cell(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise PipelineFailure("non-finite float cannot be serialized to TSV", 3)
        return format(value, ".17g")
    return str(value)


def tsv_bytes(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> bytes:
    lines = ["\t".join(headers)]
    for row in rows:
        if len(row) != len(headers):
            raise PipelineFailure("tsv row width mismatch", 3)
        lines.append("\t".join(format_cell(value) for value in row))
    return ("\n".join(lines) + "\n").encode("utf-8")


def atomic_write_tsv(path: Path, headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    payload = tsv_bytes(headers, rows)
    atomic_write_bytes(path, payload)
    return sha256_bytes(payload)


def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PipelineFailure(f"TSV is not UTF-8: {path}", 3) from exc
    lines = text.splitlines()
    if not lines:
        raise PipelineFailure(f"empty TSV: {path}", 3)
    header = lines[0].split("\t")
    rows = [line.split("\t") for line in lines[1:] if line != ""]
    for row_no, row in enumerate(rows, start=2):
        if len(row) != len(header):
            raise PipelineFailure(
                f"{path} row={row_no} reason=wrong-column-count",
                3,
            )
    return header, rows


def parse_optional_float(token: str, *, field: str, row: int) -> float | None:
    if token in {"", "NA"}:
        return None
    try:
        value = float(token)
    except ValueError as exc:
        raise PipelineFailure(f"row={row} field={field} reason=non-numeric token", 3) from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise PipelineFailure(f"row={row} field={field} reason=non-finite numeric token", 3)
    return value


def parse_bool(token: str, *, field: str, row: int) -> bool:
    if token == "true":
        return True
    if token == "false":
        return False
    raise PipelineFailure(f"row={row} field={field} reason=not-boolean", 3)


def code_identity_sha256(repo_root: Path, relative_paths: Sequence[str]) -> str:
    rows: list[str] = []
    for rel in sorted(relative_paths):
        path = repo_root / rel
        if not path.is_file():
            raise PipelineFailure(f"code identity missing file: {rel}", 3)
        rows.append(f"{rel}={sha256_file(path)}")
    return sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def hash_map(paths: Mapping[str, Path]) -> dict[str, str]:
    return {key: sha256_file(path) for key, path in sorted(paths.items())}


def publish_directory(work_dir: Path, dest_dir: Path) -> None:
    if dest_dir.exists():
        raise PipelineFailure(f"destination already exists: {dest_dir}", 4)
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    os.rename(str(work_dir), str(dest_dir))


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def looks_like_html(data: bytes, content_type: str | None = None) -> bool:
    ctype = (content_type or "").lower()
    if "text/html" in ctype or "application/xhtml" in ctype:
        return True
    head = data.lstrip().lower()[:64]
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or head.startswith(b"<head")
