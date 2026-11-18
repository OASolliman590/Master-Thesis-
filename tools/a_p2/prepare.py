"""Prepare hash-bound, outcome-gated A-P2 development inputs."""

from __future__ import annotations

import csv
import gzip
import hashlib
import itertools
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import product
from tools.a_scoring import ALIAS_TABLE_PATH, PANEL_REGISTRY_PATH


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_DIR = ROOT / "docs/validation/A_P2_IDENTITY"
DEFAULT_SCRATCH_ROOT = ROOT / ".scratch" / "runtime"
MANIFEST_NAME = "a_p2_input_manifest.json"
SIDECAR_NAME = "identity_sidecar.json"
SOURCE_MANIFEST_NAME = "manifest.json"
SOURCE_REGISTRY_NAME = "SOURCE_REGISTRY.tsv"
FAMILY_REGISTRY_NAME = "PUBLICATION_FAMILY_REGISTRY.tsv"
OVERLAP_REGISTRY_NAME = "OVERLAP_REGISTRY.tsv"
REGISTRY_IDENTITY = "A_P2_IDENTITY_20261114"
PROPOSED_DECISION_ID = "A_P2_DEVELOPMENT_RELEASE_PROPOSED_2026-11-14"
REAL_CLASSIFICATION = "PRIVATE_PATIENT_LEVEL"
DEVELOPMENT_ROLE = "development"
UNRESOLVED = "UNRESOLVED"
A1_RULE_ID = "A_P2_ATEZO_FREEZE_EXCLUSION_V1"
A1_EXCLUSIONS_NAME = "a_p2_atezo_freeze_exclusions.json"
FREEZE_TABLE_NAME = "a_p2_freeze_features.tsv"
FREEZE_MANIFEST_NAME = "a_p2_input_manifest_freeze.json"
FREEZE_SIDECAR_NAME = "identity_sidecar_freeze.json"
SENSITIVITY_MANIFEST_NAME = "a_p2_input_manifest_development_sensitivity.json"
SENSITIVITY_SIDECAR_NAME = "identity_sidecar_development_sensitivity.json"
CONSERVATIVE_RELEASE_NAME = "release_development_conservative_sensitivity.unapproved.json"
SENSITIVITY_RELEASE_NAME = "release_development_sensitivity.unapproved.json"
FREEZE_RELEASE_NAME = "release_freeze.unapproved.json"
OVERLAP_STATUSES = {
    "NO_OVERLAP_DOCUMENTED",
    "OVERLAP_RISK_GROUPED",
    "CONSERVATIVE_SENSITIVITY",
    "NOT_APPLICABLE_TO_A_P2",
    "RESOLVED_BY_SOURCE_RULE",
    UNRESOLVED,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FEATURE_HEADER = (
    "cohort",
    "patient_id",
    "cancer",
    "orr_raw",
    "orr_class",
    "P_ANTIGEN_PRESENTATION",
    "M2_CYTOTOXICITY",
    "M3_VIRAL_MIMICRY",
    "M4_EXCLUSION",
    "CYT",
    "tpm_route",
)
_REQUIRED_PRIMARY = {
    "liu2019",
    "riaz_gse91061",
    "hugo_gse78220",
    "vanallen2015",
    "kim2018",
    "gide2019",
    "gse176307",
}
_REQUIRED_OVERLAPS = {
    tuple(sorted(pair)) for pair in itertools.combinations(sorted(_REQUIRED_PRIMARY), 2)
} | {tuple(sorted((cohort, "imvigor210"))) for cohort in _REQUIRED_PRIMARY}
_CONSERVATIVE_FAMILY_COHORTS = {
    "liu2019", "vanallen2015", "riaz_gse91061", "hugo_gse78220"
}
_CONSERVATIVE_FAMILY = "a_p2_melanoma_conservative_sensitivity"
_GSE176307_SOFT_SHA256 = "ea242fbb98aa104c384a97a3d1f0baaa938031e91a5a3872b065982d73b1bf72"
_MAIN_FEATURES_SHA256 = "75b3b1b04653d605a6bde1027bc8050cf3ff363e93fbd0fa5b2f72813d81726a"
_HISTORICAL_BUILD_RECEIPT_SHA256 = "16365f3783661488aec82fb40d70b5eae97614da0f84b6b0961bf287ff86a376"
_MISSING_THERAPY_VALUES = {"", "na", "n/a", "nan", "none", "null", "unknown", "not available", "not reported"}
_BUILD_FILE_IDENTITY = "tools/a_p2/build.py"
_GSE176307_FIELD_MAP_IDENTITY = "tools/a_dav/field_maps/gse176307.json"
_PANEL_REGISTRY_IDENTITY = "specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json"
_ALIAS_TABLE_IDENTITY = "specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv"
CONSERVATIVE_MANIFEST_NAME = "a_p2_input_manifest_conservative_sensitivity.json"
CONSERVATIVE_SIDECAR_NAME = "identity_sidecar_conservative_sensitivity.json"


class PreparationError(ValueError):
    """An A-P2 preparation input or evidence registry is invalid."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _protected_path(path: Path, label: str) -> Path:
    try:
        return product._guard_external_path(path, label)
    except PermissionError as error:
        raise PreparationError(str(error)) from error


def _prepare_paths(
    inputs_dir: Path,
    out_dir: Path,
    check_only: bool,
    scratch_root: Path,
) -> tuple[Path, Path, Path, Path]:
    guarded_inputs = _protected_path(inputs_dir, "preparation input directory")
    if any(
        product._identity_tokens(part) & product._PROTECTED_IDENTITY_TOKENS
        for part in guarded_inputs.parts
    ):
        raise PreparationError("A-P2 protected input identity was refused before reading")
    if not guarded_inputs.is_dir():
        raise PreparationError("A-P2 built input directory is unavailable")
    features_path = _protected_path(guarded_inputs / "features.tsv", "preparation feature table")
    source_manifest_path = _protected_path(
        guarded_inputs / SOURCE_MANIFEST_NAME, "built input manifest"
    )

    guarded_scratch = _protected_path(scratch_root, "private scratch directory")
    guarded_out = _protected_path(out_dir, "preparation output directory")
    if not guarded_out.is_relative_to(guarded_scratch):
        raise PreparationError("A-P2 preparation output must be under the private .scratch/runtime directory")
    if guarded_out == guarded_scratch:
        raise PreparationError("A-P2 preparation output must use a fresh private subdirectory")
    if check_only:
        if not guarded_out.is_dir():
            raise PreparationError("--check-only requires an existing prepared output directory")
    elif guarded_out.exists():
        raise FileExistsError("A-P2 preparation output directory must be fresh")
    return guarded_inputs, guarded_out, features_path, source_manifest_path


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreparationError(f"Cannot read {label}") from error
    if not isinstance(value, dict):
        raise PreparationError(f"{label} must be a JSON object")
    return value, raw


def _read_tsv(
    path: Path,
    required_headers: set[str],
    label: str,
    *,
    optional_values: set[str] | None = None,
) -> tuple[list[dict[str, str]], bytes]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise PreparationError(f"Cannot read {label}") from error
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or not required_headers <= set(headers):
        raise PreparationError(f"{label} has an invalid header")
    rows = list(reader)
    required_values = required_headers - (optional_values or set())
    if not rows or any(any(not row.get(key) for key in required_values) for row in rows):
        raise PreparationError(f"{label} contains an incomplete row")
    return rows, raw


def _boolean(value: str, label: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise PreparationError(f"{label} must be true or false")


def _load_registries(registry_dir: Path) -> dict[str, Any]:
    source_rows, source_bytes = _read_tsv(
        _protected_path(registry_dir / SOURCE_REGISTRY_NAME, "source identity registry"),
        {
            "cohort_id",
            "study_family",
            "cancer",
            "accession",
            "primary_publication",
            "expression_file_identity",
            "expression_sha256",
            "representation",
            "feature_transform",
            "primary_eligible",
            "adaptive_eligible",
            "cyt_available",
        },
        "source identity registry",
    )
    family_rows, family_bytes = _read_tsv(
        _protected_path(registry_dir / FAMILY_REGISTRY_NAME, "publication-family registry"),
        {"cohort_id", "study_family_id", "publication_group_id", "status", "evidence"},
        "publication-family registry",
    )
    overlap_rows, overlap_bytes = _read_tsv(
        _protected_path(registry_dir / OVERLAP_REGISTRY_NAME, "overlap registry"),
        {
            "cohort_a",
            "cohort_b",
            "primary_source_evidence",
            "identity_comparison",
            "status",
            "rule_id",
            "resolution_rule",
        },
        "overlap registry",
        optional_values={"rule_id"},
    )

    sources: dict[str, dict[str, Any]] = {}
    for row in source_rows:
        cohort = row["cohort_id"]
        if cohort in sources:
            raise PreparationError("Source registry repeats a cohort")
        if not _SHA256.fullmatch(row["expression_sha256"]):
            raise PreparationError("Source registry contains an invalid expression hash")
        transform = row["feature_transform"]
        if transform not in product._ALLOWED_FEATURE_TRANSFORMS:
            raise PreparationError(f"Source registry has an unsupported transform: {cohort}")
        sources[cohort] = {
            **row,
            "primary_eligible": _boolean(row["primary_eligible"], "primary_eligible"),
            "adaptive_eligible": _boolean(row["adaptive_eligible"], "adaptive_eligible"),
            "cyt_available": _boolean(row["cyt_available"], "cyt_available"),
        }

    if set(sources) != _REQUIRED_PRIMARY | {"braun2020"}:
        raise PreparationError("Source registry must contain the seven primary families and Braun")
    if {name for name, row in sources.items() if row["primary_eligible"]} != _REQUIRED_PRIMARY:
        raise PreparationError("Source registry primary eligibility differs from signed A-P2 scope")
    if {name for name, row in sources.items() if row["adaptive_eligible"]} != set(sources):
        raise PreparationError("Every registered A-P2 source must declare adaptive eligibility")

    family_by_cohort: dict[str, dict[str, str]] = {}
    for row in family_rows:
        cohort = row["cohort_id"]
        if cohort in family_by_cohort or cohort not in sources:
            raise PreparationError("Publication-family registry has a duplicate or unknown cohort")
        if row["study_family_id"] != sources[cohort]["study_family"]:
            raise PreparationError("Publication-family study identity conflicts with the source registry")
        family_by_cohort[cohort] = row
    if set(family_by_cohort) != set(sources):
        raise PreparationError("Publication-family registry does not cover every source cohort")

    overlaps: dict[tuple[str, str], dict[str, str]] = {}
    for row in overlap_rows:
        pair = tuple(sorted((row["cohort_a"], row["cohort_b"])))
        if pair[0] == pair[1] or pair in overlaps:
            raise PreparationError("Overlap registry has a duplicate or self-pair")
        if row["status"] not in OVERLAP_STATUSES:
            raise PreparationError("Overlap registry has an unsupported status")
        if row["status"] == "RESOLVED_BY_SOURCE_RULE" and not row["rule_id"].strip():
            raise PreparationError("RESOLVED_BY_SOURCE_RULE requires a rule_id")
        overlaps[pair] = row
    missing_pairs = sorted(_REQUIRED_OVERLAPS - overlaps.keys())
    if missing_pairs:
        formatted = ", ".join("/".join(pair) for pair in missing_pairs)
        raise PreparationError(
            "Overlap registry is missing a required development pair: " + formatted
        )

    return {
        "sources": sources,
        "families": family_by_cohort,
        "overlaps": overlaps,
        "hashes": {
            "source_registry_sha256": _sha256_bytes(source_bytes),
            "publication_family_registry_sha256": _sha256_bytes(family_bytes),
            "overlap_registry_sha256": _sha256_bytes(overlap_bytes),
        },
    }


def _read_header(stream) -> bytes:
    raw = stream.readline()
    header_line = raw.rstrip(b"\r\n")
    try:
        headers = header_line.decode("utf-8").split("\t")
    except UnicodeDecodeError as error:
        raise PreparationError("A-P2 feature table header is not UTF-8") from error
    if headers != list(_FEATURE_HEADER) or len(headers) != len(set(headers)):
        raise PreparationError("A-P2 built input is not the expected A-P2 feature table")
    if headers.index("cohort") != 0 or headers.index("patient_id") != 1:
        raise PreparationError("A-P2 identity columns must lead the feature table")
    return raw


def _read_framed_identity_line(stream, line_number: int, allowed: set[str]) -> tuple[str, str, bytes] | None:
    """Read the cohort token first, then validate framing without decoding the suffix."""
    cohort_buffer = bytearray()
    while True:
        byte = stream.read(1)
        if not byte:
            if not cohort_buffer:
                return None
            raise PreparationError(f"A-P2 identity row {line_number} has no patient_id field")
        if byte == b"\t":
            break
        if byte in (b"\n", b"\r"):
            raise PreparationError(f"A-P2 identity row {line_number} has no patient_id field")
        cohort_buffer.extend(byte)
    cohort_bytes = bytes(cohort_buffer)
    try:
        cohort = cohort_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PreparationError(f"A-P2 cohort identity row {line_number} is not UTF-8") from error

    # The source boundary is checked before reading, counting, or decoding any suffix byte.
    if product._identity_tokens(cohort) & product._PROTECTED_IDENTITY_TOKENS:
        raise PreparationError("A-P2 protected cohort identity was refused before reading patient IDs")
    if cohort not in allowed:
        raise PreparationError("A-P2 input contains an undeclared or protected cohort identity")

    suffix = stream.readline()
    raw_line = cohort_bytes + b"\t" + suffix
    if b'"' in raw_line or raw_line.count(b"\t") != len(_FEATURE_HEADER) - 1:
        raise PreparationError(
            f"A-P2 identity row {line_number} is quoted or incorrectly framed"
        )
    patient_end = suffix.find(b"\t")
    if patient_end < 0:
        raise PreparationError(f"A-P2 identity row {line_number} has no complete patient_id field")
    try:
        patient_id = suffix[:patient_end].decode("utf-8")
    except UnicodeDecodeError as error:
        raise PreparationError(f"A-P2 patient identity row {line_number} is not UTF-8") from error
    if not patient_id or not patient_id.strip():
        raise PreparationError("A-P2 identity row is incomplete or undeclared")
    return cohort, patient_id, raw_line


def _read_identity_rows(features_path: Path, allowed: set[str]) -> list[dict[str, str]]:
    """Read the two leading identities; later fields remain opaque bytes."""
    records: list[dict[str, str]] = []
    seen_rows: set[tuple[str, str]] = set()
    seen_canonical: set[str] = set()
    try:
        with features_path.open("rb") as stream:
            _read_header(stream)
            for line_number in itertools.count(2):
                identity_line = _read_framed_identity_line(stream, line_number, allowed)
                if identity_line is None:
                    break
                cohort, patient_id, _ = identity_line
                key = (cohort, patient_id)
                if key in seen_rows:
                    raise PreparationError("A-P2 duplicate canonical identity within a cohort")
                canonical_uid = f"a_p2:{cohort}:{_sha256_bytes(patient_id.encode('utf-8'))}"
                if canonical_uid in seen_canonical:
                    raise PreparationError("A-P2 duplicate canonical identity within or across cohorts")
                seen_rows.add(key)
                seen_canonical.add(canonical_uid)
                records.append(
                    {
                        "cohort": cohort,
                        "patient_id": patient_id,
                        "canonical_patient_uid": canonical_uid,
                    }
                )
    except PreparationError:
        raise
    except OSError as error:
        raise PreparationError("Cannot read only the A-P2 identity columns") from error
    if not records:
        raise PreparationError("A-P2 input contains no identity rows")
    return sorted(records, key=lambda record: (record["cohort"], record["patient_id"]))


def _input_cohorts(identities: list[dict[str, str]]) -> set[str]:
    return {record["cohort"] for record in identities}


def _cohort_metadata(
    sources: dict[str, dict[str, Any]], cohort_ids: set[str]
) -> dict[str, dict[str, Any]]:
    return {
        cohort: {
            "study_family": source["study_family"],
            "cancer": source["cancer"],
            "representation": source["representation"],
            "feature_transform": source["feature_transform"],
            "primary_eligible": source["primary_eligible"],
            "adaptive_eligible": source["adaptive_eligible"],
            "cyt_available": source["cyt_available"],
        }
        for cohort, source in sorted(sources.items())
        if cohort in cohort_ids
    }


def _valid_hash_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value or any(
        not isinstance(key, str) or not isinstance(digest, str) or not _SHA256.fullmatch(digest)
        for key, digest in value.items()
    ):
        raise PreparationError(f"Built input manifest has an invalid {label} hash map")
    return dict(sorted(value.items()))


@lru_cache(maxsize=8)
def _historical_builder_commit(builder_hash: str) -> str:
    try:
        commits = subprocess.run(
            ["git", "rev-list", "--all", "--", _BUILD_FILE_IDENTITY],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=30,
        ).stdout.decode("ascii").splitlines()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as error:
        raise PreparationError("Cannot verify the historical A-P2 builder object") from error
    for commit in commits:
        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{_BUILD_FILE_IDENTITY}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if _sha256_bytes(result.stdout) == builder_hash:
            return commit
    raise PreparationError(
        "Built input manifest builder hash has no matching reachable historical git object"
    )


def _build_lineage(
    source_manifest: dict[str, Any], input_cohorts: set[str], registries: dict[str, Any]
) -> dict[str, Any]:
    """Bind the selected input to the exact receipt, code, mapping and membership lineage."""
    receipt_inputs = _valid_hash_map(source_manifest.get("input_sha256"), "source")
    receipt_code = _valid_hash_map(source_manifest.get("code_sha256"), "builder-code")
    receipt_outputs = _valid_hash_map(source_manifest.get("output_sha256"), "builder-output")
    if "features.tsv" not in receipt_outputs:
        raise PreparationError("Built input manifest does not bind features.tsv")

    builder_path = ROOT / _BUILD_FILE_IDENTITY
    builder_hash = receipt_code.get(_BUILD_FILE_IDENTITY)
    if builder_hash is None or not builder_path.is_file():
        raise PreparationError("Built input manifest is missing its A-P2 builder identity")
    builder_commit = _historical_builder_commit(builder_hash)

    panel_path = ROOT / _PANEL_REGISTRY_IDENTITY
    alias_path = ROOT / _ALIAS_TABLE_IDENTITY
    field_map_path = ROOT / _GSE176307_FIELD_MAP_IDENTITY
    if Path(PANEL_REGISTRY_PATH).resolve() != panel_path.resolve():
        raise PreparationError("A-P2 builder panel registry path identity changed")
    if Path(ALIAS_TABLE_PATH).resolve() != alias_path.resolve():
        raise PreparationError("A-P2 builder alias-table path identity changed")
    panel_hash = _sha256_file(panel_path)
    alias_hash = _sha256_file(alias_path)
    if receipt_inputs.get(_PANEL_REGISTRY_IDENTITY) != panel_hash:
        raise PreparationError("Built input source hashes do not match the frozen panel registry identity")
    if receipt_inputs.get(_ALIAS_TABLE_IDENTITY) != alias_hash:
        raise PreparationError("Built input source hashes do not match the frozen alias-table identity")
    field_map_hash = _sha256_file(field_map_path)
    if receipt_inputs.get(_GSE176307_FIELD_MAP_IDENTITY) != field_map_hash:
        raise PreparationError("Built input source hashes do not match the GSE176307 field-map identity")
    try:
        field_map = json.loads(field_map_path.read_bytes())
        pinned_soft_hash = field_map["source_objects"]["geo_family_soft"]["sha256"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise PreparationError("The patient-free GSE176307 field map is invalid") from error

    feature_memberships = {
        name: definition["membership_sha256"]
        for name, definition in product._feature_definitions().items()
    }
    selected_expression_hashes = {
        cohort: registries["sources"][cohort]["expression_sha256"]
        for cohort in sorted(input_cohorts)
    }
    receipt_source_values = set(receipt_inputs.values())
    missing_selected_sources = sorted(
        cohort for cohort, digest in selected_expression_hashes.items()
        if digest not in receipt_source_values
    )
    if missing_selected_sources:
        raise PreparationError(
            "Selected expression lineage is absent from the build receipt for: "
            + ", ".join(missing_selected_sources)
        )

    if panel_path.resolve().relative_to(ROOT.resolve()).as_posix() != _PANEL_REGISTRY_IDENTITY:
        raise PreparationError("Frozen panel registry path identity changed")
    if alias_path.resolve().relative_to(ROOT.resolve()).as_posix() != _ALIAS_TABLE_IDENTITY:
        raise PreparationError("Frozen alias-table path identity changed")

    return {
        "receipt_input_sha256": receipt_inputs,
        "receipt_code_sha256": receipt_code,
        "receipt_output_sha256": receipt_outputs,
        "builder_identity": {
            "path": _BUILD_FILE_IDENTITY,
            "sha256": builder_hash,
            "reachable_commit": builder_commit,
        },
        "panel_registry_identity": {"path": _PANEL_REGISTRY_IDENTITY, "sha256": panel_hash},
        "alias_table_identity": {"path": _ALIAS_TABLE_IDENTITY, "sha256": alias_hash},
        "gse176307_field_map_identity": {
            "path": _GSE176307_FIELD_MAP_IDENTITY,
            "sha256": field_map_hash,
            "pinned_soft_sha256": pinned_soft_hash,
        },
        "feature_membership_sha256": feature_memberships,
        "selected_expression_sha256": selected_expression_hashes,
    }


def _is_protected_final(cohort: str) -> bool:
    return bool(product._identity_tokens(cohort) & product._PROTECTED_IDENTITY_TOKENS)


def _resolve_gse_soft_path(inputs_dir: Path, explicit_path: Path | None) -> tuple[Path, str]:
    field_map_path = _protected_path(ROOT / _GSE176307_FIELD_MAP_IDENTITY, "GSE176307 field map")
    try:
        field_map = json.loads(field_map_path.read_bytes())
        expected_hash = field_map["source_objects"]["geo_family_soft"]["sha256"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise PreparationError("The patient-free GSE176307 field map is invalid") from error
    if expected_hash != _GSE176307_SOFT_SHA256:
        raise PreparationError("The pinned GSE176307 SOFT hash differs from its field-map identity")
    pinned_path = inputs_dir.resolve().parent.parent / "gse176307/store/objects" / expected_hash
    candidate = Path(explicit_path) if explicit_path is not None else pinned_path
    guarded = _protected_path(candidate, "pinned GSE176307 family SOFT")
    if not guarded.is_file():
        raise PreparationError("The pinned GSE176307 family SOFT object is unavailable")
    digest = _sha256_file(guarded)
    if digest != expected_hash:
        raise PreparationError("The GSE176307 family SOFT hash differs from its pinned field-map identity")
    return guarded, digest


def _read_gse176307_patient_therapies(soft_path: Path) -> dict[str, dict[str, Any]]:
    """Read only the title, GEO accession, and io.therapy values from pinned SOFT."""
    patients: dict[str, dict[str, Any]] = {}
    sample_title: str | None = None
    sample_accession: str | None = None
    sample_therapies: list[str] = []
    sample_has_therapy = False
    samples_seen: set[str] = set()

    def finish_sample() -> None:
        nonlocal sample_title, sample_accession, sample_therapies, sample_has_therapy
        if sample_title is None and sample_accession is None:
            return
        if not sample_title or not sample_accession or sample_accession in samples_seen:
            raise PreparationError("GSE176307 SOFT has incomplete or duplicate named sample identity fields")
        samples_seen.add(sample_accession)
        pieces = sample_title.split()
        if not pieces:
            raise PreparationError("GSE176307 SOFT sample title has no source patient token")
        source_patient_id = pieces[-1]
        patient_token = (
            "STUDY:gse176307:PATIENT:"
            + hashlib.sha256(source_patient_id.encode("utf-8")).hexdigest()
        )
        entry = patients.setdefault(
            patient_token,
            {"therapy_values": set(), "has_missing_therapy": False, "has_atezolizumab": False},
        )
        missing_values = [
            value for value in sample_therapies
            if value.strip().casefold() in _MISSING_THERAPY_VALUES
        ]
        values = {
            value.strip() for value in sample_therapies
            if value.strip().casefold() not in _MISSING_THERAPY_VALUES
        }
        if not sample_has_therapy or not values or missing_values:
            entry["has_missing_therapy"] = True
        if len(values) > 1:
            entry["has_conflicting_therapy"] = True
        entry["therapy_values"].update(values)
        if any(value.casefold() == "atezolizumab" for value in values):
            entry["has_atezolizumab"] = True
        if len(entry["therapy_values"]) > 1:
            entry["has_conflicting_therapy"] = True
        sample_title = None
        sample_accession = None
        sample_therapies = []
        sample_has_therapy = False

    title_prefix = b"!Sample_title ="
    accession_prefix = b"!Sample_geo_accession ="
    characteristics_prefix = b"!Sample_characteristics_ch1 ="
    try:
        with gzip.open(soft_path, "rb") as stream:
            for raw_line in stream:
                line = raw_line.rstrip(b"\r\n")
                if line.startswith(b"^SAMPLE ="):
                    finish_sample()
                    continue
                if line.startswith(title_prefix):
                    if sample_title is not None:
                        raise PreparationError("GSE176307 SOFT repeats !Sample_title within one sample")
                    try:
                        sample_title = line[len(title_prefix):].strip().decode("utf-8")
                    except UnicodeDecodeError as error:
                        raise PreparationError("GSE176307 SOFT title is not UTF-8") from error
                elif line.startswith(accession_prefix):
                    if sample_accession is not None:
                        raise PreparationError("GSE176307 SOFT repeats !Sample_geo_accession within one sample")
                    try:
                        sample_accession = line[len(accession_prefix):].strip().decode("utf-8")
                    except UnicodeDecodeError as error:
                        raise PreparationError("GSE176307 SOFT accession is not UTF-8") from error
                elif line.startswith(characteristics_prefix):
                    # Inspect only the characteristic key. Ignore every other value byte-for-byte.
                    payload = line[len(characteristics_prefix):].lstrip()
                    colon = payload.find(b":")
                    if colon >= 0 and payload[:colon].strip() == b"io.therapy":
                        sample_has_therapy = True
                        try:
                            sample_therapies.append(payload[colon + 1:].strip().decode("utf-8"))
                        except UnicodeDecodeError as error:
                            raise PreparationError("GSE176307 io.therapy value is not UTF-8") from error
            finish_sample()
    except PreparationError:
        raise
    except (OSError, EOFError, gzip.BadGzipFile) as error:
        raise PreparationError("Cannot read the pinned GSE176307 family SOFT source") from error
    if not patients:
        raise PreparationError("Pinned GSE176307 SOFT contains no named patient samples")
    return patients


def _a1_excluded_tokens(patient_therapies: dict[str, dict[str, Any]]) -> set[str]:
    return {
        token for token, values in patient_therapies.items()
        if values.get("has_atezolizumab")
        or values.get("has_missing_therapy")
        or values.get("has_conflicting_therapy")
    }


def _canonical_token_list_hash(tokens: set[str] | list[str]) -> str:
    return _sha256_bytes(json.dumps(sorted(tokens), separators=(",", ":")).encode("utf-8"))


def _derive_freeze_table(
    features_path: Path, excluded_tokens: set[str], allowed: set[str]
) -> bytes:
    output = bytearray()
    try:
        with features_path.open("rb") as stream:
            output.extend(_read_header(stream))
            for line_number in itertools.count(2):
                identity_line = _read_framed_identity_line(stream, line_number, allowed)
                if identity_line is None:
                    break
                cohort, patient_id, raw_line = identity_line
                if cohort != "gse176307" or patient_id not in excluded_tokens:
                    output.extend(raw_line)
    except PreparationError:
        raise
    except OSError as error:
        raise PreparationError("Cannot derive the hash-bound A-P2 freeze table") from error
    return bytes(output)


def _a1_artifact(
    excluded_tokens: set[str], soft_sha256: str, code_sha256: str,
    source_features_sha256: str, derived_features_sha256: str,
) -> dict[str, Any]:
    token_list = sorted(excluded_tokens)
    return {
        "schema": "a_p2_source_rule_exclusions_v1",
        "rule_id": A1_RULE_ID,
        "excluded_tokens": token_list,
        "excluded_tokens_sha256": _canonical_token_list_hash(excluded_tokens),
        "soft_sha256": soft_sha256,
        "code_sha256": code_sha256,
        "source_features_sha256": source_features_sha256,
        "derived_features_sha256": derived_features_sha256,
    }


def _a1_artifact_matches(
    artifact: dict[str, Any], expected: dict[str, Any],
    source_gse_tokens: set[str], freeze_identities: list[dict[str, str]],
) -> bool:
    if artifact != expected or artifact.get("rule_id") != A1_RULE_ID:
        return False
    excluded = set(artifact.get("excluded_tokens", []))
    if excluded != set(expected["excluded_tokens"]):
        return False
    if not excluded <= source_gse_tokens:
        return False
    frozen_gse_tokens = {
        row["patient_id"] for row in freeze_identities if row["cohort"] == "gse176307"
    }
    return not (excluded & frozen_gse_tokens)


def _overlap_disposition(
    overlaps: dict[tuple[str, str], dict[str, str]],
    input_cohorts: set[str],
    main_cohorts: dict[str, dict[str, Any]],
    conservative_cohorts: dict[str, dict[str, Any]] | None,
    a1_source_rule_verified: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return release-blocking pairs and unresolved pairs outside the release scope."""
    blockers: list[dict[str, Any]] = []
    out_of_scope: list[dict[str, Any]] = []
    for pair, row in sorted(overlaps.items()):
        selected = {cohort for cohort in pair if cohort in input_cohorts}
        relevant = len(selected) == 2 or (
            len(selected) == 1 and any(_is_protected_final(cohort) for cohort in pair if cohort not in selected)
        )
        if not relevant:
            if row["status"] == UNRESOLVED:
                out_of_scope.append(
                    {
                        "cohorts": list(pair),
                        "status": UNRESOLVED,
                        "reason": "Neither a selected-selected pair nor a selected/protected-final pair for this development release.",
                    }
                )
            continue

        status = row["status"]
        reason: str | None = None
        if pair == tuple(sorted(("gse176307", "imvigor210"))) and status not in {UNRESOLVED, "RESOLVED_BY_SOURCE_RULE"}:
            reason = "GSE176307–IMvigor210 requires the signed A1 source rule; no other status closes this pair."
        elif status == UNRESOLVED:
            reason = row["resolution_rule"]
        elif status == "NOT_APPLICABLE_TO_A_P2":
            reason = "This status cannot close a pair that includes a selected input or the protected final test."
        elif status == "OVERLAP_RISK_GROUPED":
            if len(selected) != 2:
                reason = "OVERLAP_RISK_GROUPED requires both cohorts in the development manifest."
            elif main_cohorts[pair[0]]["study_family"] != main_cohorts[pair[1]]["study_family"]:
                reason = "OVERLAP_RISK_GROUPED requires the pair to share one study_family in the main manifest."
        elif status == "CONSERVATIVE_SENSITIVITY":
            if not set(pair) <= _CONSERVATIVE_FAMILY_COHORTS:
                reason = "CONSERVATIVE_SENSITIVITY is limited to pairs in the declared four-cohort melanoma family."
            elif len(selected) != 2:
                reason = "CONSERVATIVE_SENSITIVITY requires both cohorts in the selected inputs."
            elif main_cohorts[pair[0]]["study_family"] == main_cohorts[pair[1]]["study_family"]:
                reason = "CONSERVATIVE_SENSITIVITY requires the pair to remain separate in the main manifest."
            elif conservative_cohorts is None:
                reason = "The conservative-sensitivity manifest must be emitted and hash-bound."
            elif conservative_cohorts[pair[0]]["study_family"] != conservative_cohorts[pair[1]]["study_family"]:
                reason = "The conservative-sensitivity manifest must group the pair into one study_family."
        elif status == "RESOLVED_BY_SOURCE_RULE":
            if len(selected) == 2:
                reason = "RESOLVED_BY_SOURCE_RULE is prohibited for any selected-selected pair."
            elif pair != tuple(sorted(("gse176307", "imvigor210"))):
                reason = "RESOLVED_BY_SOURCE_RULE is accepted only for GSE176307–IMvigor210."
            elif row.get("rule_id") != A1_RULE_ID:
                reason = "GSE176307–IMvigor210 requires the exact A-P2 source-rule ID."
            elif not a1_source_rule_verified:
                reason = (
                    "GSE176307–IMvigor210 requires the hash-verified A1 exclusion artifact and a freeze "
                    "manifest bound to its derived table."
                )
        elif status == "NO_OVERLAP_DOCUMENTED":
            pass
        else:
            reason = "Unsupported overlap policy status."

        if reason is not None:
            blockers.append(
                {
                    "cohorts": list(pair),
                    "status": status,
                    "evidence_needed": reason,
                    "rule_id": row.get("rule_id", ""),
                }
            )
    return blockers, out_of_scope


def _identity_resolution_from_registry(
    overlap_rows: list[dict[str, Any]], blocked_pairs: set[tuple[str, str]]
) -> str:
    """Summarize one identity's resolution only from its in-scope registry pairs."""
    if not overlap_rows:
        raise PreparationError("An identity row has no in-scope registry-backed overlap resolution")

    pair_keys = {
        tuple(sorted(pair_row["cohorts"])): pair_row
        for pair_row in overlap_rows
    }
    if len(pair_keys) != len(overlap_rows):
        raise PreparationError("An identity row repeats an in-scope overlap registry pair")

    if any(pair in blocked_pairs for pair in pair_keys):
        return "UNRESOLVED_OVERLAP"

    # These are the only registry statuses that _overlap_disposition can accept for
    # a selected identity. NOT_APPLICABLE and UNRESOLVED must remain blockers in scope.
    explicitly_resolved = {
        "NO_OVERLAP_DOCUMENTED",
        "OVERLAP_RISK_GROUPED",
        "CONSERVATIVE_SENSITIVITY",
        "RESOLVED_BY_SOURCE_RULE",
    }
    if any(pair_row.get("status") not in explicitly_resolved for pair_row in overlap_rows):
        raise PreparationError("An identity row has no registry-backed resolution for every in-scope pair")
    return "RESOLVED_AUTHORITATIVE"


def _manifest_cohorts(
    sources: dict[str, dict[str, Any]], input_cohorts: set[str], conservative: bool
) -> dict[str, dict[str, Any]]:
    cohorts = _cohort_metadata(sources, input_cohorts)
    if conservative:
        if not _CONSERVATIVE_FAMILY_COHORTS <= input_cohorts:
            raise PreparationError("Conservative sensitivity requires Liu, Van Allen, Riaz, and Hugo inputs")
        for cohort in _CONSERVATIVE_FAMILY_COHORTS:
            cohorts[cohort]["study_family"] = _CONSERVATIVE_FAMILY
    return cohorts


def _build_package(
    *,
    package_id: str,
    operation: str,
    manifest_name: str,
    sidecar_name: str,
    release_name: str,
    features_path: Path,
    input_sha256: str,
    source_manifest_sha256: str,
    build_lineage: dict[str, Any],
    identities: list[dict[str, str]],
    registries: dict[str, Any],
    input_cohorts: set[str],
    conservative: bool,
    a1_source_rule_verified: bool,
    a1_artifact_sha256: str,
    a1_exclusion_sha256: str,
    soft_sha256: str,
    derived_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    sources = registries["sources"]
    main_metadata = _manifest_cohorts(sources, input_cohorts, False)
    conservative_metadata = _manifest_cohorts(sources, input_cohorts, True)
    cohort_metadata = conservative_metadata if conservative else main_metadata
    blockers, out_of_scope_unresolved = _overlap_disposition(
        registries["overlaps"], input_cohorts, main_metadata,
        conservative_metadata, a1_source_rule_verified,
    )
    resolution_status = "UNRESOLVED_OVERLAP" if blockers else "RESOLVED_NO_UNRESOLVED_OVERLAP"
    blocked_pairs = {
        tuple(sorted(item["cohorts"]))
        for item in blockers
    }
    identity_records = []
    for record in identities:
        cohort = record["cohort"]
        in_scope_pairs = []
        for pair, overlap in sorted(registries["overlaps"].items()):
            if cohort not in pair:
                continue
            selected = {name for name in pair if name in input_cohorts}
            relevant = len(selected) == 2 or (
                len(selected) == 1 and any(_is_protected_final(name) for name in pair if name not in selected)
            )
            if relevant:
                in_scope_pairs.append({
                    "cohorts": list(pair),
                    "status": overlap["status"],
                    "rule_id": overlap.get("rule_id", ""),
                })
        if not in_scope_pairs:
            raise PreparationError(f"No registry-backed in-scope overlap resolution exists for {cohort}")
        identity_resolution_status = _identity_resolution_from_registry(in_scope_pairs, blocked_pairs)
        identity_records.append({
            **record,
            "publication_family_id": cohort_metadata[cohort]["study_family"],
            "overlap_registry_pairs": in_scope_pairs,
            "resolution_status": identity_resolution_status,
        })
    sidecar = {
        "schema": "a_p2_identity_bindings_v1",
        "data_classification": REAL_CLASSIFICATION,
        "resolution_status": resolution_status,
        "provenance": {
            "kind": "authoritative_acquisition_registry",
            "registry_identity": REGISTRY_IDENTITY,
            **registries["hashes"],
            "identity_canonicalization": "a_p2:<cohort>:SHA-256(exact study-namespaced patient_id token)",
        },
        "uniqueness_checks": {
            "within_cohort_canonical_identity_unique": True,
            "across_cohort_canonical_identity_unique": True,
            "cross_cohort_identity_interpretation": (
                "Built patient_id values are study-namespaced tokens; comparison establishes token uniqueness only, "
                "not distinct people. No cross-study person matching is inferred."
            ),
        },
        "records": identity_records,
    }
    sidecar_bytes = _json_bytes(sidecar)
    identity_meta = {
        "schema": "a_p2_identity_provenance_v1",
        "kind": "authoritative_acquisition_registry",
        "registry_identity": REGISTRY_IDENTITY,
        **registries["hashes"],
        "sidecar": sidecar_name,
        "sidecar_sha256": _sha256_bytes(sidecar_bytes),
        "resolution_status": resolution_status,
    }
    feature_definitions = product._feature_definitions()
    source_objects = [
        {
            "cohort": cohort,
            "accession": sources[cohort]["accession"],
            "expression_file_identity": sources[cohort]["expression_file_identity"],
            "sha256": sources[cohort]["expression_sha256"],
        }
        for cohort in sorted(input_cohorts)
    ]
    lineage = {
        "kind": "source_derived",
        "source_build_manifest_sha256": source_manifest_sha256,
        "build_lineage": build_lineage,
        "source_object_sha256": sorted(
            sources[cohort]["expression_sha256"]
            for cohort in input_cohorts if sources[cohort]["primary_eligible"]
        ),
        "selected_expression_inputs": source_objects,
        "registered_but_absent_adaptive_sources": sorted(
            cohort for cohort, source in sources.items()
            if source["adaptive_eligible"] and cohort not in input_cohorts
        ),
    }
    lineage["a1_source_rule"] = {
        "rule_id": A1_RULE_ID,
        "exclusion_artifact_sha256": a1_artifact_sha256,
        "excluded_tokens_sha256": a1_exclusion_sha256,
        "source_soft_sha256": soft_sha256,
        "derived_features_sha256": derived_sha256,
    }
    manifest = {
        "schema": "a_p2_input_manifest_v1",
        "data_classification": REAL_CLASSIFICATION,
        "role": DEVELOPMENT_ROLE,
        "input_table": str(features_path.resolve()),
        "input_sha256": input_sha256,
        "feature_definition": product._FEATURE_DEFINITION,
        "feature_membership_sha256": {
            name: definition["membership_sha256"] for name, definition in feature_definitions.items()
        },
        "transform_contract": {
            "panel_feature_definition": product._FEATURE_DEFINITION,
            "primary_feature_transform": product._TPM_FEATURE_TRANSFORM,
            "cohort_transforms": {
                cohort: sources[cohort]["feature_transform"] for cohort in sorted(input_cohorts)
            },
            "cohort_expression_representations": {
                cohort: sources[cohort]["representation"] for cohort in sorted(input_cohorts)
            },
            "braun_scope": (
                "Braun is not produced by the current builder; its cohort-adaptive sensitivity needs a separate "
                "implementation and a later release. The seven-cohort release runs cohort-adaptive sensitivity "
                "on its seven selected cohorts."
            ),
            "cohort_adaptive_sensitivity_scope": "the seven selected eligible cohorts in this manifest",
        },
        "cyt_definition": product._CYT_DEFINITION,
        "cohorts": cohort_metadata,
        "identity_provenance": identity_meta,
        "provenance": lineage,
    }
    manifest_bytes = _json_bytes(manifest)
    manifest_hash = _sha256_bytes(manifest_bytes)
    release_record = {
        "record_type": "a_p2_user_release_v2",
        "record_status": "UNAPPROVED",
        "release_scope": "A_P2_REAL_OUTCOME_ACCESS",
        "data_classification": REAL_CLASSIFICATION,
        "operation": operation,
        "input_role": DEVELOPMENT_ROLE,
        "input_manifest_sha256": manifest_hash,
        "input_sha256": input_sha256,
        "identity_sidecar_sha256": identity_meta["sidecar_sha256"],
        **registries["hashes"],
        "cohorts": sorted(cohort_metadata),
        "outcome_fields": ["orr_class"],
        "decision": {
            "identity": PROPOSED_DECISION_ID,
            "path": f"docs/decisions/{PROPOSED_DECISION_ID}.md",
            "sha256": "PENDING_USER_SIGNATURE_HASH",
        },
    }
    return manifest, sidecar, {
        "package_id": package_id,
        "manifest_name": manifest_name,
        "sidecar_name": sidecar_name,
        "release_name": release_name,
        "manifest_bytes": manifest_bytes,
        "sidecar_bytes": sidecar_bytes,
        "release_bytes": _json_bytes(release_record),
        "release_record": release_record,
        "blocking_pairs": blockers,
        "out_of_scope_unresolved_pairs": out_of_scope_unresolved,
        "manifest_sha256": manifest_hash,
    }


def _validate_existing_sidecar(
    manifest: dict[str, Any],
    sidecar: dict[str, Any],
    sidecar_bytes: bytes,
    input_identities: list[dict[str, str]],
    registries: dict[str, Any],
    expected_blocking_pairs: set[tuple[str, str]],
) -> None:
    metadata = manifest["identity_provenance"]
    if _sha256_bytes(sidecar_bytes) != metadata["sidecar_sha256"]:
        raise PreparationError("A-P2 identity sidecar hash does not match the manifest")
    if sidecar.get("schema") != "a_p2_identity_bindings_v1":
        raise PreparationError("A-P2 identity sidecar has an unsupported schema")
    if sidecar.get("data_classification") != REAL_CLASSIFICATION:
        raise PreparationError("A-P2 identity sidecar classification does not match")
    provenance = sidecar.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("kind") != "authoritative_acquisition_registry":
        raise PreparationError("A-P2 sidecar is not linked to the authoritative acquisition registry")
    for key, digest in registries["hashes"].items():
        if metadata.get(key) != digest or provenance.get(key) != digest:
            raise PreparationError("A-P2 identity registry hash differs from the current registry")
    if provenance.get("registry_identity") != REGISTRY_IDENTITY:
        raise PreparationError("A-P2 identity registry identity does not match")
    if sidecar.get("resolution_status") != metadata.get("resolution_status"):
        raise PreparationError("A-P2 sidecar and manifest overlap statuses differ")
    if provenance.get("identity_canonicalization") != (
        "a_p2:<cohort>:SHA-256(exact study-namespaced patient_id token)"
    ):
        raise PreparationError("A-P2 sidecar identity-token canonicalization differs")
    uniqueness = sidecar.get("uniqueness_checks")
    if not isinstance(uniqueness, dict) or uniqueness.get("within_cohort_canonical_identity_unique") is not True or uniqueness.get("across_cohort_canonical_identity_unique") is not True:
        raise PreparationError("A-P2 sidecar lacks its identity-token uniqueness checks")
    if uniqueness.get("cross_cohort_identity_interpretation") != (
        "Built patient_id values are study-namespaced tokens; comparison establishes token uniqueness only, "
        "not distinct people. No cross-study person matching is inferred."
    ):
        raise PreparationError("A-P2 sidecar overstates cross-study patient identity evidence")
    records = sidecar.get("records")
    if not isinstance(records, list):
        raise PreparationError("A-P2 identity sidecar needs a records list")
    expected_pairs = {(row["cohort"], row["patient_id"]) for row in input_identities}
    observed_pairs: set[tuple[str, str]] = set()
    canonical_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise PreparationError("A-P2 identity sidecar record is invalid")
        required = ("cohort", "patient_id", "canonical_patient_uid", "publication_family_id", "resolution_status")
        if any(not isinstance(record.get(key), str) or not record[key] for key in required):
            raise PreparationError("A-P2 identity sidecar record is incomplete")
        identity_pair = (record["cohort"], record["patient_id"])
        if identity_pair in observed_pairs:
            raise PreparationError("A-P2 identity sidecar repeats an identity row")
        if record["canonical_patient_uid"] in canonical_ids:
            raise PreparationError("A-P2 duplicate canonical identity within or across cohorts")
        expected_uid = f"a_p2:{record['cohort']}:{_sha256_bytes(record['patient_id'].encode('utf-8'))}"
        if record["canonical_patient_uid"] != expected_uid:
            raise PreparationError("A-P2 sidecar canonical identity does not match its study-namespaced token")
        if record["cohort"] not in manifest["cohorts"]:
            raise PreparationError("A-P2 sidecar names a cohort absent from the manifest")
        if record["publication_family_id"] != manifest["cohorts"][record["cohort"]]["study_family"]:
            raise PreparationError("A-P2 sidecar family binding conflicts with the manifest")
        expected_overlap_rows = []
        for pair, overlap in sorted(registries["overlaps"].items()):
            if record["cohort"] not in pair:
                continue
            selected = {name for name in pair if name in manifest["cohorts"]}
            relevant = len(selected) == 2 or (
                len(selected) == 1 and any(_is_protected_final(name) for name in pair if name not in selected)
            )
            if relevant:
                expected_overlap_rows.append({
                    "cohorts": list(pair),
                    "status": overlap["status"],
                    "rule_id": overlap.get("rule_id", ""),
                })
        if record.get("overlap_registry_pairs") != expected_overlap_rows:
            raise PreparationError("A-P2 sidecar overlap resolution is not registry-derived")
        expected_resolution = _identity_resolution_from_registry(
            expected_overlap_rows, expected_blocking_pairs
        )
        if record["resolution_status"] != expected_resolution:
            raise PreparationError("A-P2 identity row resolution does not follow its in-scope registry pairs")
        observed_pairs.add(identity_pair)
        canonical_ids.add(record["canonical_patient_uid"])
    if observed_pairs != expected_pairs:
        raise PreparationError("A-P2 identity sidecar does not match the two identity columns")


def _validate_prepared_manifest(
    manifest: dict[str, Any],
    source_manifest_sha256: str,
    input_sha256: str,
    build_lineage: dict[str, Any],
    registries: dict[str, Any],
    input_cohorts: set[str],
    conservative: bool,
    expected_input_path: Path,
    expected_a1_binding: dict[str, str] | None,
) -> None:
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("kind") != "source_derived":
        raise PreparationError("Prepared manifest is missing source-derived provenance")
    if provenance.get("source_build_manifest_sha256") != source_manifest_sha256:
        raise PreparationError("Prepared manifest does not bind the current built input manifest")
    if provenance.get("build_lineage") != build_lineage:
        raise PreparationError("Prepared manifest build receipt, source, membership, alias, or builder lineage differs")
    if manifest.get("input_sha256") != input_sha256:
        raise PreparationError("Prepared manifest does not bind the current feature table")
    if manifest.get("input_table") != str(expected_input_path.resolve()):
        raise PreparationError("Prepared manifest does not bind the expected absolute input-table path")
    expected_memberships = build_lineage["feature_membership_sha256"]
    if manifest.get("feature_membership_sha256") != expected_memberships:
        raise PreparationError("Prepared manifest feature memberships differ from the build lineage")
    expected_cohorts = _manifest_cohorts(
        registries["sources"], input_cohorts, conservative
    )
    if manifest.get("cohorts") != expected_cohorts:
        raise PreparationError("Prepared manifest cohort or study-family declarations differ from the registry")
    expected_source_hashes = sorted(
        registries["sources"][cohort]["expression_sha256"]
        for cohort in input_cohorts
        if registries["sources"][cohort]["primary_eligible"]
    )
    if provenance.get("source_object_sha256") != expected_source_hashes:
        raise PreparationError("Prepared manifest selected source hashes differ from the registry")
    expected_selected = [
        {
            "cohort": cohort,
            "accession": registries["sources"][cohort]["accession"],
            "expression_file_identity": registries["sources"][cohort]["expression_file_identity"],
            "sha256": registries["sources"][cohort]["expression_sha256"],
        }
        for cohort in sorted(input_cohorts)
    ]
    if provenance.get("selected_expression_inputs") != expected_selected:
        raise PreparationError("Prepared manifest selected expression identities differ from the registry")
    if provenance.get("a1_source_rule") != expected_a1_binding:
        raise PreparationError("Manifest does not bind the verified A1 source-rule companion")


def _signed_dimension_errors(*, input_cohorts: set[str], input_count: int, bladder_count: int,
                             excluded_count: int, derived_count: int, main_families: int,
                             conservative_families: int) -> list[str]:
    actual = {"input_cohorts": input_cohorts, "input_count": input_count,
              "bladder_count": bladder_count, "excluded_count": excluded_count,
              "derived_count": derived_count, "main_families": main_families,
              "conservative_families": conservative_families}
    expected = {"input_cohorts": _REQUIRED_PRIMARY, "input_count": 408,
                "bladder_count": 87, "excluded_count": 33, "derived_count": 375,
                "main_families": 6, "conservative_families": 4}
    return [name for name, value in expected.items() if actual[name] != value]


def _package_report(
    manifest_path: Path,
    manifest: dict[str, Any],
    details: dict[str, Any],
    input_cohorts: set[str],
    registries: dict[str, Any],
    operation: str,
) -> dict[str, Any]:
    sources = registries["sources"]
    missing_primary = sorted(
        cohort for cohort, source in sources.items()
        if source["primary_eligible"] and cohort not in input_cohorts
    )
    missing_adaptive = sorted(
        cohort for cohort, source in sources.items()
        if source["adaptive_eligible"] and cohort not in input_cohorts
    )
    shape_status = "PASS"
    try:
        product._validate_manifest_shape(manifest_path, manifest, operation)
    except (product.ProductError, PermissionError) as error:
        shape_status = "BLOCKED: " + str(error)
    identity_status = "PASS"
    try:
        product._validate_identity_provenance(manifest)
    except PermissionError as error:
        identity_status = "BLOCKED: " + str(error)
    blockers = details["blocking_pairs"]
    structural_status = "BLOCKED" if blockers or missing_primary or shape_status != "PASS" or identity_status != "PASS" else "PASS"
    return {
        "status": "BLOCKED",
        "structural_status": structural_status,
        "release_readiness": "INDEPENDENT_BINDINGS_REQUIRED",
        "product_manifest_shape": shape_status,
        "product_identity_provenance": identity_status,
        "input_sha256": manifest["input_sha256"],
        "input_manifest_sha256": details["manifest_sha256"],
        "identity_sidecar_sha256": manifest["identity_provenance"]["sidecar_sha256"],
        "blocking_pairs": blockers,
        "unresolved_pairs_out_of_scope": details["out_of_scope_unresolved_pairs"],
        "missing_primary_cohorts": missing_primary,
        "missing_adaptive_cohorts": missing_adaptive,
        "release_record_status": "UNAPPROVED",
    }


def _expected_package_specs(
    features_path: Path,
    input_sha256: str,
    identities: list[dict[str, str]],
    input_cohorts: set[str],
    derived_path: Path,
    derived_sha256: str,
    derived_identities: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "package_id": "main",
            "operation": "development",
            "manifest_name": MANIFEST_NAME,
            "sidecar_name": SIDECAR_NAME,
            "release_name": "release_development.unapproved.json",
            "features_path": features_path,
            "input_sha256": input_sha256,
            "identities": identities,
            "conservative": False,
            "a1_source_rule_verified": True,
        },
        {
            "package_id": "freeze",
            "operation": "freeze",
            "manifest_name": FREEZE_MANIFEST_NAME,
            "sidecar_name": FREEZE_SIDECAR_NAME,
            "release_name": FREEZE_RELEASE_NAME,
            "features_path": derived_path,
            "input_sha256": derived_sha256,
            "identities": derived_identities,
            "conservative": False,
            "a1_source_rule_verified": True,
        },
        {
            "package_id": "development_sensitivity",
            "operation": "development",
            "manifest_name": SENSITIVITY_MANIFEST_NAME,
            "sidecar_name": SENSITIVITY_SIDECAR_NAME,
            "release_name": SENSITIVITY_RELEASE_NAME,
            "features_path": derived_path,
            "input_sha256": derived_sha256,
            "identities": derived_identities,
            "conservative": False,
            "a1_source_rule_verified": True,
        },
        {
            "package_id": "conservative",
            "operation": "development",
            "manifest_name": CONSERVATIVE_MANIFEST_NAME,
            "sidecar_name": CONSERVATIVE_SIDECAR_NAME,
            "release_name": CONSERVATIVE_RELEASE_NAME,
            "features_path": features_path,
            "input_sha256": input_sha256,
            "identities": identities,
            "conservative": True,
            "a1_source_rule_verified": True,
        },
    ]


def prepare_development(
    inputs_dir: Path,
    out_dir: Path,
    *,
    check_only: bool = False,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    geo_soft_path: Path | None = None,
) -> dict[str, Any]:
    """Write or structurally check all private A-P2 release-preparation packages."""
    guarded_inputs, guarded_out, features_path, source_manifest_path = _prepare_paths(
        Path(inputs_dir), Path(out_dir), check_only, DEFAULT_SCRATCH_ROOT
    )
    registries = _load_registries(_protected_path(Path(registry_dir), "identity registry directory"))
    sources = registries["sources"]
    identities = _read_identity_rows(features_path, set(sources))
    input_cohorts = _input_cohorts(identities)
    source_manifest, source_manifest_bytes = _read_json(source_manifest_path, "built input manifest")
    input_sha256 = _sha256_file(features_path)
    expected_input_hash = source_manifest.get("output_sha256", {}).get("features.tsv")
    if not isinstance(expected_input_hash, str) or expected_input_hash != input_sha256:
        raise PreparationError("A-P2 feature table hash does not match the built input manifest")
    source_manifest_sha256 = _sha256_bytes(source_manifest_bytes)
    build_lineage = _build_lineage(source_manifest, input_cohorts, registries)
    if build_lineage["receipt_output_sha256"].get("features.tsv") != input_sha256:
        raise PreparationError("A-P2 feature hash differs from the build receipt output lineage")

    soft_path, soft_sha256 = _resolve_gse_soft_path(guarded_inputs, geo_soft_path)
    patient_therapies = _read_gse176307_patient_therapies(soft_path)
    recomputed_tokens = set(patient_therapies)
    built_gse_tokens = {
        row["patient_id"] for row in identities if row["cohort"] == "gse176307"
    }
    # GEO lists every submitted patient; the builder later drops some for timing,
    # missing assay or missing label. Every built patient must be found in GEO, and
    # the rule is applied to built patients only.
    if not built_gse_tokens <= recomputed_tokens:
        raise PreparationError("recomputed GSE176307 patient tokens do not match: a built identity is absent from the SOFT")
    patient_therapies = {
        token: values for token, values in patient_therapies.items() if token in built_gse_tokens
    }
    if input_sha256 == _MAIN_FEATURES_SHA256 and len(built_gse_tokens) != 87:
        raise PreparationError("Hash-verified real A-P2 input does not contain the expected 87 GSE176307 identities")

    excluded_tokens = _a1_excluded_tokens(patient_therapies)
    derived_bytes = _derive_freeze_table(features_path, excluded_tokens, set(sources))
    derived_sha256 = _sha256_bytes(derived_bytes)
    derived_path = guarded_out / FREEZE_TABLE_NAME
    derived_identities = [
        row for row in identities
        if not (row["cohort"] == "gse176307" and row["patient_id"] in excluded_tokens)
    ]
    code_sha256 = _sha256_file(Path(__file__))
    artifact = _a1_artifact(
        excluded_tokens, soft_sha256, code_sha256, input_sha256, derived_sha256
    )
    artifact_bytes = _json_bytes(artifact)
    artifact_sha256 = _sha256_bytes(artifact_bytes)
    artifact_path = guarded_out / A1_EXCLUSIONS_NAME
    artifact_verified = _a1_artifact_matches(
        artifact, artifact, built_gse_tokens, derived_identities
    ) and artifact["derived_features_sha256"] == derived_sha256
    if not artifact_verified:
        raise PreparationError("The A1 source-rule exclusion artifact failed its own structural checks")
    a1_binding = {
        "rule_id": A1_RULE_ID,
        "exclusion_artifact_sha256": artifact_sha256,
        "excluded_tokens_sha256": artifact["excluded_tokens_sha256"],
        "source_soft_sha256": soft_sha256,
        "derived_features_sha256": derived_sha256,
    }

    specs = _expected_package_specs(
        features_path, input_sha256, identities, input_cohorts,
        derived_path, derived_sha256, derived_identities,
    )
    packages: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
    for spec in specs:
        a1_valid_for_package = artifact_verified and spec["a1_source_rule_verified"]
        packages[spec["package_id"]] = _build_package(
            package_id=spec["package_id"],
            operation=spec["operation"],
            manifest_name=spec["manifest_name"],
            sidecar_name=spec["sidecar_name"],
            release_name=spec["release_name"],
            features_path=spec["features_path"],
            input_sha256=spec["input_sha256"],
            source_manifest_sha256=source_manifest_sha256,
            build_lineage=build_lineage,
            identities=spec["identities"],
            registries=registries,
            input_cohorts=input_cohorts,
            conservative=spec["conservative"],
            a1_source_rule_verified=a1_valid_for_package,
            a1_artifact_sha256=artifact_sha256,
            a1_exclusion_sha256=artifact["excluded_tokens_sha256"],
            soft_sha256=soft_sha256,
            derived_sha256=derived_sha256,
        )

    if check_only:
        try:
            actual_artifact, actual_artifact_bytes = _read_json(artifact_path, "A1 source-rule exclusions")
        except PreparationError as error:
            raise PreparationError("The A1 source-rule exclusion artifact is missing or invalid") from error
        actual_derived = _protected_path(derived_path, "derived A-P2 freeze table")
        if actual_artifact != artifact or actual_artifact_bytes != artifact_bytes:
            raise PreparationError("The A1 source-rule exclusion artifact hashes do not match the pinned source and code")
        if not actual_derived.is_file() or actual_derived.read_bytes() != derived_bytes:
            raise PreparationError("The derived A-P2 freeze table does not match the source rule and excluded tokens")
    else:
        if guarded_out.exists():
            raise FileExistsError("A-P2 preparation output directory must be fresh")
        if not guarded_out.resolve(strict=False).is_relative_to(
            _protected_path(DEFAULT_SCRATCH_ROOT, "private scratch directory")
        ):
            raise PreparationError("A-P2 preparation output escaped the private .scratch/runtime directory")
        guarded_out.mkdir(parents=True)
        derived_path.write_bytes(derived_bytes)
        artifact_path.write_bytes(artifact_bytes)

    package_reports: dict[str, dict[str, Any]] = {}
    package_hashes: dict[str, dict[str, str]] = {}
    for spec in specs:
        package_id = spec["package_id"]
        manifest, sidecar, details = packages[package_id]
        manifest_path = _protected_path(guarded_out / details["manifest_name"], "prepared A-P2 manifest")
        sidecar_path = _protected_path(guarded_out / details["sidecar_name"], "prepared A-P2 sidecar")
        release_path = _protected_path(guarded_out / details["release_name"], "unapproved A-P2 release template")
        if check_only:
            actual_manifest, actual_manifest_bytes = _read_json(manifest_path, "prepared A-P2 manifest")
            actual_sidecar, actual_sidecar_bytes = _read_json(sidecar_path, "prepared A-P2 identity sidecar")
            actual_release, actual_release_bytes = _read_json(release_path, "unapproved A-P2 release template")
            expected_a1 = a1_binding
            _validate_prepared_manifest(
                actual_manifest, source_manifest_sha256, spec["input_sha256"],
                build_lineage, registries, input_cohorts, spec["conservative"],
                spec["features_path"], expected_a1,
            )
            expected_blocking_pairs = {
                tuple(sorted(item["cohorts"])) for item in details["blocking_pairs"]
            }
            _validate_existing_sidecar(
                actual_manifest, actual_sidecar, actual_sidecar_bytes,
                spec["identities"], registries, expected_blocking_pairs,
            )
            if actual_manifest_bytes != details["manifest_bytes"]:
                raise PreparationError(
                    "Prepared manifest build receipt, source, membership, alias, or builder lineage differs"
                )
            if actual_sidecar_bytes != details["sidecar_bytes"]:
                raise PreparationError(f"Prepared {package_id} sidecar bytes or hash do not match its inputs")
            if actual_release_bytes != details["release_bytes"] or actual_release.get("record_status") != "UNAPPROVED":
                if package_id == "freeze":
                    raise PreparationError("freeze release template does not bind the derived table and remain UNAPPROVED")
                raise PreparationError(f"The {package_id} release template does not match its manifest and remain UNAPPROVED")
            manifest, sidecar = actual_manifest, actual_sidecar
        else:
            manifest_path.write_bytes(details["manifest_bytes"])
            sidecar_path.write_bytes(details["sidecar_bytes"])
            release_path.write_bytes(details["release_bytes"])
        try:
            product._validate_manifest_shape(manifest_path, manifest, spec["operation"])
        except product.ProductError as error:
            raise PreparationError(f"Prepared {package_id} manifest is not accepted by A-P2: {error}") from error
        package_reports[package_id] = _package_report(
            manifest_path, manifest, details, input_cohorts, registries, spec["operation"]
        )
        package_hashes[package_id] = {
            "input_sha256": spec["input_sha256"],
            "manifest_sha256": details["manifest_sha256"],
            "sidecar_sha256": manifest["identity_provenance"]["sidecar_sha256"],
            "release_template_sha256": _sha256_bytes(details["release_bytes"]),
        }

    dimension_errors = _signed_dimension_errors(
        input_cohorts=input_cohorts, input_count=len(identities), bladder_count=len(built_gse_tokens),
        excluded_count=len(excluded_tokens), derived_count=len(derived_identities),
        main_families=len({c["study_family"] for c in _manifest_cohorts(sources, input_cohorts, False).values()}),
        conservative_families=len({c["study_family"] for c in _manifest_cohorts(sources, input_cohorts, True).values()}),
    )
    binding_errors = []
    if input_sha256 != _MAIN_FEATURES_SHA256:
        binding_errors.append("original_input_hash")
    if source_manifest_sha256 != _HISTORICAL_BUILD_RECEIPT_SHA256:
        binding_errors.append("historical_receipt_hash")
    for report in package_reports.values():
        report["signed_dimension_errors"] = dimension_errors
        report["historical_binding_errors"] = binding_errors
    main = package_reports["main"]
    main.update({
        "outcome_gate": "NOT_OPENED",
        "source_registry_hashes": registries["hashes"],
        "build_lineage_status": "PASS",
        "input_cohorts": sorted(input_cohorts),
        "cohort_adaptive_sensitivity_cohorts": sorted(
            cohort for cohort in input_cohorts if sources[cohort]["adaptive_eligible"]
        ),
        "identity_uniqueness": packages["main"][1]["uniqueness_checks"],
        "conservative_sensitivity_emitted": True,
        "conservative_manifest_sha256": package_hashes["conservative"]["manifest_sha256"],
        "package_hashes": package_hashes,
        "a1_rule_id": A1_RULE_ID,
        "gse176307_identity_token_match": "PASS",
        "gse176307_patient_count": len(built_gse_tokens),
        "a1_exclusion_count": len(excluded_tokens),
        "a1_exclusion_denominator": len(built_gse_tokens),
        "a1_exclusion_artifact_sha256": artifact_sha256,
        "a1_excluded_tokens_sha256": artifact["excluded_tokens_sha256"],
        "a1_soft_sha256": soft_sha256,
        "a1_code_sha256": code_sha256,
        "freeze_table_sha256": derived_sha256,
        "unresolved_pairs_out_of_scope": packages["main"][2]["out_of_scope_unresolved_pairs"],
    })
    main["conservative_sensitivity"] = package_reports["conservative"]
    main["freeze"] = package_reports["freeze"]
    main["development_sensitivity"] = package_reports["development_sensitivity"]
    return main

