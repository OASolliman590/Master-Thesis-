"""Exact-field input and synthetic provenance guards for A-P1."""

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.a_meta.provenance import canonical_sha256, is_locked_study, known_cohort_ids

from .endpoints import REQUIRED_FIELDS


_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SYNTHETIC_PRODUCER = "tools.a_p1.synthetic_fixture"
_MANIFEST_KIND = "a_p1_input"


def create_synthetic_manifest(
    records: Sequence[Mapping[str, object]], measurement_contract: Mapping[str, object]
) -> dict:
    """Create a hash-bound synthetic provenance object for invented input rows."""
    projected = _project_records(records)
    studies = sorted({str(row["study_id"]) for row in projected})
    _reject_synthetic_real_identities(studies)
    contract = _validate_measurement_contract(measurement_contract)
    return {
        "manifest_version": 1,
        "producer": _SYNTHETIC_PRODUCER,
        "data_classification": "synthetic",
        "kind": _MANIFEST_KIND,
        "selected_fields": list(REQUIRED_FIELDS),
        "cohort_ids": studies,
        "measurement_contract": contract,
        "payload_sha256": _input_hash(projected, contract),
        "synthetic_scope": "invented software fixture; not biological evidence",
    }


def load_input_tsv(
    input_path: Path | str,
    manifest_path: Path | str,
    *,
    allow_outcomes: bool = False,
) -> tuple[list[dict[str, str]], dict]:
    """Preflight the manifest, then read only the exact A-P1 input fields."""
    source_path = assert_allowed_input_path(input_path)
    manifest = preflight_input_manifest(manifest_path, allow_outcomes=allow_outcomes)
    records = _read_selected_fields(source_path)
    _validate_payload_binding(records, manifest)
    return records, manifest


def assert_allowed_input_path(path_value: Path | str) -> Path:
    """Refuse protected or packet paths, including paths reached through symlinks."""
    path = Path(path_value).expanduser()
    candidates = (path, path.resolve(strict=False))
    if any(is_locked_study(candidate.as_posix()) for candidate in candidates):
        raise PermissionError("Protected final-test paths are refused by A-P1")
    if any(candidate.name == "ingestion_packet.json" for candidate in candidates):
        raise PermissionError("A-P1 does not read ingestion packets")
    return path


def preflight_input_manifest(
    manifest_path: Path | str, *, allow_outcomes: bool = False
) -> dict:
    """Read only manifest metadata and apply the outcome release gate."""
    provenance_path = assert_allowed_input_path(manifest_path)
    manifest = _read_manifest(provenance_path)
    _preflight_manifest(manifest, allow_outcomes=allow_outcomes)
    return manifest


def validate_records_provenance(
    records: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    *,
    allow_outcomes: bool = False,
) -> dict:
    """Validate in-memory records through the same guard used by the file API."""
    normalized_manifest = dict(manifest)
    _preflight_manifest(normalized_manifest, allow_outcomes=allow_outcomes)
    projected = _project_records(records)
    _validate_payload_binding(projected, normalized_manifest)
    return normalized_manifest


def is_known_real_identity(value: object) -> bool:
    token = _identity_token(value)
    return token in _known_identity_tokens()


def _read_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("A-P1 provenance manifest is missing or malformed") from error
    if not isinstance(value, dict):
        raise ValueError("A-P1 provenance manifest must be a JSON object")
    return value


def _preflight_manifest(manifest: Mapping[str, object], *, allow_outcomes: bool) -> None:
    if manifest.get("manifest_version") != 1 or manifest.get("kind") != _MANIFEST_KIND:
        raise ValueError("Unsupported A-P1 provenance manifest")
    if tuple(manifest.get("selected_fields", ())) != REQUIRED_FIELDS:
        raise ValueError("A-P1 provenance must bind the exact selected field list")
    cohort_ids = manifest.get("cohort_ids")
    if not isinstance(cohort_ids, list) or not cohort_ids or any(not isinstance(x, str) or not x for x in cohort_ids):
        raise ValueError("A-P1 provenance must declare non-empty cohort identities")
    if any(is_locked_study(value) for value in cohort_ids):
        raise PermissionError("Protected final-test identities are refused by A-P1")
    classification = manifest.get("data_classification")
    identities = set(cohort_ids)
    known = known_cohort_ids()
    if classification == "synthetic":
        if any(is_known_real_identity(value) for value in identities):
            raise ValueError("Synthetic provenance contradicts a known real cohort identity")
        if manifest.get("producer") != _SYNTHETIC_PRODUCER:
            raise ValueError("Synthetic provenance was not created by the A-P1 fixture path")
    elif classification == "real":
        if not identities.issubset(known):
            raise ValueError("Real provenance names an unknown cohort identity")
        if not allow_outcomes:
            raise PermissionError("Real-cohort outcomes are restricted without --allow-outcomes")
        if not str(manifest.get("outcome_release_id", "")).strip():
            raise PermissionError("Real-cohort input requires an explicit outcome release ID")
        if manifest.get("outcome_release_status") != "SIGNED_RELEASED":
            raise PermissionError("Real-cohort input requires a signed outcome release")
        source_hashes = manifest.get("source_object_sha256")
        if (
            not isinstance(source_hashes, list)
            or not source_hashes
            or any(not _HEX_SHA256.fullmatch(str(value)) for value in source_hashes)
        ):
            raise PermissionError("Real-cohort provenance requires source-object SHA-256 values")
    else:
        raise ValueError("A-P1 provenance must classify the input as synthetic or real")
    _validate_measurement_contract(manifest.get("measurement_contract", {}))
    if not _HEX_SHA256.fullmatch(str(manifest.get("payload_sha256", ""))):
        raise ValueError("A-P1 provenance must bind a SHA-256 input payload")


def _validate_payload_binding(
    records: Sequence[Mapping[str, object]], manifest: Mapping[str, object]
) -> None:
    projected = _project_records(records)
    studies = sorted({str(row["study_id"]) for row in projected})
    if studies != sorted(manifest["cohort_ids"]):
        raise ValueError("A-P1 provenance study identities do not match the selected input")
    contract = _validate_measurement_contract(manifest["measurement_contract"])
    if _input_hash(projected, contract) != manifest["payload_sha256"]:
        raise ValueError("A-P1 provenance payload hash does not match selected fields")


def _read_selected_fields(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            headers = next(reader)
        except StopIteration as error:
            raise ValueError("A-P1 input table is empty") from error
        if len(headers) != len(set(headers)):
            raise ValueError("A-P1 input table has duplicate field names")
        indices = {field: headers.index(field) for field in REQUIRED_FIELDS if field in headers}
        missing = set(REQUIRED_FIELDS) - set(indices)
        if missing:
            raise ValueError("A-P1 input table is missing an exact required field")
        rows = []
        for row in reader:
            if len(row) != len(headers):
                raise ValueError("A-P1 input row width does not match its header")
            rows.append({field: row[indices[field]] for field in REQUIRED_FIELDS})
    if not rows:
        raise ValueError("A-P1 input table has no rows")
    return rows


def _project_records(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    if not records:
        raise ValueError("A-P1 input table has no rows")
    projected = []
    for record in records:
        if any(field not in record for field in REQUIRED_FIELDS):
            raise ValueError("A-P1 input is missing an exact required selected field")
        projected.append({field: record[field] for field in REQUIRED_FIELDS})
    return projected


def _validate_measurement_contract(value: object) -> dict:
    if not isinstance(value, Mapping):
        raise ValueError("A-P1 requires an explicit measurement contract")
    required = {
        "representation_id": value.get("representation_id"),
        "unit": value.get("unit"),
        "transform": value.get("transform"),
        "gene_mapping": value.get("gene_mapping"),
        "qualification_status": value.get("qualification_status"),
    }
    if any(not isinstance(item, str) or not item for item in required.values()):
        raise ValueError("A-P1 measurement contract has an empty required field")
    if required["unit"] != "TPM" or required["transform"] != "unlogged_abundance":
        raise ValueError("CYT requires qualified unlogged TPM abundance")
    if required["gene_mapping"] != "unique" or required["qualification_status"] != "qualified":
        raise ValueError("CYT requires uniquely mapped, source-qualified genes")
    return required


def _input_hash(records: Sequence[Mapping[str, object]], measurement_contract: Mapping[str, object]) -> str:
    return canonical_sha256({
        "selected_fields": list(REQUIRED_FIELDS),
        "records": list(records),
        "measurement_contract": dict(measurement_contract),
    })


def _reject_synthetic_real_identities(studies: Sequence[str]) -> None:
    if any(is_locked_study(study) for study in studies):
        raise ValueError("Protected final-test identities cannot be synthetic")
    if any(is_known_real_identity(study) for study in studies):
        raise ValueError("Known real cohort identities cannot be synthetic")


def _identity_token(value: object) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


@lru_cache(maxsize=1)
def _known_identity_tokens() -> frozenset[str]:
    return frozenset(_identity_token(known) for known in known_cohort_ids())
