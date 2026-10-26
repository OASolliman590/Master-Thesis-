"""Classify the stored public filenames for the S02 and S03 raw questions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_STUDIES = {
    "QR-GSE188249": ("S02", ["GSE188249", "GSE188250"]),
    "QR-GSE198052": ("S03", ["GSE198052"]),
}
_CLASS_ORDER = ("RAW_ARCHIVE", "FILELIST", "MATRIX_NAME")
_MATRIX_SUFFIXES = (
    ".txt.gz",
    ".tsv.gz",
    ".csv.gz",
    ".mtx.gz",
    ".txt",
    ".tsv",
    ".csv",
    ".mtx",
    ".h5ad",
    ".h5",
    ".rds",
)


def _classify_file_name(file_name: str) -> str:
    lowered = file_name.lower()
    if lowered.endswith("raw.tar"):
        return "RAW_ARCHIVE"
    if file_name == "filelist.txt":
        return "FILELIST"
    if lowered.endswith(_MATRIX_SUFFIXES):
        return "MATRIX_NAME"
    raise ValueError(f"unrecognized exact_file_name: {file_name}")


def build_raw_question(source_records: dict[str, Any]) -> dict[str, Any]:
    """Return filename classifications for the stored S02 and S03 records."""
    if not isinstance(source_records, dict):
        raise ValueError("source object records must be an object")
    records = source_records.get("records")
    if not isinstance(records, list):
        raise ValueError("source object records are missing their records list")

    grouped: dict[str, list[dict[str, str]]] = {"S02": [], "S03": []}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid source object record")
        study = _STUDIES.get(record.get("study_id"))
        if study is None or record.get("access_route") != "PUBLIC_DIRECT":
            continue

        file_name = record.get("exact_file_name")
        if not isinstance(file_name, str) or not file_name:
            raise ValueError("public source record has no exact_file_name")
        classification = _classify_file_name(file_name)
        entry_id, _ = study
        grouped[entry_id].append(
            {"exact_file_name": file_name, "classification": classification}
        )

    questions = []
    for study_id, (entry_id, series_accessions) in _STUDIES.items():
        file_names = grouped[entry_id]
        if not file_names:
            raise ValueError(f"no public filenames found for {entry_id}")
        counts = {name: 0 for name in _CLASS_ORDER}
        for file_record in file_names:
            counts[file_record["classification"]] += 1
        questions.append(
            {
                "entry_id": entry_id,
                "series_accessions": series_accessions,
                "file_names": file_names,
                "file_name_class_counts": counts,
                "matrix_name_present": counts["MATRIX_NAME"] > 0,
            }
        )

    return {
        "schema_version": 1,
        "admitted_count": 0,
        "analysis_ready": False,
        "decisions": [],
        "questions": questions,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    source_path = root / "docs/validation/A_DAV_05/SOURCE_OBJECT_RECORDS.json"
    output_path = root / "docs/validation/A_DAV_07/RAW_QUESTION.json"
    source_records = json.loads(source_path.read_text(encoding="utf-8"))
    result = build_raw_question(source_records)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
