"""Synthetic-tested patient-level exploratory single-cell response contrasts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd


@dataclass(frozen=True)
class SC3Group:
    cohort: str
    source_family: str
    compartment: str
    endpoint_family: str
    profile_ids: tuple[str, ...]
    n_r: int
    n_nr: int


SC_ENDPOINT_MAPPINGS = {
    "RECIST": ("orr", "ORR"),
    "pathology": ("source_label", "SOURCE_LABEL_UNSPECIFIED"),
    "expansion": ("source_label", "SOURCE_LABEL_UNSPECIFIED"),
}
SC3_IDENTITY_COLUMNS = ("cohort", "source_family", "profile_id", "patient_id", "sample_id")
SC3_R_CLINICAL_COLUMNS = frozenset({
    "profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment",
    "endpoint_family", "response_metric", "outcome_label", "response", "eligible", "baseline",
    "treatment", "drug_class", "sc3_group_id", "n_cells", "total_umis", "library_size", "cancer",
})
SC3_RELEASE_SCOPE = "SC3_REAL_OUTCOME_ACCESS"
SC3_RELEASE_OPERATION = "sc3-analysis"
SC3_RELEASE_RECORD_TYPE = "sc3_user_release_v1"
SC3_RELEASE_OUTCOME_FIELDS = (
    "endpoint_family", "outcome_label", "response", "response_metric",
)
SC3_SOURCE_PRODUCER = "tools.sc.sc3_source_provenance"
_SC3_RELEASE_TOKEN = object()


@dataclass(frozen=True)
class _VerifiedSC3Release:
    proof: object
    manifest_path: Path
    release_record_path: Path
    decision_path: Path
    manifest: Mapping
    input_sha256: Mapping[str, str]
    cohorts: frozenset[str]
    source_family_by_cohort: Mapping[str, str]
    classification: str
    test_only_root: Path | None = None
    test_registry_root: Path | None = None


def metric_family(metric: str | None) -> str | None:
    value = str(metric or "").strip().casefold().replace("_", " ")
    if value in {"t cell expansion", "t-cell expansion", "expansion"}:
        return "expansion"
    if value in {"recist", "objective response", "orr"}:
        return "RECIST"
    if value in {"pathology", "pathological response", "pathology response"}:
        return "pathology"
    return None


def outcome_fields(metric: str | None, label: str | None) -> dict[str, str | None]:
    family = metric_family(metric)
    value = str(label or "").strip().upper()
    outcome = value if value in {"R", "NR"} else None
    return {
        "endpoint_family": family,
        "response": outcome if family != "expansion" else None,
        "outcome_label": outcome,
    }


def guard_sc3(
    *,
    is_synthetic: bool,
    allow_outcomes: bool,
    clinical: pd.DataFrame | None = None,
    provenance_manifest: Path | str | None = None,
) -> None:
    if allow_outcomes:
        raise PermissionError("SC-3 real-outcome execution is not released; invented synthetic data only")
    if is_synthetic:
        if clinical is None:
            raise PermissionError("Synthetic SC-3 requires clinical profiles and a verified provenance manifest")
        authorize_sc3(clinical, provenance_manifest=provenance_manifest)
    else:
        raise PermissionError("SC-3 real-outcome execution is not released; invented synthetic data only")


def _sc3_payload(clinical: pd.DataFrame) -> dict:
    frame = clinical.copy().astype(object)
    frame = frame.where(pd.notna(frame), None)
    return {"profiles": frame.to_dict(orient="records")}


def _reject_sc3_symlinks(path: Path | str) -> Path:
    raw = str(path)
    original = Path(path).expanduser()
    if not original.is_absolute():
        original = Path.cwd() / original
    candidates = (raw, str(original), str(original.resolve(strict=False)))
    for candidate in candidates:
        for component in re.split(r"[\\/]+", candidate):
            token = re.sub(r"[^a-z0-9]", "", component.casefold())
            if "imvigor210" in token or "ingestionpacketjson" in token:
                raise ValueError("SC-3 paths cannot reference forbidden protected paths")
    current = Path(original.anchor)
    for part in original.parts[1:]:
        if part in {"", "."}:
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            raise ValueError(f"SC-3 paths cannot contain symlinks: {current.name}")
    return original


def _existing_sc3_file(path: Path | str) -> Path:
    original = _reject_sc3_symlinks(path)
    resolved = original.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("SC-3 inputs and provenance must be regular files")
    return resolved


def _new_sc3_directory(path: Path | str) -> Path:
    original = _reject_sc3_symlinks(path)
    parent = original.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("SC-3 output parent must be a directory")
    target = parent / original.name
    if target.exists() or target.is_symlink():
        raise ValueError("SC-3 output must be a new directory")
    return target


def _preflight_sc3_paths(
    input_paths: Mapping[str, Path | str],
    provenance_path: Path | str,
    output_dir: Path | str | None = None,
    retention_dir: Path | str | None = None,
) -> tuple[dict[str, Path], Path, Path | None, Path | None]:
    """Validate SC-3 paths and aliases before a payload is read or hashed."""
    inputs = {name: _existing_sc3_file(path) for name, path in input_paths.items()}
    provenance = _existing_sc3_file(provenance_path)
    all_files = [*inputs.values(), provenance]
    if len({str(path) for path in all_files}) != len(all_files):
        raise ValueError("SC-3 input and provenance paths must identify distinct files")
    for left_index, left in enumerate(all_files):
        for right in all_files[left_index + 1:]:
            if os.path.samefile(left, right):
                raise ValueError("SC-3 input and provenance paths cannot alias the same file")

    output = _new_sc3_directory(output_dir) if output_dir is not None else None
    retention = None
    if retention_dir is not None:
        retention_original = _reject_sc3_symlinks(retention_dir)
        retention_parent = retention_original.parent.resolve(strict=True)
        retention = retention_parent / retention_original.name
        if retention.exists() and not retention.is_dir():
            raise ValueError("SC-3 R retention path must be a directory")
        if retention.is_symlink():
            raise ValueError("SC-3 R retention path cannot be a symlink")

    for destination in (output, retention):
        if destination is None:
            continue
        for source in all_files:
            if destination == source or destination in source.parents:
                raise ValueError("SC-3 output and R retention paths cannot contain input or provenance files")
        if output is not None and retention is not None and (
            output == retention or output in retention.parents or retention in output.parents
        ):
            raise ValueError("SC-3 output and R retention paths must be separate")
    return inputs, provenance, output, retention


def _input_sha256(path: Path) -> str:
    path = _reject_sc3_symlinks(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_sc3_identity(path: Path) -> pd.DataFrame:
    path = _reject_sc3_symlinks(path)
    with path.open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream, delimiter="\t"), [])
    if not header or len(header) != len(set(header)):
        raise ValueError("SC-3 clinical header is missing or duplicated")
    if not set(SC3_IDENTITY_COLUMNS).issubset(header):
        raise ValueError("SC-3 clinical input is missing named identity columns")
    return pd.read_csv(
        path, sep="\t", usecols=list(SC3_IDENTITY_COLUMNS), dtype=str, keep_default_na=False,
    )


def _validate_sc3_identity(identity: pd.DataFrame, declared_cohorts: set[str]) -> None:
    cohorts = set(identity["cohort"].astype(str).str.strip())
    real_cohorts = cohorts & (_real_sc_cohorts() | _known_cohorts())
    if real_cohorts or any(_is_locked(value) for value in cohorts):
        raise PermissionError("SC-3 refuses known-real or protected cohort identifiers")
    if "" in cohorts or cohorts != declared_cohorts:
        raise PermissionError("SC-3 synthetic manifest cohort IDs do not match the named clinical identities")
    for column in ("source_family", "profile_id", "patient_id", "sample_id"):
        values = identity[column].astype(str).str.strip()
        if values.eq("").any():
            raise ValueError(f"SC-3 clinical identity column {column} contains an empty value")
    cohort_sources = identity.groupby("cohort", dropna=False)["source_family"].nunique()
    source_cohorts = identity.groupby("source_family", dropna=False)["cohort"].nunique()
    if (cohort_sources > 1).any() or (source_cohorts > 1).any():
        raise ValueError("SC-3 source-family metadata must map one cohort to one source family")
    stable_identity = identity.groupby(["patient_id", "sample_id"], dropna=False)[
        ["cohort", "source_family"]
    ].nunique()
    if (stable_identity > 1).any().any():
        raise ValueError("SC-3 stable patient/specimen identities occur in multiple source cohorts")
    if identity["profile_id"].duplicated().any():
        raise ValueError("SC-3 profile identities must be unique")


def _require_path_within(path: Path, root: Path, label: str) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise PermissionError(f"SC-3 {label} must remain inside the test-only fixture root") from error


def _release_registry_cohorts(test_registry_root: Path | None) -> set[str]:
    if test_registry_root is None:
        return _real_sc_cohorts() | _known_cohorts()
    registry = _reject_sc3_symlinks(test_registry_root / "docs" / "cohorts" / "REGISTRY.tsv")
    lin_map = _reject_sc3_symlinks(test_registry_root / "tools" / "sc" / "lin_cohort_map.tsv")
    if not registry.is_file() or not lin_map.is_file():
        raise PermissionError("SC-3 test-only registry fixtures are incomplete")
    registry_ids = pd.read_csv(registry, sep="\t", usecols=["cohort_id"], dtype=str)["cohort_id"]
    lin_ids = pd.read_csv(lin_map, sep="\t", usecols=["cohort"], dtype=str)["cohort"]
    return set(registry_ids.dropna().astype(str)) | set(lin_ids.dropna().astype(str))


def _validate_released_identity(
    identity: pd.DataFrame,
    cohorts: set[str],
    source_family_by_cohort: Mapping[str, str],
    registered_cohorts: set[str],
) -> None:
    actual_cohorts = set(identity["cohort"].astype(str).str.strip())
    if any(_is_locked(cohort) for cohort in actual_cohorts | cohorts):
        raise PermissionError("SC-3 refuses the locked IMvigor210 final test")
    if actual_cohorts != cohorts:
        raise PermissionError("SC-3 release cohort set does not match named clinical identities")
    unknown = cohorts - registered_cohorts
    if unknown:
        raise PermissionError(
            f"SC-3 source mapping is unresolved for unregistered cohorts: {sorted(unknown)}"
        )
    actual_sources = {
        str(cohort): str(source)
        for cohort, source in identity[["cohort", "source_family"]].drop_duplicates().itertuples(index=False, name=None)
    }
    if actual_sources != dict(source_family_by_cohort):
        raise PermissionError("SC-3 source-family mapping does not match named clinical identities")
    _validate_sc3_identity_relations(identity)


def _validate_sc3_identity_relations(identity: pd.DataFrame) -> None:
    for column in ("source_family", "profile_id", "patient_id", "sample_id"):
        if identity[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"SC-3 clinical identity column {column} contains an empty value")
    cohort_sources = identity.groupby("cohort", dropna=False)["source_family"].nunique()
    source_cohorts = identity.groupby("source_family", dropna=False)["cohort"].nunique()
    if (cohort_sources > 1).any() or (source_cohorts > 1).any():
        raise ValueError("SC-3 source-family metadata must map one cohort to one source family")
    stable_identity = identity.groupby(["patient_id", "sample_id"], dropna=False)[
        ["cohort", "source_family"]
    ].nunique()
    if (stable_identity > 1).any().any():
        raise ValueError("SC-3 stable patient/specimen identities occur in multiple source cohorts")
    if identity["profile_id"].duplicated().any():
        raise ValueError("SC-3 profile identities must be unique")


def preflight_sc3_release(
    input_paths: Mapping[str, Path | str],
    provenance_path: Path | str,
    release_record_path: Path | str | None,
    output_dir: Path | str,
    *,
    allow_outcomes: bool,
    retention_dir: Path | str | None = None,
    test_only_root: Path | str | None = None,
    test_registry_root: Path | str | None = None,
) -> tuple[dict[str, Path], Path, Path, Path, _VerifiedSC3Release, Path | None]:
    """Verify a scoped SC-3 release before reading outcomes or hashing payload inputs."""
    paths_to_guard = [*input_paths.values(), provenance_path, output_dir]
    paths_to_guard.extend(path for path in (release_record_path, retention_dir, test_only_root, test_registry_root) if path is not None)
    for path in paths_to_guard:
        _reject_sc3_symlinks(path)
    if allow_outcomes is not True:
        raise PermissionError("SC-3 source-derived outcomes require explicit opt-in")
    if release_record_path is None:
        raise PermissionError("SC-3 source-derived outcomes require a scoped release record")
    if set(input_paths) != {"clinical", "expression"}:
        raise ValueError("SC-3 release requires only named clinical and expression inputs")

    inputs, provenance, output, retention = _preflight_sc3_paths(
        input_paths, provenance_path, output_dir, retention_dir,
    )
    assert output is not None
    release_record = _existing_sc3_file(release_record_path)
    file_paths = [*inputs.values(), provenance, release_record]
    if len({str(path) for path in file_paths}) != len(file_paths):
        raise ValueError("SC-3 release record cannot alias an input or provenance file")
    for left_index, left in enumerate(file_paths):
        for right in file_paths[left_index + 1:]:
            if os.path.samefile(left, right):
                raise ValueError("SC-3 release record and inputs must be distinct files")
    for destination in (output, retention):
        if destination is None:
            continue
        if any(destination == source or destination in source.parents for source in file_paths):
            raise ValueError("SC-3 output and retention paths cannot contain release inputs")

    fixture_root = None
    fixture_registry = None
    if test_only_root is not None:
        fixture_root = _reject_sc3_symlinks(test_only_root).resolve(strict=True)
        if not fixture_root.is_dir():
            raise PermissionError("SC-3 test-only fixture root must be an existing directory")
        for path in (*file_paths, output, *([retention] if retention is not None else [])):
            _require_path_within(path, fixture_root, "test-only path")
        if test_registry_root is None:
            raise PermissionError("SC-3 test-only release requires an explicit test registry root")
        fixture_registry = _reject_sc3_symlinks(test_registry_root).resolve(strict=True)
        _require_path_within(fixture_registry, fixture_root, "test-only registry")
    elif test_registry_root is not None:
        raise PermissionError("SC-3 registry overrides are available only for test-only fixtures")

    try:
        record = json.loads(release_record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionError("SC-3 scoped release record is missing or malformed") from error
    if not isinstance(record, dict):
        raise PermissionError("SC-3 scoped release record is malformed")
    if record.get("record_type") != SC3_RELEASE_RECORD_TYPE or record.get("release_scope") != SC3_RELEASE_SCOPE:
        raise PermissionError("SC-3 release record has the wrong type or scope")

    expected_status = "TEST_ONLY_APPROVED" if fixture_root is not None else "APPROVED"
    if record.get("record_status") != expected_status:
        raise PermissionError("SC-3 release record is not approved for this execution mode")
    if record.get("real_authorization") is not (fixture_root is None):
        raise PermissionError("SC-3 release record classification is inconsistent")
    if record.get("operation") != SC3_RELEASE_OPERATION:
        raise PermissionError("SC-3 release record does not authorize this operation")
    if set(record) != {
        "record_type", "record_status", "real_authorization", "release_scope", "operation",
        "input_manifest_sha256", "input_sha256", "cohorts", "source_family_by_cohort",
        "source_resolution_status", "overlap_resolution_status", "metric_resolution_status",
        "outcome_fields", "decision",
    }:
        raise PermissionError("SC-3 release record has missing or contradictory fields")

    record_cohorts = record.get("cohorts")
    if (
        not isinstance(record_cohorts, (list, tuple))
        or not record_cohorts
        or any(not isinstance(value, str) or not value or value.strip() != value for value in record_cohorts)
        or len(set(record_cohorts)) != len(record_cohorts)
    ):
        raise PermissionError("SC-3 release record needs an exact unique cohort set")
    declared_cohorts = set(record_cohorts)
    if any(_is_locked(cohort) for cohort in declared_cohorts):
        raise PermissionError("SC-3 refuses the locked IMvigor210 final test")
    decision = record.get("decision")
    if not isinstance(decision, dict) or set(decision) != {"identity", "path", "sha256"}:
        raise PermissionError("SC-3 release record must reference a scoped decision identity and hash")
    decision_identity = decision.get("identity")
    decision_relative = decision.get("path")
    decision_hash = decision.get("sha256")
    if (
        not isinstance(decision_identity, str) or not decision_identity
        or not isinstance(decision_relative, str) or not decision_relative.startswith("docs/decisions/")
        or not re.fullmatch(r"[0-9a-f]{64}", str(decision_hash or ""))
    ):
        raise PermissionError("SC-3 release decision reference is incomplete")
    if Path(decision_relative).is_absolute() or ".." in Path(decision_relative).parts:
        raise PermissionError("SC-3 release decision path must remain under docs/decisions")
    decision_root = fixture_root if fixture_root is not None else Path(__file__).resolve().parents[2]
    decision_path = _existing_sc3_file(decision_root / decision_relative)
    if decision_path.stem != decision_identity:
        raise PermissionError("SC-3 release decision identity does not match its path")
    try:
        decision_path.relative_to((decision_root / "docs" / "decisions").resolve(strict=True))
    except (OSError, ValueError) as error:
        raise PermissionError("SC-3 release decision is outside its scoped decision directory") from error
    if fixture_root is not None:
        _require_path_within(decision_path, fixture_root, "test-only decision")
    if any(os.path.samefile(decision_path, source) for source in file_paths):
        raise ValueError("SC-3 release decision cannot alias an input or release record")
    for destination in (output, retention):
        if destination is not None and (destination == decision_path or destination in decision_path.parents):
            raise ValueError("SC-3 output and retention paths cannot contain the release decision")
    if _input_sha256(decision_path) != decision_hash:
        raise PermissionError("SC-3 release decision identity or exact file hash does not match")

    manifest_hash = _input_sha256(provenance)
    if record.get("input_manifest_sha256") != manifest_hash:
        raise PermissionError("SC-3 release record does not bind this exact input manifest")
    try:
        manifest = json.loads(provenance.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionError("SC-3 source-derived input provenance is missing or malformed") from error
    expected_classification = "source_derived_test_fixture" if fixture_root is not None else "real"
    if (
        not isinstance(manifest, dict)
        or manifest.get("manifest_version") != 1
        or manifest.get("producer") != SC3_SOURCE_PRODUCER
        or manifest.get("data_classification") != expected_classification
        or manifest.get("kind") != "sc3_input"
    ):
        raise PermissionError("SC-3 requires hash-matched source-derived provenance; synthetic fixture provenance cannot be relabelled")
    manifest_cohort_values = manifest.get("cohort_ids")
    if (
        not isinstance(manifest_cohort_values, (list, tuple))
        or not manifest_cohort_values
        or any(not isinstance(value, str) or not value or value.strip() != value for value in manifest_cohort_values)
        or len(set(manifest_cohort_values)) != len(manifest_cohort_values)
    ):
        raise PermissionError("SC-3 source provenance needs an exact unique cohort set")
    manifest_cohorts = set(manifest_cohort_values)
    source_family_by_cohort = manifest.get("source_family_by_cohort")
    expected_hashes = record.get("input_sha256")
    manifest_hashes = manifest.get("input_sha256")
    if (
        not isinstance(source_family_by_cohort, dict)
        or set(source_family_by_cohort) != manifest_cohorts
        or any(not isinstance(value, str) or not value.strip() for value in source_family_by_cohort.values())
        or manifest_cohorts != declared_cohorts
        or not isinstance(expected_hashes, dict)
        or set(expected_hashes) != {"clinical", "expression"}
        or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in expected_hashes.values())
        or manifest_hashes != expected_hashes
        or not isinstance(manifest_hashes, dict)
        or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in manifest_hashes.values())
        or record.get("source_family_by_cohort") != source_family_by_cohort
        or record.get("source_resolution_status") != "RESOLVED"
        or manifest.get("source_resolution_status") != "RESOLVED"
        or record.get("overlap_resolution_status") != "RESOLVED"
        or manifest.get("overlap_resolution_status") != "RESOLVED"
        or record.get("metric_resolution_status") != "RESOLVED"
        or manifest.get("metric_resolution_status") != "RESOLVED"
        or record.get("outcome_fields") != list(SC3_RELEASE_OUTCOME_FIELDS)
    ):
        raise PermissionError("SC-3 release record does not match source, overlap, metric, cohort, or outcome scope")

    identity = _read_sc3_identity(inputs["clinical"])
    registered = _release_registry_cohorts(fixture_registry)
    _validate_released_identity(identity, declared_cohorts, source_family_by_cohort, registered)

    input_hashes = {name: _input_sha256(inputs[name]) for name in ("clinical", "expression")}
    if input_hashes != expected_hashes:
        raise PermissionError("SC-3 release record does not bind these exact clinical and expression inputs")
    verified = _VerifiedSC3Release(
        proof=_SC3_RELEASE_TOKEN,
        manifest_path=provenance,
        release_record_path=release_record,
        decision_path=decision_path,
        manifest=manifest,
        input_sha256=input_hashes,
        cohorts=frozenset(declared_cohorts),
        source_family_by_cohort=dict(source_family_by_cohort),
        classification=expected_classification,
        test_only_root=fixture_root,
        test_registry_root=fixture_registry,
    )
    return inputs, provenance, release_record, output, verified, retention


def _known_cohorts() -> set[str]:
    from tools.a_meta.provenance import known_cohort_ids

    return known_cohort_ids()


def _is_locked(value: object) -> bool:
    from tools.a_meta.provenance import is_locked_study

    return is_locked_study(value)


def write_sc3_synthetic_manifest(
    clinical: pd.DataFrame,
    path: Path | str,
    *,
    input_sha256: Mapping[str, str] | None = None,
) -> dict:
    """Authenticate a synthetic clinical fixture using the A-META fixture format."""
    from tools.a_meta.provenance import write_synthetic_fixture_manifest

    cohorts = sorted(set(clinical.get("cohort", pd.Series(dtype=str)).astype(str)))
    manifest_path = Path(path).expanduser().absolute()
    _reject_sc3_symlinks(manifest_path)
    manifest = write_synthetic_fixture_manifest(
        manifest_path,
        kind="sc3_input",
        payload=_sc3_payload(clinical),
        cohort_ids=cohorts,
    )
    if manifest_path.exists() and manifest_path.is_symlink():
        raise ValueError("SC-3 synthetic provenance cannot be a symlink")
    if input_sha256 is not None:
        manifest["input_sha256"] = dict(input_sha256)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def write_sc3_r_synthetic_manifest(
    counts_path: Path | str,
    clinical_path: Path | str,
    path: Path | str,
) -> dict:
    """Write verified synthetic input provenance for the direct R analysis entry point."""
    from tools.a_meta.provenance import write_synthetic_fixture_manifest

    paths = {
        "counts": _existing_sc3_file(counts_path),
        "clinical": _existing_sc3_file(clinical_path),
    }
    if os.path.samefile(paths["counts"], paths["clinical"]):
        raise ValueError("SC-3 counts and clinical paths cannot alias the same file")
    manifest_path = Path(path).expanduser().absolute()
    _reject_sc3_symlinks(manifest_path)
    if not manifest_path.parent.is_dir() or manifest_path.exists():
        raise ValueError("SC-3 synthetic provenance output must be new in an existing directory")
    if any(manifest_path == source for source in paths.values()):
        raise ValueError("SC-3 synthetic provenance cannot alias its inputs")
    identity = _read_sc3_identity(paths["clinical"])
    cohorts = sorted(set(identity["cohort"].astype(str).str.strip()))
    _validate_sc3_identity(identity, set(cohorts))
    input_hashes = {
        "counts": _input_sha256(paths["counts"]),
        "clinical": _input_sha256(paths["clinical"]),
    }
    payload = (
        f"counts:{input_hashes['counts']}\nclinical:{input_hashes['clinical']}\n"
        f"cohorts:{','.join(cohorts)}\n"
    )
    manifest = write_synthetic_fixture_manifest(
        manifest_path,
        kind="sc3_r_input",
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        cohort_ids=cohorts,
    )
    manifest["input_sha256"] = input_hashes
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run_sc3_deseq2_synthetic(
    counts_path: Path | str,
    clinical_path: Path | str,
    provenance_path: Path | str,
    output_dir: Path | str,
    validated_groups: Sequence[Mapping],
    *,
    retention_dir: Path | str,
    runner=None,
):
    """Run the invented-only DESeq2 adapter after path and identity preflight."""
    from tools.a_meta.frozen import read_frozen_aliases
    from tools.r_bridge import run_r

    inputs, provenance, output, retention = _preflight_sc3_paths(
        {"counts": counts_path, "clinical": clinical_path},
        provenance_path,
        output_dir,
        retention_dir,
    )
    assert output is not None and retention is not None
    try:
        manifest = json.loads(provenance.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionError("SC-3 direct R provenance is missing or malformed") from error
    declared_cohorts = set(map(str, manifest.get("cohort_ids", ())))
    if (
        manifest.get("manifest_version") != 1
        or manifest.get("producer") != "tools.a_meta.synthetic_fixture"
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != "sc3_r_input"
        or declared_cohorts & (_real_sc_cohorts() | _known_cohorts())
        or any(_is_locked(value) for value in declared_cohorts)
    ):
        raise PermissionError("SC-3 direct R requires invented provenance with non-real cohort identities")

    identity = _read_sc3_identity(inputs["clinical"])
    _validate_sc3_identity(identity, declared_cohorts)
    hashes = {name: _input_sha256(path) for name, path in inputs.items()}
    if manifest.get("input_sha256") != hashes:
        raise PermissionError("SC-3 direct R provenance does not bind the counts and clinical inputs")
    payload = (
        f"counts:{hashes['counts']}\nclinical:{hashes['clinical']}\n"
        f"cohorts:{','.join(sorted(declared_cohorts))}\n"
    )
    if manifest.get("payload_sha256") != hashlib.sha256(payload.encode("utf-8")).hexdigest():
        raise PermissionError("SC-3 direct R provenance does not match the verified input hashes")

    with inputs["clinical"].open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream, delimiter="\t"), [])
    if not header or len(header) != len(set(header)) or set(header) - SC3_R_CLINICAL_COLUMNS:
        raise ValueError("SC-3 direct R clinical header contains unsupported or duplicate columns")
    required = {
        "profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment",
        "outcome_label", "eligible", "baseline", "treatment", "n_cells", "total_umis",
        "library_size", "sc3_group_id",
    }
    if not required.issubset(header) or not ("response_metric" in header or "endpoint_family" in header):
        raise ValueError("SC-3 direct R clinical input is missing required safe fields")

    root = Path(__file__).resolve().parents[2]
    script = root / "r/scripts/sc3_deseq2.R"
    return run_r(
        script,
        inputs,
        {
            "expected_outputs": ["de_results.tsv", "de_refusals.tsv"],
            "design": "~ response",
            "fdr": 0.10,
            "authorization": {
                "data_classification": "synthetic",
                "provenance_manifest": str(provenance),
            },
            "validated_groups": [dict(group) for group in validated_groups],
            "frozen_aliases": read_frozen_aliases(),
        },
        output,
        retention_dir=retention,
        runner=runner,
    )


def run_sc3_deseq2_released(
    expression_path: Path | str,
    clinical_path: Path | str,
    provenance_path: Path | str,
    release_record_path: Path | str | None,
    output_dir: Path | str,
    validated_groups: Sequence[Mapping],
    *,
    allow_outcomes: bool,
    retention_dir: Path | str,
    test_only_root: Path | str | None = None,
    test_registry_root: Path | str | None = None,
    runner=None,
):
    """Run the real-classified R adapter after independently rechecking its scoped release."""
    from tools.a_meta.frozen import read_frozen_aliases
    from tools.r_bridge import run_r

    inputs, provenance, release, output, verified, retention = preflight_sc3_release(
        {"clinical": clinical_path, "expression": expression_path},
        provenance_path,
        release_record_path,
        output_dir,
        allow_outcomes=allow_outcomes,
        retention_dir=retention_dir,
        test_only_root=test_only_root,
        test_registry_root=test_registry_root,
    )
    assert retention is not None
    root = Path(__file__).resolve().parents[2]
    script = root / "r/scripts/sc3_deseq2.R"
    authorization = {
        "data_classification": verified.classification,
        "allow_outcomes": True,
        "provenance_manifest": str(provenance),
        "release_record": str(release),
    }
    if verified.test_only_root is not None:
        authorization["test_only_root"] = str(verified.test_only_root)
        authorization["test_registry_root"] = str(verified.test_registry_root)
    return run_r(
        script,
        {"counts": inputs["expression"], "clinical": inputs["clinical"]},
        {
            "expected_outputs": ["de_results.tsv", "de_refusals.tsv"],
            "design": "~ response",
            "fdr": 0.10,
            "authorization": authorization,
            "validated_groups": [dict(group) for group in validated_groups],
            "frozen_aliases": read_frozen_aliases(),
        },
        output,
        retention_dir=retention,
        runner=runner,
    )


def _real_sc_cohorts() -> set[str]:
    cohort_map = Path(__file__).with_name("lin_cohort_map.tsv")
    frame = pd.read_csv(cohort_map, sep="\t", usecols=["cohort"], dtype=str)
    return set(frame["cohort"].astype(str)) | {"prostate_hormone_naive_atlas"}


def authorize_sc3(
    clinical: pd.DataFrame,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
    verified_release: _VerifiedSC3Release | None = None,
) -> None:
    """Require verified fixture provenance or a prior scoped-release proof."""
    if verified_release is not None:
        if verified_release.proof is not _SC3_RELEASE_TOKEN:
            raise PermissionError("SC-3 release authorization proof is invalid")
        cohorts = set(clinical.get("cohort", pd.Series(dtype=str)).dropna().astype(str).str.strip())
        if any(_is_locked(cohort) for cohort in cohorts):
            raise PermissionError("SC-3 refuses the locked IMvigor210 final test")
        if cohorts != set(verified_release.cohorts):
            raise PermissionError("SC-3 release cohort set differs from the verified clinical profiles")
        if provenance_manifest is None or Path(provenance_manifest).resolve(strict=False) != verified_release.manifest_path:
            raise PermissionError("SC-3 release provenance differs from the verified input manifest")
        if allow_outcomes is not True:
            raise PermissionError("SC-3 source-derived outcomes require explicit opt-in")
        return
    from tools.a_meta.provenance import (
        SYNTHETIC_FIXTURE_PRODUCER,
        canonical_sha256,
        is_locked_study,
        known_cohort_ids,
    )

    if allow_outcomes:
        raise PermissionError("SC-3 real-outcome execution is not released; invented synthetic data only")
    cohorts = set(clinical.get("cohort", pd.Series(dtype=str)).dropna().astype(str))
    if any(is_locked_study(cohort) for cohort in cohorts):
        raise PermissionError("SC-3 refuses the locked IMvigor210 final test")
    real_ids = cohorts & (_real_sc_cohorts() | known_cohort_ids())
    if real_ids:
        raise PermissionError("SC-3 synthetic fixtures cannot use a known real cohort")
    if provenance_manifest is None:
        raise PermissionError("SC-3 requires a verified synthetic manifest with invented cohort IDs")
    try:
        manifest_path = _existing_sc3_file(provenance_manifest)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionError("SC-3 synthetic provenance is missing or malformed") from error
    expected_cohorts = {cohort for cohort in cohorts if cohort}
    if (
        manifest.get("manifest_version") != 1
        or manifest.get("producer") != SYNTHETIC_FIXTURE_PRODUCER
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != "sc3_input"
        or set(map(str, manifest.get("cohort_ids", ()))) != expected_cohorts
        or manifest.get("payload_sha256") != canonical_sha256(_sc3_payload(clinical))
        or expected_cohorts & (known_cohort_ids() | _real_sc_cohorts())
    ):
        raise PermissionError("SC-3 synthetic manifest does not match the supplied clinical profiles")


def _truthy(values: pd.Series) -> pd.Series:
    if values.dtype == bool:
        return values
    return values.astype(str).str.strip().str.casefold().isin({"true", "1", "yes"})


def _is_baseline_ici(treatment: object) -> bool:
    drug_class = _drug_class(str(treatment))
    return drug_class in {"ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4"}


def group_profiles(
    clinical: pd.DataFrame,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
    verified_release: _VerifiedSC3Release | None = None,
) -> tuple[dict[tuple[str, str, str], SC3Group], list[dict]]:
    """Group validated patient profiles without mixing outcome metric families."""
    authorize_sc3(
        clinical,
        allow_outcomes=allow_outcomes,
        provenance_manifest=provenance_manifest,
        verified_release=verified_release,
    )
    required = {
        "cohort", "source_family", "profile_id", "patient_id", "sample_id", "compartment",
        "outcome_label", "eligible", "baseline", "n_cells", "total_umis", "library_size",
    }
    treatment_col = "treatment"
    required.add(treatment_col)
    if "endpoint_family" not in clinical and "response_metric" not in clinical:
        required.add("endpoint_family")
    missing = required - set(clinical.columns)
    if missing:
        raise ValueError(f"Clinical profiles are missing fields: {sorted(missing)}")
    frame = clinical.copy()
    for column in ("cohort", "source_family", "profile_id", "patient_id", "sample_id", "compartment"):
        frame[column] = frame[column].astype("string").fillna("").str.strip()
    if frame[["profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment"]].eq("").any().any():
        raise ValueError("SC-3 profiles require non-empty patient, specimen, cohort, and profile identities")
    sample_counts = frame.groupby(["cohort", "patient_id"], dropna=False)["sample_id"].nunique()
    if (sample_counts > 1).any():
        raise ValueError("Each SC-3 patient must have one baseline specimen per cohort")
    cohort_sources = frame.groupby("cohort", dropna=False)["source_family"].nunique()
    source_cohorts = frame.groupby("source_family", dropna=False)["cohort"].nunique()
    if (cohort_sources > 1).any() or (source_cohorts > 1).any():
        raise ValueError("SC-3 source-family metadata must map one cohort to one source family")
    identity_sources = frame.groupby(["patient_id", "sample_id"], dropna=False)[
        ["cohort", "source_family"]
    ].nunique()
    if (identity_sources > 1).any().any():
        raise ValueError("SC-3 stable patient/specimen identities occur in multiple source cohorts")
    if frame["profile_id"].duplicated().any():
        raise ValueError("SC-3 profile IDs must be unique")

    if "response_metric" in frame:
        mapped = frame["response_metric"].map(metric_family)
        metric_present = frame["response_metric"].notna() & frame["response_metric"].astype(str).str.strip().ne("")
        if "endpoint_family" in frame:
            declared = frame["endpoint_family"].map(metric_family)
            conflict = mapped.notna() & declared.notna() & mapped.ne(declared)
            if conflict.any():
                raise ValueError("SC-3 response metric and endpoint family disagree")
            unresolved = metric_present & mapped.isna()
            frame["endpoint_family"] = mapped.fillna(declared).mask(unresolved, None)
        else:
            frame["endpoint_family"] = mapped.mask(metric_present & mapped.isna(), None)
    else:
        frame["endpoint_family"] = frame["endpoint_family"].map(metric_family)
    if "response" in frame:
        expansion_rows = frame["endpoint_family"].eq("expansion")
        clinical_response = frame["response"].astype("string").fillna("").str.strip().str.upper()
        if (expansion_rows & clinical_response.isin({"R", "NR"})).any():
            raise ValueError("T-cell expansion labels cannot be stored as clinical response")
    frame["eligible"] = _truthy(frame["eligible"])
    frame["baseline"] = _truthy(frame["baseline"])
    frame["n_cells"] = pd.to_numeric(frame["n_cells"], errors="coerce")
    frame["total_umis"] = pd.to_numeric(frame["total_umis"], errors="coerce")
    frame["library_size"] = pd.to_numeric(frame["library_size"], errors="coerce")
    frame["_profile_floor"] = (
        frame["n_cells"].ge(15)
        & frame["total_umis"].ge(5_000)
        & frame["library_size"].gt(0)
    )
    frame["_baseline_ici"] = frame["baseline"] & frame[treatment_col].map(_is_baseline_ici)

    groups: dict[tuple[str, str, str], SC3Group] = {}
    refusals: list[dict] = []
    dimensions = ["cohort", "compartment", "endpoint_family"]
    for key, complete_frame in frame.groupby(dimensions, dropna=False, sort=True):
        cohort, compartment, family = map(str, key)
        if family in {"", "nan", "None"}:
            raw_metric = ",".join(sorted(set(complete_frame.get(
                "response_metric", complete_frame["endpoint_family"]
            ).astype(str))))
            refusals.append({
                "cohort": cohort, "compartment": compartment, "endpoint_family": "unusable",
                "response_metric": raw_metric, "n_R": 0, "n_NR": 0,
                "reason": "metric_compatibility_requires_decision",
            })
            continue
        if complete_frame["patient_id"].duplicated().any():
            raise ValueError("SC-3 requires one pseudobulk profile per patient and compartment/metric")
        if complete_frame["sample_id"].duplicated().any():
            raise ValueError("An SC-3 specimen cannot belong to more than one patient profile")
        valid = complete_frame[
            complete_frame["eligible"]
            & complete_frame["_baseline_ici"]
            & complete_frame["_profile_floor"]
            & complete_frame["outcome_label"].isin(["R", "NR"])
        ].copy()
        n_r = int(valid.loc[valid["outcome_label"].eq("R"), "patient_id"].nunique())
        n_nr = int(valid.loc[valid["outcome_label"].eq("NR"), "patient_id"].nunique())
        if n_r < 3 or n_nr < 3:
            refusals.append({"cohort": cohort, "compartment": compartment, "endpoint_family": family,
                             "n_R": n_r, "n_NR": n_nr, "reason": "fewer_than_three_patients_per_arm"})
            continue
        groups[(cohort, compartment, family)] = SC3Group(
            cohort=cohort,
            source_family=str(valid["source_family"].iloc[0]),
            compartment=compartment,
            endpoint_family=family,
            profile_ids=tuple(valid["profile_id"].astype(str)),
            n_r=n_r,
            n_nr=n_nr,
        )
    return groups, refusals


def validated_group_manifest(
    clinical: pd.DataFrame,
    groups: Mapping,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
    verified_release: _VerifiedSC3Release | None = None,
) -> list[dict]:
    import hashlib

    authorize_sc3(
        clinical, allow_outcomes=allow_outcomes, provenance_manifest=provenance_manifest,
        verified_release=verified_release,
    )
    by_profile = clinical.set_index(clinical["profile_id"].astype(str), drop=False)
    result = []
    for group_id, group in enumerate(groups.values(), start=1):
        profiles = list(group.profile_ids)
        frame = by_profile.loc[profiles]
        profile_hash = hashlib.sha256("\n".join(sorted(profiles)).encode("utf-8")).hexdigest()
        result.append({
            "group_id": f"sc3_group_{group_id}",
            "cohort": group.cohort,
            "source_family": group.source_family,
            "compartment": group.compartment,
            "endpoint_family": group.endpoint_family,
            "n_R": group.n_r,
            "n_NR": group.n_nr,
            "profile_ids_sha256": profile_hash,
            "profile_count": len(profiles),
        })
    return result


def _drug_class(treatment: str) -> str:
    from tools.a_cohorts.view import normalise_drug_class

    value = re.sub(r"\baPD\s*-?1\b", "anti-PD1", str(treatment), flags=re.IGNORECASE)
    value = re.sub(r"\baPD\s*-?L1\b", "anti-PD-L1", value, flags=re.IGNORECASE)
    value = re.sub(r"\baCTLA\s*-?4\b", "anti-CTLA4", value, flags=re.IGNORECASE)
    value = re.sub(r"(?<!anti-)\bCTLA\s*-?4\b", "anti-CTLA4", value, flags=re.IGNORECASE)
    try:
        return str(normalise_drug_class(value))
    except ValueError:
        return "UNMAPPED"


def _sc3_effects(
    clinical: pd.DataFrame,
    expression: pd.DataFrame,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
    verified_release: _VerifiedSC3Release | None = None,
) -> pd.DataFrame:
    from types import SimpleNamespace

    from tools.a_meta.effects import EFFECT_COLUMNS, _effect_row
    from .presentation import SC1_PANEL_IDS, _apply_frozen_gene_aliases, panel_definitions_for_sc1

    if "cancer" not in clinical.columns:
        raise ValueError("SC-3 effects require declared cancer metadata for A-META synthesis")

    groups, _ = group_profiles(
        clinical,
        allow_outcomes=allow_outcomes,
        provenance_manifest=provenance_manifest,
        verified_release=verified_release,
    )
    definitions = panel_definitions_for_sc1()
    extras = ("compartment", "sc_endpoint_family", "response_metric", "source_family")
    records: list[dict] = []
    expression = _apply_frozen_gene_aliases(expression)
    expression.index = expression.index.astype(str)
    expression.columns = expression.columns.astype(str)
    if expression.index.duplicated().any() or expression.columns.duplicated().any():
        raise ValueError("SC-3 expression gene and profile identities must be unique")
    clinical_index = clinical.copy()
    clinical_index["profile_id"] = clinical_index["profile_id"].astype(str)
    by_profile = clinical_index.set_index("profile_id", drop=False)

    for group in groups.values():
        ids = list(group.profile_ids)
        frame = by_profile.loc[ids].copy().reset_index(drop=True)
        if not set(ids).issubset(expression.columns):
            raise ValueError("SC-3 expression columns do not cover the validated patient groups")
        raw = expression.loc[:, ids].apply(pd.to_numeric, errors="raise")
        measured = raw.to_numpy(dtype=float)
        observed = measured[~pd.isna(measured)]
        if any(not math.isfinite(value) or value < 0 or value != math.floor(value) for value in observed):
            raise ValueError("SC-3 expression profiles must contain non-negative integer UMI sums")
        library_sizes = pd.to_numeric(frame["library_size"], errors="coerce")
        if library_sizes.isna().any() or (library_sizes <= 0).any():
            raise ValueError("SC-3 profiles require positive full-library sizes")
        normalized = np_log2_plus1(raw.divide(library_sizes.to_numpy(), axis=1) * 1_000_000.0)
        labels = [1 if value == "R" else 0 if value == "NR" else None for value in frame["outcome_label"]]
        treatment_col = "treatment" if "treatment" in frame else "drug_class"
        frame["_sc3_drug_class"] = frame[treatment_col].astype(str).map(_drug_class)
        valid_classes = {"ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4"}
        included = [index for index, value in enumerate(frame["_sc3_drug_class"]) if value in valid_classes]
        strata = [("ALL", included)]
        strata.extend(
            (drug_class, [index for index in included if frame.loc[index, "_sc3_drug_class"] == drug_class])
            for drug_class in sorted({frame.loc[index, "_sc3_drug_class"] for index in included})
        )
        cancers = sorted(set(frame.get("cancer", pd.Series("unknown", index=frame.index)).astype(str)))
        cancer = cancers[0] if len(cancers) == 1 else "multi"
        metric_values = sorted(set(frame.get("response_metric", pd.Series(group.endpoint_family, index=frame.index)).astype(str)))
        metric_label = ",".join(metric_values)
        endpoint_family, endpoint_definition_id = SC_ENDPOINT_MAPPINGS[group.endpoint_family]
        view = SimpleNamespace(metadata=SimpleNamespace(cohort_id=group.cohort))
        clinical_rows = [
            {"patient_id": str(row.patient_id), "sample_id": str(row.sample_id)}
            for row in frame.itertuples(index=False)
        ]

        def add_effect(unit_family, unit, values, *, coverage=None, method_id="", m5m6_gene_flag=False):
            for stratum, indices in strata:
                row = _effect_row(
                    view=view,
                    unit_family=unit_family,
                    unit=f"sc3::{group.compartment}::{group.endpoint_family}::{unit}",
                    cancer=cancer,
                    stratum=stratum,
                    endpoint_family=endpoint_family,
                    endpoint_definition_id=endpoint_definition_id,
                    labels=labels,
                    values=values,
                    patient_indices=indices,
                    excluded={},
                    coverage=coverage,
                    clinical_rows=clinical_rows,
                    cancer_components=cancers,
                    method_id=method_id,
                    m5m6_gene_flag=m5m6_gene_flag,
                )
                if int(row["n_R"]) < 3 or int(row["n_NR"]) < 3:
                    row["g"] = None
                    row["se"] = None
                    row["status"] = "NA"
                    floor_reasons = []
                    if int(row["n_R"]) < 3:
                        floor_reasons.append("n_R<3")
                    if int(row["n_NR"]) < 3:
                        floor_reasons.append("n_NR<3")
                    row["reason"] = ";".join(filter(None, [str(row["reason"]), *floor_reasons]))
                patient_tokens = sorted(
                    f"{clinical_rows[index]['patient_id']}\x1f{clinical_rows[index]['sample_id']}"
                    for index in indices
                    if labels[index] in (0, 1) and values[index] is not None
                )
                row["patient_set_id"] = hashlib.sha256("\x1e".join(patient_tokens).encode("utf-8")).hexdigest()
                row.update({
                    "compartment": group.compartment,
                    "sc_endpoint_family": group.endpoint_family,
                    "response_metric": metric_label,
                    "source_family": group.source_family,
                })
                records.append(row)

        for panel_id in SC1_PANEL_IDS:
            members = definitions[panel_id]
            present = [gene for gene in members if gene in normalized.index]
            required_members = math.ceil(0.8 * len(members))
            coverage_complete = bool(members) and len(present) >= required_members
            values = [None] * len(ids)
            if coverage_complete:
                for index, profile_id in enumerate(ids):
                    measured = normalized.loc[present, profile_id].dropna()
                    if len(measured) >= required_members:
                        values[index] = float(measured.mean())
            add_effect(
                "panel", panel_id, values,
                coverage={"complete": coverage_complete, "n_found": len(present), "n_total": len(members)},
                method_id=f"CUSTOM_MEAN_{panel_id}",
            )

        for panel_id in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS"):
            for gene in definitions[panel_id]:
                values = [
                    float(normalized.at[gene, profile_id]) if gene in normalized.index and pd.notna(normalized.at[gene, profile_id]) else None
                    for profile_id in ids
                ]
                add_effect("m5m6_gene", gene, values, method_id="GENE_STUDY_SCALE", m5m6_gene_flag=True)

        if "fraction_cells_total" in frame:
            values = [
                float(value) if pd.notna(value) else None
                for value in pd.to_numeric(frame["fraction_cells_total"], errors="coerce")
            ]
            add_effect("fraction", "compartment_fraction", values)

    columns = [*EFFECT_COLUMNS, *extras]
    return pd.DataFrame.from_records(records, columns=columns)


def np_log2_plus1(frame: pd.DataFrame) -> pd.DataFrame:
    import numpy as np

    return np.log2(frame + 1.0)
