"""Patient-free readiness for the specified Paper A comparator set."""
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs/research/A_COMPARATOR_READINESS_W6_20261107.tsv"
_COLUMNS = (
    "method_id",
    "source_urls",
    "immutable_identity",
    "prior_source_family_use",
    "measurement_coverage_missing_policy",
    "implementation_state",
    "admission_blocker",
    "future_command",
)


class ComparatorNotReady(ValueError):
    """Raised when a comparator has no verified executable rule."""


def method_statuses() -> list[dict[str, str]]:
    """Return the fixed, patient-free W6 registry rows in document order."""
    with REGISTRY_PATH.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != _COLUMNS:
            raise ValueError("Comparator readiness registry columns do not match its contract")
        rows = list(reader)
    method_ids = [row["method_id"] for row in rows]
    if any(not method_id for method_id in method_ids) or len(set(method_ids)) != len(method_ids):
        raise ValueError("Comparator readiness registry has a missing or duplicate method ID")
    if any(any(not row[column] for column in _COLUMNS) for row in rows):
        raise ValueError("Comparator readiness registry has an empty required field")
    return rows


def method_status(method_id: str) -> dict[str, str]:
    for row in method_statuses():
        if row["method_id"] == method_id:
            return row
    raise KeyError(f"Unknown Paper A comparator: {method_id}")


def require_method_ready(method_id: str) -> dict[str, str]:
    row = method_status(method_id)
    if row["implementation_state"] != "READY":
        raise ComparatorNotReady(
            f"{method_id} is {row['implementation_state']}: {row['admission_blocker']}"
        )
    return row
