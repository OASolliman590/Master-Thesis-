"""Fail-closed provenance checks shared by the A-META public interfaces."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/cohorts/REGISTRY.tsv"
SYNTHETIC_FIXTURE_PRODUCER = "tools.a_meta.synthetic_fixture"
_LOCKED = "imvigor210"


def known_cohort_ids() -> set[str]:
    with REGISTRY.open(newline="", encoding="utf-8") as stream:
        return {row["cohort_id"] for row in csv.DictReader(stream, delimiter="\t")}


def is_locked_study(value: object) -> bool:
    token = "".join(character for character in str(value).casefold() if character.isalnum())
    return _LOCKED in token


def canonical_sha256(value: object) -> str:
    payload = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def effect_input_payload(view, features) -> dict:
    metadata = view.metadata
    if hasattr(features, "values_by_unit"):
        feature_values = features.values_by_unit
        unit_family = getattr(features, "unit_family", None)
    else:
        feature_values = [dict(row) for row in _feature_records(features)]
        unit_family = None
    return {
        "cohort_id": str(getattr(metadata, "cohort_id", "")),
        "cancer": str(getattr(metadata, "cancer", "")),
        "endpoint_families": list(getattr(metadata, "endpoint_families", ())),
        "uniform_drug_class": getattr(metadata, "uniform_drug_class", None),
        "clinical_rows": [dict(row) for row in view.clinical_rows],
        "unit_family": unit_family,
        "features": feature_values,
    }


def effect_rows_payload(rows) -> list[dict]:
    return [dict(row) for row in rows]


def validate_effect_input_provenance(
    view,
    features,
    *,
    allow_outcomes: bool,
    provenance_manifest: Path | str | None = None,
) -> None:
    cohort_id = str(getattr(view.metadata, "cohort_id", ""))
    _guard_cohort_ids((cohort_id,), allow_outcomes=allow_outcomes)
    manifest = _read_manifest(provenance_manifest)
    if manifest is None:
        if cohort_id in known_cohort_ids():
            if not allow_outcomes:
                raise ValueError("Real-cohort effects are restricted without allow_outcomes=True")
            return
        if allow_outcomes:
            return
        raise ValueError("Synthetic effects require a hash-matched synthetic-fixture manifest")
    if manifest.get("data_classification") == "synthetic":
        if cohort_id in known_cohort_ids():
            raise ValueError("Synthetic provenance contradicts a known real cohort")
        if manifest.get("kind") == "feature_bundle":
            _validate_synthetic_manifest_header(manifest, expected_kind="feature_bundle")
            if set(manifest.get("cohort_ids", ())) != {cohort_id}:
                raise ValueError("Synthetic feature manifest cohort does not match the cohort view")
            family = str(getattr(features, "unit_family", ""))
            expected_hash = manifest.get("effect_input_sha256", {}).get(family)
            if expected_hash != canonical_sha256(effect_input_payload(view, features)):
                raise ValueError("Synthetic feature manifest does not match the cohort and feature hashes")
            return
        _validate_synthetic_manifest(
            manifest,
            expected_kind="study_effects_input",
            expected_sha256=canonical_sha256(effect_input_payload(view, features)),
            cohort_ids=(cohort_id,),
        )
        return
    if manifest.get("data_classification") == "real":
        if cohort_id not in known_cohort_ids():
            raise ValueError("Real provenance names an unknown cohort")
        if not allow_outcomes:
            raise ValueError("Real-cohort effects are restricted without allow_outcomes=True")
        if manifest.get("cohort") != cohort_id:
            raise ValueError("Feature manifest cohort does not match the cohort view")
        return
    raise ValueError("Analysis provenance is missing a supported data classification")


def validate_effect_rows_provenance(
    effects,
    rows: list[dict],
    *,
    allow_outcomes: bool,
    provenance_manifest: Path | str | None = None,
) -> None:
    study_ids = {str(row.get("study", "")) for row in rows if str(row.get("study", ""))}
    _guard_cohort_ids(study_ids, allow_outcomes=allow_outcomes)
    manifest = _read_manifest(provenance_manifest)
    known = known_cohort_ids()
    real_studies = study_ids & known
    if manifest is not None and manifest.get("data_classification") == "synthetic":
        if real_studies:
            raise ValueError("Synthetic provenance contradicts one or more known real cohorts")
        if isinstance(effects, (str, Path)):
            path = Path(effects)
            expected = manifest.get("outputs_sha256", {}).get(path.name)
            if not expected or file_sha256(path) != expected:
                raise ValueError("Synthetic effect manifest does not match the effect-table hash")
            _validate_synthetic_manifest_header(manifest, expected_kind="effect_table")
            if set(manifest.get("cohort_ids", ())) != study_ids:
                raise ValueError("Synthetic effect manifest cohort IDs do not match the effect table")
            if manifest.get("cohort") and manifest.get("cohort") not in study_ids:
                raise ValueError("Synthetic effect manifest cohort contradicts the effect table")
        else:
            _validate_synthetic_manifest(
                manifest,
                expected_kind="effect_rows",
                expected_sha256=canonical_sha256(effect_rows_payload(rows)),
                cohort_ids=study_ids,
            )
        return
    if real_studies:
        if not allow_outcomes:
            raise ValueError("Real-cohort synthesis is restricted without allow_outcomes=True")
        if manifest is not None:
            if manifest.get("data_classification") != "real":
                raise ValueError("Effect-table provenance contradicts known real cohort IDs")
            _validate_effect_file_hash(effects, manifest)
        return
    if manifest is not None and manifest.get("data_classification") == "real":
        raise ValueError("Real effect provenance has no known real cohort IDs")
    if allow_outcomes:
        return
    raise ValueError("Synthetic synthesis requires a hash-matched synthetic-fixture manifest")


def validate_effect_file_manifest(path: Path | str, *, allow_outcomes: bool) -> tuple[dict, bool]:
    effect_path = Path(path)
    manifest_path = effect_path.parent / "manifest.json"
    manifest = _read_manifest(manifest_path)
    if manifest is None:
        raise ValueError("Effect table requires a verifiable manifest")
    classification = manifest.get("data_classification")
    if classification == "synthetic":
        _validate_synthetic_manifest_header(manifest, expected_kind="effect_table")
        cohort = str(manifest.get("cohort", ""))
        declared_studies = {str(value) for value in manifest.get("cohort_ids", ())}
        if is_locked_study(cohort) or any(is_locked_study(value) for value in declared_studies):
            raise ValueError("IMvigor210 is a locked final test and is refused by A-META")
        if cohort in known_cohort_ids() or declared_studies & known_cohort_ids():
            raise ValueError("Synthetic provenance contradicts a known real cohort")
        _validate_effect_file_hash(effect_path, manifest)
        with effect_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if "study" not in (reader.fieldnames or []):
                raise ValueError("Effect table requires a study column")
            studies = {str(row.get("study", "")) for row in reader if row.get("study")}
        if set(manifest.get("cohort_ids", ())) != studies:
            raise ValueError("Synthetic effect manifest cohort IDs do not match the effect table")
        if any(is_locked_study(study) for study in studies):
            raise ValueError("IMvigor210 is a locked final test and is refused by A-META")
        if studies & known_cohort_ids():
            raise ValueError("Synthetic provenance contradicts a known real cohort")
        return manifest, False
    if classification == "real":
        cohort = str(manifest.get("cohort", ""))
        if cohort not in known_cohort_ids():
            raise ValueError("Real effect manifest names an unknown cohort")
        if is_locked_study(cohort):
            raise ValueError("IMvigor210 is a locked final test and is refused by A-META")
        if not allow_outcomes:
            raise ValueError("Real-cohort synthesis requires the explicit --allow-outcomes flag")
        _validate_effect_file_hash(effect_path, manifest)
        return manifest, True
    raise ValueError("Effect manifest must declare data_classification as real or synthetic")


def preflight_effect_file(
    path: Path | str,
    *,
    allow_outcomes: bool,
    provenance_manifest: Path | str | None = None,
) -> bool:
    """Reject restricted path inputs from their manifest before reading effects."""
    effect_path = Path(path)
    manifest_path = Path(provenance_manifest) if provenance_manifest is not None else effect_path.parent / "manifest.json"
    manifest = _read_manifest(manifest_path)
    if manifest is None:
        raise ValueError("Effect table requires a verifiable manifest")
    classification = manifest.get("data_classification")
    cohort = str(manifest.get("cohort", ""))
    cohort_ids = {str(value) for value in manifest.get("cohort_ids", ())}
    if is_locked_study(cohort) or any(is_locked_study(value) for value in cohort_ids):
        raise ValueError("IMvigor210 is a locked final test and is refused by A-META")
    known = known_cohort_ids()
    if classification == "real":
        if cohort not in known:
            raise ValueError("Real effect manifest names an unknown cohort")
        if not allow_outcomes:
            raise ValueError("Real-cohort synthesis is restricted without allow_outcomes=True")
        _validate_effect_file_hash(effect_path, manifest)
        return True
    if classification == "synthetic":
        _validate_synthetic_manifest_header(manifest, expected_kind="effect_table")
        if cohort in known or cohort_ids & known:
            raise ValueError("Synthetic provenance contradicts a known real cohort")
        _validate_effect_file_hash(effect_path, manifest)
        return False
    raise ValueError("Effect manifest must declare data_classification as real or synthetic")


def write_synthetic_fixture_manifest(
    path: Path | str,
    *,
    kind: str,
    payload: object | None = None,
    payload_sha256: str | None = None,
    cohort_ids=(),
    output_path: Path | str | None = None,
) -> dict:
    """Write the explicit synthetic-fixture provenance used by tests and toy runs."""
    if (payload is None) == (payload_sha256 is None):
        raise ValueError("Provide exactly one of payload or payload_sha256")
    manifest_path = Path(path)
    content_hash = canonical_sha256(payload) if payload_sha256 is None else str(payload_sha256)
    manifest = {
        "manifest_version": 1,
        "producer": SYNTHETIC_FIXTURE_PRODUCER,
        "data_classification": "synthetic",
        "kind": kind,
        "payload_sha256": content_hash,
        "cohort_ids": sorted({str(value) for value in cohort_ids}),
    }
    if output_path is not None:
        output = Path(output_path)
        manifest["outputs_sha256"] = {output.name: file_sha256(output)}
        manifest["cohort"] = manifest["cohort_ids"][0] if len(manifest["cohort_ids"]) == 1 else ""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _guard_cohort_ids(cohort_ids, *, allow_outcomes: bool) -> None:
    ids = {str(value) for value in cohort_ids if str(value)}
    if any(is_locked_study(value) for value in ids):
        raise ValueError("IMvigor210 is a locked final test and is refused by A-META")
    real_ids = ids & known_cohort_ids()
    if real_ids and not allow_outcomes:
        raise ValueError("Real-cohort outcomes are restricted without allow_outcomes=True")


def _validate_synthetic_manifest(manifest, *, expected_kind, expected_sha256, cohort_ids) -> None:
    _validate_synthetic_manifest_header(manifest, expected_kind=expected_kind)
    if manifest.get("payload_sha256") != expected_sha256:
        raise ValueError("Synthetic fixture manifest does not match the input hash")
    declared = set(manifest.get("cohort_ids", ()))
    if declared != {str(value) for value in cohort_ids if str(value)}:
        raise ValueError("Synthetic fixture manifest cohort IDs do not match the inputs")


def _validate_synthetic_manifest_header(manifest, *, expected_kind) -> None:
    if manifest.get("producer") != SYNTHETIC_FIXTURE_PRODUCER:
        raise ValueError("Synthetic classification was not written by the synthetic-fixture path")
    if manifest.get("data_classification") != "synthetic" or manifest.get("kind") != expected_kind:
        raise ValueError("Synthetic fixture manifest has the wrong kind or classification")
    if manifest.get("manifest_version") != 1:
        raise ValueError("Unsupported synthetic fixture manifest version")


def _validate_effect_file_hash(path, manifest) -> None:
    if not isinstance(path, (str, Path)):
        raise ValueError("An effect-file manifest cannot authenticate in-memory rows")
    effect_path = Path(path)
    expected = manifest.get("outputs_sha256", {}).get(effect_path.name)
    if not expected or file_sha256(effect_path) != expected:
        raise ValueError("Effect manifest output hash does not match the current effect table")


def _read_manifest(path):
    if path is None:
        return None
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Analysis provenance manifest is missing or malformed") from error
    if not isinstance(manifest, dict):
        raise ValueError("Analysis provenance manifest must contain a JSON object")
    return manifest


def _feature_records(features):
    if hasattr(features, "records"):
        return list(features.records)
    if isinstance(features, Mapping):
        return list(features.get("records", ()))
    return list(features)


def _jsonable(value):
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return value
    return str(value)
