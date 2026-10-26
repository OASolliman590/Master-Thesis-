"""Build the bounded offline metadata queue from the A-DAV-06 crosswalk."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_PINNED_ENTRY_IDS = frozenset({"ICB-BULK-003", "ICB-BULK-009", "S01"})
_CONTROLLED_PREFIXES = ("EGAS", "EGAD", "phs")
_ACCESSION_PATTERNS = (
    re.compile(r"GSE[0-9]+\Z"),
    re.compile(r"EGAS[0-9]+\Z"),
    re.compile(r"EGAD[0-9]+\Z"),
    re.compile(r"phs[0-9]+\Z"),
    re.compile(r"PRJ(?:NA|EB|DB)[0-9]+\Z"),
)
_IMVIGOR_LABEL = "IMvigor210CoreBiologies"


def _validate_accession(value: Any, entry_id: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid accession for {entry_id}: expected a non-empty string")
    if value == _IMVIGOR_LABEL:
        return value
    if any(pattern.fullmatch(value) for pattern in _ACCESSION_PATTERNS):
        return value
    raise ValueError(f"invalid accession shape for {entry_id}: {value!r}")


def _classify(entry_id: str, accessions: list[str]) -> str:
    if entry_id in {"S02", "S03"}:
        return "RAW_QUESTION"
    if any(accession.startswith(_CONTROLLED_PREFIXES) for accession in accessions):
        return "CONTROLLED_LANDING_ONLY"
    if not accessions:
        return "NO_PUBLIC_ACCESSION"
    if all(accession.startswith("GSE") for accession in accessions):
        return "PUBLIC_GEO_FILELIST"
    if accessions == ["PRJEB23709"]:
        return "NON_GEO_PUBLIC"
    raise ValueError(f"cannot classify accession combination for {entry_id}")


def build_metadata_queue(crosswalk: dict[str, Any]) -> dict[str, Any]:
    """Return the A-DAV-07 queue as a deterministic function of a crosswalk."""
    if not isinstance(crosswalk, dict):
        raise ValueError("crosswalk must be an object")
    lanes = crosswalk.get("lanes")
    if not isinstance(lanes, dict):
        raise ValueError("crosswalk is missing lane mapping")

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for lane in ("I", "E"):
        rows = lanes.get(lane)
        if not isinstance(rows, list):
            raise ValueError(f"missing lane {lane}")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"invalid row in lane {lane}")
            entry_id = row.get("entry_id")
            if not isinstance(entry_id, str) or not entry_id:
                raise ValueError(f"invalid entry id in lane {lane}")
            if entry_id in seen_ids:
                raise ValueError(f"duplicate entry id: {entry_id}")
            seen_ids.add(entry_id)

            accessions = row.get("public_series_accessions")
            if not isinstance(accessions, list):
                raise ValueError(f"invalid accession list for {entry_id}")
            validated = [_validate_accession(value, entry_id) for value in accessions]

            if entry_id in _PINNED_ENTRY_IDS:
                continue
            records.append(
                {
                    "entry_id": entry_id,
                    "lane": lane,
                    "queue_class": _classify(entry_id, validated),
                    "public_series_accessions": validated,
                }
            )

    return {
        "schema_version": 1,
        "admitted_count": 0,
        "analysis_ready": False,
        "decisions": [],
        "queue": records,
    }


def write_metadata_queue(crosswalk_path: Path, output_path: Path) -> None:
    """Read a crosswalk and write its deterministic metadata queue as JSON."""
    crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    queue = build_metadata_queue(crosswalk)
    output_path.write_text(
        json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    write_metadata_queue(
        root / "docs/validation/A_DAV_06/LANE_CROSSWALK.json",
        root / "docs/validation/A_DAV_07/METADATA_QUEUE.json",
    )


if __name__ == "__main__":
    main()
