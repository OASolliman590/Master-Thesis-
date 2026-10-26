"""Rebuild metadata review context and emit a fresh unsigned worksheet."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Callable, cast

from .assays import validate_assays
from .core import DERIVED_TABLES, ENTITY_TABLES, DavError, SchemaStore, require
from .endpoints import map_endpoints
from .exposure import validate_exposure
from .ingest import IngestError, validate_output_path
from .overlap import validate_overlap
from .registries import build_registries
from .timing import validate_timing
from .worksheet import build_worksheet

STAGES: tuple[tuple[str, Callable[..., dict[str, Any]]], ...] = (
    ("endpoints", map_endpoints), ("timing", validate_timing), ("assays", validate_assays),
    ("overlap", validate_overlap), ("exposure", validate_exposure),
)
OUTPUT_FILES = ("review_packet.json", "reviewer_worksheet.json", "SUMMARY.json")


def _read_packet(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise DavError("MALFORMED_INPUT") from None
    require(type(value) is dict, "MALFORMED_INPUT")
    return cast(dict[str, Any], value)


def _patient_free_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "purpose": "PRE_ADMISSION_METADATA_REVIEW",
        "source_admission": False,
        "matrix_construction": False,
        "biological_analysis_executed": False,
        "stages": [{"stage": row["stage"], "status": row["status"],
                    "reasons": row["reasons"]} for row in results],
    }


def prepare_review(packet: dict[str, Any], output_dir: Path, *,
                   schemas: SchemaStore | None = None) -> dict[str, Any]:
    """Rebuild registry-dependent metadata results and write a fresh unsigned review package.

    Only canonical entity records survive the reset. All prior dependencies, derived
    tables, and any carried worksheet signature are excluded from the new outputs.
    """
    store = schemas or SchemaStore()
    try:
        output = validate_output_path(output_dir)
    except IngestError as error:
        raise DavError(str(error)) from None

    current = copy.deepcopy(packet)
    require(type(current.get("records")) is dict and type(current.get("config")) is dict,
            "MALFORMED_INPUT")
    raw_records = current["records"]
    current["records"] = {name: copy.deepcopy(rows) for name, rows in raw_records.items()
                           if name in ENTITY_TABLES}
    # Remove historical/derived stage products while retaining every raw canonical entity.
    for tables in DERIVED_TABLES.values():
        for table in tables:
            current["records"].pop(table, None)
    current["dependencies"] = {}
    admission = current["config"].get("admission")
    if isinstance(admission, dict):
        admission.pop("reviewer_worksheet", None)
        admission.pop("worksheet_created_utc", None)

    results: list[dict[str, Any]] = []
    registry = build_registries(current, schemas=store)
    results.append(registry)
    current["records"] = registry["records"]
    if registry["status"] == "READY":
        current["dependencies"]["registries"] = registry
        for stage, function in STAGES:
            result = function(current, schemas=store)
            results.append(result)
            current["records"] = result["records"]
            # Every downstream metadata stage depends only on registries. Keep only
            # newly produced receipts from this invocation.
            current["dependencies"][stage] = result

    worksheet = build_worksheet(current)
    summary = _patient_free_summary(results)

    # Replace only files owned by this command. Never touch the input packet or raw store.
    output.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        target = output / name
        if target.is_symlink():
            raise DavError("OUTPUT_PATH_UNSAFE")
        if target.exists():
            target.unlink()
    (output / "review_packet.json").write_text(
        json.dumps(current, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "reviewer_worksheet.json").write_text(
        json.dumps(worksheet, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "SUMMARY.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"packet": current, "worksheet": worksheet, "summary": summary}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path, help="configured local canonical packet JSON")
    parser.add_argument("--out", required=True, type=Path, help="private output directory under .scratch/runtime")
    args = parser.parse_args(argv)
    try:
        prepare_review(_read_packet(args.packet), args.out)
    except DavError as error:
        parser.error(error.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
