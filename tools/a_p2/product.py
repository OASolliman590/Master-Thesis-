"""Patient-free orchestration and release gates for the A-P2 product."""

from __future__ import annotations

import hashlib
import csv
import io
import inspect
import json
import re
import shutil
from pathlib import Path
from typing import Any

from tools.a_scoring import core as scoring_core
from tools.a_scoring.core import DEFAULT_PANELS, panel_definitions
from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]
R_SCRIPT = ROOT / "r/R/a_p2.R"
_HEX_256 = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_FEATURES = tuple(DEFAULT_PANELS)
_FEATURE_DEFINITION = "arithmetic mean over every member of each frozen panel after the cohort-declared source transform"
_CYT_DEFINITION = "sqrt(TPM_GZMA * TPM_PRF1)"
_TPM_FEATURE_TRANSFORM = "log2(TPM + 1)"
_DEPOSITED_LOG2_FEATURE_TRANSFORM = "deposited log2 upper-quartile"
_ALLOWED_FEATURE_TRANSFORMS = {
    _TPM_FEATURE_TRANSFORM,
    _DEPOSITED_LOG2_FEATURE_TRANSFORM,
}
_REAL_CLASS = "PRIVATE_PATIENT_LEVEL"
_SYNTHETIC_CLASS = "SYNTHETIC_ONLY"
_OUTCOME_FIELD = "orr_class"
_COMPARATOR_CAVEAT = "M2 includes GZMA and PRF1 and therefore partly overlaps the CYT comparator."
_KNOWN_REAL_IDENTITY_TOKENS = {
    "liu2019", "riaz_gse91061", "gse91061", "srp094781",
    "hugo_gse78220", "gse78220", "vanallen2015", "kim2018",
    "gide2019", "gse176307", "braun2020",
}
_PROTECTED_IDENTITY_TOKENS = {"imvigor", "imvigor210"}
_DECISION_DIR = ROOT / "docs/decisions"
_CODE_HASH_INPUTS = {
    "python_product": Path(__file__),
    "python_cli": ROOT / "tools/a_p2/__main__.py",
    "r_entrypoint": R_SCRIPT,
    "r_random_streams": ROOT / "r/R/random_streams.R",
    "r_bridge": Path(inspect.getfile(run_r)),
    "panel_registry": Path(inspect.getfile(panel_definitions)),
    "renv_lock": ROOT / "r/renv.lock",
    "numerical_freeze_register": ROOT / "specs/A/NUMERICAL_FREEZE_REGISTER.tsv",
    "validation_contract": ROOT / "specs/amendments/2026-11-02-paper-a-validation/AMENDMENT.md",
    "measurement_decision": ROOT / "docs/decisions/A_P2_MEASUREMENT_20261102.md",
}


class ProductError(ValueError):
    """An A-P2 input, authorization, or output contract is invalid."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _known_source_identity_tokens() -> set[str]:
    tokens = set(_KNOWN_REAL_IDENTITY_TOKENS)
    metadata_path = _guard_external_path(
        _DECISION_DIR / "A_P2_MEASUREMENT_20261102.md", "patient-free identity metadata"
    )
    try:
        with metadata_path.open(encoding="utf-8") as stream:
            in_cohort_table = False
            for line in stream:
                if not in_cohort_table:
                    in_cohort_table = line.strip().casefold().startswith("| cohort |")
                    continue
                if not line.startswith("|"):
                    break
                cells = line.split("|")
                if len(cells) < 3:
                    continue
                label = cells[1].strip().strip("`")
                if label and label.casefold() not in {"cohort", "---"}:
                    tokens.update(_identity_tokens(label))
    except OSError as error:
        raise PermissionError("Patient-free A-P2 identity metadata is unavailable") from error
    return tokens


def _guard_external_path(
    path: Path, label: str, *, allow_protected: bool = False
) -> Path:
    """Reject aliases before following them, then check the resolved path too."""
    original = Path(path).expanduser()
    if not original.is_absolute():
        original = Path.cwd() / original

    current = Path(original.anchor)
    for component in original.parts[1:]:
        current = current / component
        if current.is_symlink():
            raise PermissionError(f"A-P2 {label} path has symlink ancestry")

    resolved = original.resolve(strict=False)
    original_parts = [part for part in original.parts if part not in {original.anchor, "", ".", ".."}]
    resolved_parts = [part for part in resolved.parts if part not in {resolved.anchor, "", ".", ".."}]
    all_parts = original_parts + resolved_parts
    if any(re.sub(r"[^a-z0-9]", "", part.casefold()) == "ingestionpacketjson" for part in all_parts):
        raise PermissionError("A-P2 never reads ingestion_packet.json")
    if not allow_protected and any(
        _identity_tokens(part) & _PROTECTED_IDENTITY_TOKENS for part in all_parts
    ):
        raise PermissionError(f"A-P2 {label} path names a protected path")
    return resolved


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        guarded = _guard_external_path(path, label)
        raw = guarded.read_bytes()
        value = json.loads(raw)
    except PermissionError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProductError(f"Cannot read {label} metadata: {error}") from error
    if not isinstance(value, dict):
        raise ProductError(f"{label} must be a JSON object")
    return value, raw


def _verify_equation(path: Path) -> tuple[dict[str, Any], str, bytes]:
    equation, raw = _read_json(path, "frozen equation")
    declared = equation.get("equation_sha256")
    if not isinstance(declared, str) or not _HEX_256.fullmatch(declared):
        raise ProductError("Frozen equation has no valid equation_sha256")
    content = dict(equation)
    content.pop("equation_sha256", None)
    actual = _sha256_bytes(_canonical_json(content))
    if actual != declared:
        raise ProductError("Frozen equation hash does not match its contents")
    if equation.get("schema") != "a_p2_equation_v1":
        raise ProductError("Unsupported frozen equation schema")
    for model_name in ("primary", "cohort_adaptive"):
        model = equation.get(model_name)
        if not isinstance(model, dict) or not model.get("available"):
            continue
        coefficients = {
            "coefficients": model.get("coefficients"),
            "intercept": model.get("intercept"),
        }
        if _sha256_bytes(_canonical_json(coefficients)) != model.get("coefficient_sha256"):
            raise ProductError(f"Frozen {model_name} coefficient hash does not match")
        scaling = model.get("scaling") if model_name == "primary" else model.get("scaling_by_study")
        if _sha256_bytes(_canonical_json(scaling)) != model.get("scaling_sha256"):
            raise ProductError(f"Frozen {model_name} scaling hash does not match")
    return equation, actual, raw


def _cohort_ids(manifest: dict[str, Any]) -> list[str]:
    cohorts = manifest.get("cohorts")
    if not isinstance(cohorts, dict) or not cohorts:
        raise ProductError("Input manifest must declare cohort, family, and representation metadata")
    if any(not isinstance(name, str) or not name for name in cohorts):
        raise ProductError("Input manifest cohort identifiers must be non-empty strings")
    return sorted(cohorts)


def _check_imvigor_barrier(
    manifest: dict[str, Any], operation: str, classification: str
) -> None:
    protected = []
    for cohort, metadata in manifest.get("cohorts", {}).items():
        values = [cohort]
        if isinstance(metadata, dict) and isinstance(metadata.get("study_family"), str):
            values.append(metadata["study_family"])
        if any(_identity_tokens(value) & _PROTECTED_IDENTITY_TOKENS for value in values):
            protected.append(cohort)
    if not protected:
        return
    if classification == _SYNTHETIC_CLASS:
        return
    if classification != _REAL_CLASS or operation != "final-evaluate":
        raise PermissionError("IMvigor210 is blocked outside an explicitly released real final evaluation")
    if manifest.get("role") != "final_test" or len(_cohort_ids(manifest)) != 1:
        raise PermissionError("IMvigor210 requires the single final_test input role")


def _input_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    value = manifest.get("input_table")
    if not isinstance(value, str) or not value:
        raise ProductError("Input manifest must name input_table")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = manifest_path.parent / candidate
    allow_protected = (
        manifest.get("data_classification") == _REAL_CLASS
        and manifest.get("role") == "final_test"
    )
    return _guard_external_path(candidate, "input table", allow_protected=allow_protected)


def _identity_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    identity = manifest.get("identity_provenance")
    value = identity.get("sidecar") if isinstance(identity, dict) else None
    if not isinstance(value, str) or not value:
        raise ProductError("A-P2 requires a hash-bound identity sidecar")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = manifest_path.parent / candidate
    allow_protected = (
        manifest.get("data_classification") == _REAL_CLASS
        and manifest.get("role") == "final_test"
    )
    return _guard_external_path(candidate, "identity sidecar", allow_protected=allow_protected)


def _validate_manifest_shape(
    manifest_path: Path, manifest: dict[str, Any], operation: str
) -> tuple[Path, str, str]:
    if manifest.get("schema") != "a_p2_input_manifest_v1":
        raise ProductError("Unsupported A-P2 input manifest schema")
    if manifest.get("feature_definition") != _FEATURE_DEFINITION:
        raise ProductError("Input manifest does not declare the frozen complete panel-feature transform")
    if manifest.get("cyt_definition") != _CYT_DEFINITION:
        raise ProductError("Input manifest does not declare the exact no-offset CYT comparator")
    expected_memberships = {
        name: definition["membership_sha256"]
        for name, definition in _feature_definitions().items()
    }
    if manifest.get("feature_membership_sha256") != expected_memberships:
        raise ProductError("Input panel memberships do not match the frozen A-P2 gene sets")
    role = "final_test" if operation == "final-evaluate" else "development"
    if manifest.get("role") != role:
        raise ProductError(f"{operation} requires input role {role!r}")
    classification = manifest.get("data_classification")
    if classification not in {_SYNTHETIC_CLASS, _REAL_CLASS}:
        raise ProductError("Input manifest needs an explicit data_classification")
    cohorts = _cohort_ids(manifest)
    for cohort, metadata in manifest["cohorts"].items():
        if not isinstance(metadata, dict):
            raise ProductError(f"Cohort metadata is not an object: {cohort}")
        required = {
            "study_family", "cancer", "representation", "feature_transform",
            "primary_eligible", "adaptive_eligible", "cyt_available",
        }
        if not required <= metadata.keys():
            raise ProductError(f"Cohort metadata is incomplete: {cohort}")
        if not all(isinstance(metadata[key], str) and metadata[key] for key in ("study_family", "cancer", "representation")):
            raise ProductError(f"Cohort family, cancer, and representation must be named: {cohort}")
        if not all(isinstance(metadata[key], bool) for key in ("primary_eligible", "adaptive_eligible", "cyt_available")):
            raise ProductError(f"Cohort eligibility metadata must be explicit booleans: {cohort}")
        if not isinstance(metadata["feature_transform"], str) or metadata["feature_transform"] not in _ALLOWED_FEATURE_TRANSFORMS:
            raise ProductError(f"Cohort feature transformation is not in the A-P2 measurement contract: {cohort}")
        if metadata["primary_eligible"] and metadata["feature_transform"] != _TPM_FEATURE_TRANSFORM:
            raise ProductError(f"Primary A-P2 cohorts must declare log2(TPM + 1) panel features: {cohort}")
        if metadata["primary_eligible"] and not metadata["cyt_available"]:
            raise ProductError(f"Primary TPM cohort must declare CYT availability: {cohort}")
    if operation == "final-evaluate" and (len(cohorts) != 1 or len({manifest["cohorts"][key]["study_family"] for key in cohorts}) != 1):
        raise ProductError("Final evaluation accepts exactly one complete study family")
    input_digest = manifest.get("input_sha256")
    if not isinstance(input_digest, str) or not _HEX_256.fullmatch(input_digest):
        raise ProductError("Input manifest needs the exact input_sha256")
    input_path = _input_path(manifest_path, manifest)
    identity = manifest.get("identity_provenance")
    if not isinstance(identity, dict) or identity.get("schema") != "a_p2_identity_provenance_v1":
        raise ProductError("A-P2 identity provenance must use a_p2_identity_provenance_v1")
    sidecar_digest = identity.get("sidecar_sha256")
    if not isinstance(sidecar_digest, str) or not _HEX_256.fullmatch(sidecar_digest):
        raise ProductError("A-P2 identity sidecar needs its exact SHA256")
    return input_path, classification, input_digest


def _synthetic_authorization(manifest: dict[str, Any]) -> None:
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        raise PermissionError("Synthetic operation requires an explicit generated-fixture provenance record")
    expected = {
        "kind": "generated_fixture",
        "authorization": "synthetic-test-authorization",
        "signatures_present": False,
        "valid_as_real_approval": False,
    }
    if any(provenance.get(key) != value for key, value in expected.items()):
        raise PermissionError("Synthetic fixture authorization is invalid and cannot authorize real outcomes")
    fixture_id = provenance.get("fixture_id")
    if not isinstance(fixture_id, str) or not fixture_id:
        raise PermissionError("Synthetic fixture must have a named generator identity")

    identity = manifest.get("identity_provenance")
    if not isinstance(identity, dict) or any(identity.get(key) != expected for key, expected in {
        "kind": "generated_fixture",
        "fixture_id": fixture_id,
        "valid_as_real_identity_evidence": False,
    }.items()):
        raise PermissionError("Synthetic fixture identity provenance is missing or can be mistaken for real evidence")
    _validate_synthetic_identities(manifest)


def _validate_synthetic_identities(manifest: dict[str, Any]) -> None:
    authoritative_tokens = _known_source_identity_tokens()
    for cohort, metadata in manifest["cohorts"].items():
        identities = (("cohort", cohort), ("study_family", metadata["study_family"]))
        for identity_type, value in identities:
            tokens = _identity_tokens(value)
            if tokens & _PROTECTED_IDENTITY_TOKENS:
                raise PermissionError(f"Synthetic fixture names IMvigor210 or another protected source identity ({identity_type})")
            if tokens & authoritative_tokens:
                raise PermissionError(f"Synthetic fixture names a known A-P2 source identity ({identity_type})")


def _validate_identity_provenance(manifest: dict[str, Any]) -> None:
    identity = manifest["identity_provenance"]
    if manifest["data_classification"] == _SYNTHETIC_CLASS:
        fixture_id = manifest["provenance"]["fixture_id"]
        required = {
            "kind": "generated_fixture",
            "fixture_id": fixture_id,
            "valid_as_real_identity_evidence": False,
        }
        if any(identity.get(key) != value for key, value in required.items()):
            raise PermissionError("Synthetic identity sidecar is not explicitly limited to generated fixtures")
        return

    required_hashes = (
        "source_registry_sha256",
        "publication_family_registry_sha256",
        "overlap_registry_sha256",
    )
    if identity.get("kind") != "authoritative_acquisition_registry":
        raise PermissionError("Real A-P2 needs authoritative patient and family identity provenance")
    if not isinstance(identity.get("registry_identity"), str) or not identity["registry_identity"]:
        raise PermissionError("Real A-P2 identity provenance needs its authoritative registry identity")
    if any(not isinstance(identity.get(key), str) or not _HEX_256.fullmatch(identity[key]) for key in required_hashes):
        raise PermissionError("Real A-P2 identity provenance needs exact source, family, and overlap registry hashes")
    if identity.get("resolution_status") != "RESOLVED_NO_UNRESOLVED_OVERLAP":
        raise PermissionError("Real A-P2 identity and overlap resolution is incomplete")


def _authorize_real(
    manifest: dict[str, Any], manifest_bytes: bytes, operation: str,
    release_record_path: Path | None, equation_hash: str | None,
) -> None:
    if release_record_path is None:
        raise PermissionError("Real A-P2 outcome access requires an approved user-release record")
    record, _ = _read_json(release_record_path, "user-release record")
    if not _release_record_is_approved(record):
        raise PermissionError("The user-release record is missing or is not an approved real decision")
    decision = record.get("decision")
    if not isinstance(decision, dict):
        raise PermissionError("The user-release record must reference a scoped decision identity and hash")
    if set(decision) != {"identity", "path", "sha256"}:
        raise PermissionError("The user-release decision reference has missing or contradictory fields")
    decision_identity = decision.get("identity")
    decision_path_value = decision.get("path")
    decision_digest = decision.get("sha256")
    if not isinstance(decision_identity, str) or not decision_identity:
        raise PermissionError("The user-release decision identity is missing")
    if not isinstance(decision_path_value, str) or not decision_path_value.startswith("docs/decisions/"):
        raise PermissionError("The user-release decision must reference a scoped docs/decisions record")
    if not isinstance(decision_digest, str) or not _HEX_256.fullmatch(decision_digest):
        raise PermissionError("The user-release decision record needs its exact SHA256")
    decision_path = _guard_external_path(ROOT / decision_path_value, "decision record")
    try:
        decision_path.relative_to(_DECISION_DIR.resolve())
    except ValueError as error:
        raise PermissionError("The user-release decision path is outside docs/decisions") from error
    if decision_path.stem != decision_identity or _sha256_file(decision_path) != decision_digest:
        raise PermissionError("The referenced user decision identity or hash does not match")

    exact_cohorts = _cohort_ids(manifest)
    identity = manifest["identity_provenance"]
    required = {
        "data_classification": _REAL_CLASS,
        "release_scope": "A_P2_REAL_OUTCOME_ACCESS",
        "operation": operation,
        "input_role": manifest.get("role"),
        "input_manifest_sha256": _sha256_bytes(manifest_bytes),
        "input_sha256": manifest.get("input_sha256"),
        "identity_sidecar_sha256": identity.get("sidecar_sha256"),
        "source_registry_sha256": identity.get("source_registry_sha256"),
        "publication_family_registry_sha256": identity.get("publication_family_registry_sha256"),
        "overlap_registry_sha256": identity.get("overlap_registry_sha256"),
        "cohorts": exact_cohorts,
        "outcome_fields": [_OUTCOME_FIELD],
    }
    final = {}
    if operation == "final-evaluate":
        final = {
            "test_role": "UNTOUCHED_FINAL_TEST",
            "frozen_equation_sha256": equation_hash,
            "final_test_cohort": exact_cohorts[0],
        }
    allowed_fields = {"record_type", "record_status", "release_scope", "decision"} | set(required) | set(final)
    if set(record) != allowed_fields:
        raise PermissionError("The user-release record contains missing or contradictory fields")
    if _release_binding_errors(record, required):
        raise PermissionError("The user-release record does not match this A-P2 operation, input, and identity resolution")
    if _release_binding_errors(record, final):
        raise PermissionError("The user-release record does not bind this untouched final input and frozen equation")


def _release_binding_errors(record: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    return [key for key, value in expected.items() if record.get(key) != value]


def _release_record_is_approved(record: dict[str, Any]) -> bool:
    return (
        record.get("record_type") == "a_p2_user_release_v2"
        and record.get("record_status") == "APPROVED"
        and record.get("release_scope") == "A_P2_REAL_OUTCOME_ACCESS"
    )


def _preflight_manifest(
    manifest_path: Path, operation: str, allow_outcomes: bool,
) -> tuple[dict[str, Any], bytes, Path, str, str, Path]:
    guarded_manifest = _guard_external_path(manifest_path, "input manifest")
    manifest, manifest_bytes = _read_json(guarded_manifest, "input manifest")
    input_path, classification, input_digest = _validate_manifest_shape(guarded_manifest, manifest, operation)
    _check_imvigor_barrier(manifest, operation, classification)
    if classification == _REAL_CLASS and not allow_outcomes:
        raise PermissionError("Real A-P2 outcome access is disabled; explicit --allow-outcomes is required")
    identity_path = _identity_path(guarded_manifest, manifest)
    if classification == _SYNTHETIC_CLASS:
        _synthetic_authorization(manifest)
    else:
        provenance = manifest.get("provenance")
        if not isinstance(provenance, dict) or provenance.get("kind") != "source_derived":
            raise PermissionError("Real A-P2 input requires source-derived provenance")
        source_hashes = provenance.get("source_object_sha256")
        if not isinstance(source_hashes, list) or not source_hashes or any(
            not isinstance(value, str) or not _HEX_256.fullmatch(value) for value in source_hashes
        ):
            raise PermissionError("Real A-P2 input requires exact source-object hashes")
        _validate_identity_provenance(manifest)
    return manifest, manifest_bytes, input_path, classification, input_digest, identity_path


def _authorize(
    manifest_path: Path, operation: str, release_record_path: Path | None,
    equation_hash: str | None, allow_outcomes: bool = False,
    preloaded: tuple[dict[str, Any], bytes, Path, str, str, Path] | None = None,
) -> tuple[dict[str, Any], bytes, Path, str, str, Path, bool]:
    loaded = preloaded or _preflight_manifest(manifest_path, operation, allow_outcomes)
    manifest, manifest_bytes, input_path, classification, input_digest, identity_path = loaded
    if classification == _SYNTHETIC_CLASS:
        if release_record_path is not None:
            raise ProductError("Synthetic fixtures use fixture provenance and cannot be real user-release records")
        if any(cohort.casefold().replace("_", "").replace("-", "") == "imvigor210" for cohort in _cohort_ids(manifest)):
            raise PermissionError("Synthetic authorization cannot open the IMvigor210 final-test barrier")
        _validate_identity_provenance(manifest)
        protected_release = False
    else:
        _authorize_real(manifest, manifest_bytes, operation, release_record_path, equation_hash)
        protected_release = operation == "final-evaluate"
    return (*loaded, protected_release)


def _read_verified_bytes(path: Path, expected_digest: str, label: str, *, allow_protected: bool = False) -> bytes:
    guarded = _guard_external_path(path, label, allow_protected=allow_protected)
    if not guarded.is_file():
        if label == "input table":
            raise ProductError("Authorized A-P2 input table is unavailable")
        raise ProductError(f"Authorized A-P2 {label} is unavailable")
    raw = guarded.read_bytes()
    if _sha256_bytes(raw) != expected_digest:
        if label == "input table":
            raise ProductError("A-P2 input table hash does not match its manifest")
        raise ProductError(f"A-P2 {label} hash does not match its manifest")
    return raw


def _validate_identity_sidecar(
    sidecar_bytes: bytes, payload_bytes: bytes, manifest: dict[str, Any]
) -> None:
    identity_meta = manifest["identity_provenance"]
    if _sha256_bytes(sidecar_bytes) != identity_meta["sidecar_sha256"]:
        raise ProductError("A-P2 identity sidecar hash does not match its manifest")
    try:
        sidecar = json.loads(sidecar_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProductError("A-P2 identity sidecar is invalid JSON") from error
    classification = manifest["data_classification"]
    if not isinstance(sidecar, dict) or sidecar.get("schema") != "a_p2_identity_bindings_v1":
        raise ProductError("A-P2 identity sidecar has an unsupported schema")
    if sidecar.get("data_classification") != classification:
        raise PermissionError("A-P2 identity sidecar classification does not match the input")
    sidecar_provenance = sidecar.get("provenance")
    if not isinstance(sidecar_provenance, dict):
        raise PermissionError("A-P2 identity sidecar lacks provenance")
    if classification == _SYNTHETIC_CLASS:
        fixture_id = manifest["provenance"]["fixture_id"]
        if any(sidecar_provenance.get(key) != value for key, value in {
            "kind": "generated_fixture",
            "fixture_id": fixture_id,
            "valid_as_real_identity_evidence": False,
        }.items()):
            raise PermissionError("Synthetic identity sidecar cannot authorize real identity resolution")
        status = "SYNTHETIC_FIXTURE_UNIQUE"
    else:
        if sidecar_provenance.get("kind") != "authoritative_acquisition_registry":
            raise PermissionError("Real identity sidecar is not linked to the authoritative acquisition registry")
        if any(sidecar_provenance.get(key) != identity_meta.get(key) for key in (
            "registry_identity", "source_registry_sha256",
            "publication_family_registry_sha256", "overlap_registry_sha256",
        )):
            raise PermissionError("Real identity sidecar and declared registry hashes do not match")
        status = "RESOLVED_AUTHORITATIVE"

    records = sidecar.get("records")
    if not isinstance(records, list):
        raise ProductError("A-P2 identity sidecar must contain a records list")
    identities = {}
    unique_people = set()
    for record in records:
        if not isinstance(record, dict) or any(
            not isinstance(record.get(key), str) or not record[key]
            for key in ("cohort", "patient_id", "canonical_patient_uid", "publication_family_id", "resolution_status")
        ):
            raise ProductError("A-P2 identity sidecar record is incomplete")
        key = (record["cohort"], record["patient_id"])
        if key in identities:
            raise PermissionError("A-P2 identity sidecar repeats a cohort and patient row")
        if record["canonical_patient_uid"] in unique_people:
            raise PermissionError("A-P2 canonical patient identity repeats across input rows")
        if record["resolution_status"] != status:
            raise PermissionError("A-P2 identity sidecar contains an unresolved identity")
        cohort = record["cohort"]
        if cohort not in manifest["cohorts"]:
            raise PermissionError("A-P2 identity sidecar includes an undeclared cohort")
        if record["publication_family_id"] != manifest["cohorts"][cohort]["study_family"]:
            raise PermissionError("A-P2 identity sidecar family binding conflicts with the manifest")
        if classification == _SYNTHETIC_CLASS:
            tokens = _identity_tokens(record["canonical_patient_uid"])
            if tokens & (_known_source_identity_tokens() | _PROTECTED_IDENTITY_TOKENS):
                raise PermissionError("Synthetic identity sidecar uses a known or protected identity alias")
        identities[key] = record["canonical_patient_uid"]
        unique_people.add(record["canonical_patient_uid"])

    try:
        text = io.TextIOWrapper(io.BytesIO(payload_bytes), encoding="utf-8", newline="")
        rows = csv.reader(text, delimiter="\t")
        header = next(rows)
    except (UnicodeDecodeError, StopIteration) as error:
        raise ProductError("A-P2 input table has no valid header") from error
    required = ("cohort", "patient_id")
    if len(set(header)) != len(header) or any(name not in header for name in required):
        raise ProductError("A-P2 input table must have unique cohort and patient_id columns")
    cohort_index, patient_index = (header.index(name) for name in required)
    payload_keys = []
    for row in rows:
        if len(row) != len(header):
            raise ProductError("A-P2 input row width does not match its header")
        payload_keys.append((row[cohort_index], row[patient_index]))
    if len(payload_keys) != len(set(payload_keys)):
        raise PermissionError("A-P2 input repeats a cohort and patient row")
    if set(payload_keys) != set(identities):
        raise PermissionError("A-P2 input rows do not match the authoritative identity sidecar")


def _read_authorized_input_material(
    input_path: Path, identity_path: Path, manifest: dict[str, Any], *, allow_protected: bool
) -> tuple[bytes, bytes]:
    payload_bytes = _read_verified_bytes(
        input_path, manifest["input_sha256"], "input table", allow_protected=allow_protected,
    )
    identity_bytes = _read_verified_bytes(
        identity_path, manifest["identity_provenance"]["sidecar_sha256"],
        "identity sidecar", allow_protected=allow_protected,
    )
    _validate_identity_sidecar(identity_bytes, payload_bytes, manifest)
    return payload_bytes, identity_bytes


def _feature_definitions() -> dict[str, dict[str, Any]]:
    memberships = panel_definitions(_EXPECTED_FEATURES)
    result: dict[str, dict[str, Any]] = {}
    for feature in _EXPECTED_FEATURES:
        genes = list(memberships[feature])
        membership_bytes = ("\n".join(genes) + "\n").encode("utf-8")
        result[feature] = {
            "genes": genes,
            "membership_sha256": _sha256_bytes(membership_bytes),
            "membership_hash_format": "UTF-8 gene symbols in frozen registry order, one per LF-terminated line",
            "transform": "arithmetic mean over the complete frozen membership after the cohort-declared source transform",
        }
    return result


def _expected_outputs(operation: str) -> list[str]:
    if operation == "development":
        return [
            "primary_leave_family_out.tsv", "primary_aggregates.tsv", "cohort_adaptive_aggregates.tsv",
            "primary_split_sensitivity.tsv", "cohort_adaptive_leave_family_out.tsv",
            "cohort_adaptive_split_sensitivity.tsv", "family_folds.tsv", "family_models.tsv",
            "primary_split_assignments.tsv", "primary_split_receipt.json",
            "cohort_adaptive_split_assignments.tsv", "cohort_adaptive_split_receipt.json",
        ]
    if operation == "freeze":
        return ["equation.json", "fit_diagnostics.tsv"]
    return [
        "final_metrics.tsv", "predictions.tsv", "bootstrap.tsv",
        "adaptive_external_scaling.tsv",
        "bootstrap_summary.tsv", "bootstrap_assignments.tsv", "bootstrap_receipt.json",
        "second_check_assignments.tsv", "second_check_receipt.json",
        "second_check.tsv",
    ]


def _write_product_manifest(
    out_dir: Path, operation: str, classification: str,
    manifest_sha256: str, input_sha256: str, r_manifest: dict[str, Any],
    equation_sha256: str | None = None, identity_sidecar_sha256: str | None = None,
) -> dict[str, Any]:
    output_files = sorted(
        path for path in out_dir.iterdir()
        if path.is_file() and path.name not in {"product_manifest.json"}
    )
    value: dict[str, Any] = {
        "schema": "a_p2_product_manifest_v1",
        "operation": operation,
        "data_classification": classification,
        "biological_validation": False if classification == _SYNTHETIC_CLASS else None,
        "input_manifest_sha256": manifest_sha256,
        "input_sha256": input_sha256,
        "identity_sidecar_sha256": identity_sidecar_sha256,
        "equation_sha256": equation_sha256,
        "code_provenance": _code_provenance(),
        "r_bridge_manifest_sha256": _sha256_bytes(_canonical_json(r_manifest)),
        "output_sha256": {path.name: _sha256_file(path) for path in output_files},
    }
    (out_dir / "product_manifest.json").write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return value


def _code_provenance() -> dict[str, str]:
    return {
        role: _sha256_file(path)
        for role, path in _CODE_HASH_INPUTS.items()
    }


def _prepare_output(path: Path) -> Path:
    out_dir = _guard_external_path(path, "output directory")
    if out_dir.is_symlink():
        raise ProductError("A-P2 output directory cannot be a symlink")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"A-P2 output directory is not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _snapshot_bytes(out_dir: Path, name: str, content: bytes) -> Path:
    work_dir = out_dir / ".work"
    work_dir.mkdir(parents=True, exist_ok=True)
    target = work_dir / name
    if target.exists() or target.is_symlink():
        raise FileExistsError("A-P2 verified snapshot already exists in private work storage")
    target.write_bytes(content)
    return target


def _bridge(operation: str, input_path: Path, manifest: dict[str, Any], out_dir: Path,
            equation_path: Path | None = None,
            equation_hash: str | None = None) -> tuple[dict[str, Any], dict[str, Path]]:
    inputs = {"features": input_path}
    if equation_path is not None:
        inputs["equation"] = equation_path
    cohorts = manifest["cohorts"]
    config = {
        "operation": operation,
        "data_classification": manifest["data_classification"],
        "cohorts": cohorts,
        "input_sha256": manifest["input_sha256"],
        "identity_sidecar_sha256": manifest["identity_provenance"]["sidecar_sha256"],
        "work_dir": str(out_dir / ".work"),
        "code_provenance": _code_provenance(),
        "feature_names": list(_EXPECTED_FEATURES),
        "expected_outputs": _expected_outputs(operation),
        "response_column": _OUTCOME_FIELD,
        "final_test_label": (
            "SYNTHETIC_FINAL_TEST_FIXTURE"
            if manifest["data_classification"] == _SYNTHETIC_CLASS
            else "UNTOUCHED_FINAL_TEST"
        ),
        "adaptive_final_label": (
            "SYNTHETIC_COHORT_ADAPTIVE_SENSITIVITY"
            if manifest["data_classification"] == _SYNTHETIC_CLASS
            else "EXTERNAL_OUTCOME_BLINDED_COHORT_ADAPTIVE_EVALUATION"
        ),
    }
    if equation_path is not None:
        config["equation_sha256"] = equation_hash
        config["equation_file_sha256"] = _sha256_file(equation_path)
    result = run_r(
        R_SCRIPT, inputs, config, out_dir / "r_bridge",
        retention_dir=out_dir / ".work" / "r_bridge_stages",
    )
    return result.manifest, result.outputs


def run_development(
    manifest_path: Path, out_path: Path, release_record_path: Path | None = None,
    allow_outcomes: bool = False,
) -> dict[str, Any]:
    manifest, raw, input_path, classification, input_digest, identity_path, protected_release = _authorize(
        manifest_path, "development", release_record_path, None, allow_outcomes,
    )
    payload_bytes, identity_bytes = _read_authorized_input_material(
        input_path, identity_path, manifest, allow_protected=protected_release,
    )
    out_dir = _prepare_output(out_path)
    input_snapshot = _snapshot_bytes(out_dir, "verified_input.tsv", payload_bytes)
    _snapshot_bytes(out_dir, "verified_identity_bindings.json", identity_bytes)
    r_manifest, outputs = _bridge("development", input_snapshot, manifest, out_dir)
    for name, path in outputs.items():
        shutil.copyfile(path, out_dir / name)
    return _write_product_manifest(
        out_dir, "development", classification, _sha256_bytes(raw),
        input_digest, r_manifest,
        identity_sidecar_sha256=manifest["identity_provenance"]["sidecar_sha256"],
    )


def run_freeze(
    manifest_path: Path, out_path: Path, release_record_path: Path | None = None,
    allow_outcomes: bool = False,
) -> dict[str, Any]:
    manifest, raw, input_path, classification, input_digest, identity_path, protected_release = _authorize(
        manifest_path, "freeze", release_record_path, None, allow_outcomes,
    )
    payload_bytes, identity_bytes = _read_authorized_input_material(
        input_path, identity_path, manifest, allow_protected=protected_release,
    )
    out_dir = _prepare_output(out_path)
    input_snapshot = _snapshot_bytes(out_dir, "verified_input.tsv", payload_bytes)
    _snapshot_bytes(out_dir, "verified_identity_bindings.json", identity_bytes)
    r_manifest, outputs = _bridge("freeze", input_snapshot, manifest, out_dir)
    equation, _ = _read_json(outputs["equation.json"], "R-fitted equation")
    equation["feature_definitions"] = _feature_definitions()
    equation["training_feature_transforms"] = {
        analysis_name: {
            cohort: {
                "representation": metadata["representation"],
                "feature_transform": metadata["feature_transform"],
            }
            for cohort, metadata in manifest["cohorts"].items()
            if metadata[eligibility_field]
        }
        for analysis_name, eligibility_field in (
            ("primary", "primary_eligible"),
            ("cohort_adaptive", "adaptive_eligible"),
        )
    }
    equation["schema"] = "a_p2_equation_v1"
    equation["data_classification"] = classification
    equation["training_input_manifest_sha256"] = _sha256_bytes(raw)
    equation["training_identity_provenance_sha256"] = manifest["identity_provenance"]["sidecar_sha256"]
    equation["glmnet_lock_version"] = "5.2"
    equation["code_provenance"] = _code_provenance()
    for model_name in ("primary", "cohort_adaptive"):
        model = equation.get(model_name)
        if isinstance(model, dict) and model.get("available"):
            coefficients = {"coefficients": model["coefficients"], "intercept": model["intercept"]}
            scaling = model.get("scaling") if model_name == "primary" else model.get("scaling_by_study")
            model["coefficient_sha256"] = _sha256_bytes(_canonical_json(coefficients))
            model["scaling_sha256"] = _sha256_bytes(_canonical_json(scaling))
    equation_content = dict(equation)
    equation_content.pop("equation_sha256", None)
    equation["equation_sha256"] = _sha256_bytes(_canonical_json(equation_content))
    equation_path = out_dir / "equation.json"
    equation_path.write_text(json.dumps(equation, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    shutil.copyfile(outputs["fit_diagnostics.tsv"], out_dir / "fit_diagnostics.tsv")
    return _write_product_manifest(
        out_dir, "freeze", classification, _sha256_bytes(raw), input_digest,
        r_manifest, equation["equation_sha256"],
        identity_sidecar_sha256=manifest["identity_provenance"]["sidecar_sha256"],
    )


def run_final_evaluation(
    manifest_path: Path, equation_path: Path, out_path: Path,
    release_record_path: Path | None = None, allow_outcomes: bool = False,
) -> dict[str, Any]:
    preloaded = _preflight_manifest(manifest_path, "final-evaluate", allow_outcomes)
    equation_path = _guard_external_path(equation_path, "frozen equation")
    equation, equation_hash, equation_bytes = _verify_equation(equation_path)
    manifest, raw, input_path, classification, input_digest, identity_path, protected_release = _authorize(
        manifest_path, "final-evaluate", release_record_path, equation_hash,
        allow_outcomes, preloaded=preloaded,
    )
    final_families = {metadata["study_family"] for metadata in manifest["cohorts"].values()}
    trained_families = set(equation.get("primary_training_cohort_families", [])) | set(
        equation.get("adaptive_training_cohort_families", [])
    )
    if final_families & trained_families:
        raise PermissionError("Final test family overlaps the frozen development equation")
    if equation.get("data_classification") != classification:
        raise PermissionError("Final input and frozen equation classifications do not match")
    if equation.get("status") != "AVAILABLE_SYNTHETIC_SOFTWARE_ONLY" and classification == _SYNTHETIC_CLASS:
        raise ProductError("Synthetic final evaluation requires an available synthetic equation")
    if classification == _REAL_CLASS and equation.get("status") != "AVAILABLE_REAL_RELEASED_FIT":
        raise PermissionError("A real final evaluation requires a released real development equation")
    payload_bytes, identity_bytes = _read_authorized_input_material(
        input_path, identity_path, manifest, allow_protected=protected_release,
    )
    out_dir = _prepare_output(out_path)
    input_snapshot = _snapshot_bytes(out_dir, "verified_input.tsv", payload_bytes)
    _snapshot_bytes(out_dir, "verified_identity_bindings.json", identity_bytes)
    equation_snapshot = _snapshot_bytes(out_dir, "verified_equation.json", equation_bytes)
    r_manifest, outputs = _bridge(
        "final-evaluate", input_snapshot, manifest, out_dir, equation_snapshot,
        equation_hash=equation_hash,
    )
    for name, path in outputs.items():
        shutil.copyfile(path, out_dir / name)
    return _write_product_manifest(
        out_dir, "final-evaluate", classification, _sha256_bytes(raw),
        input_digest, r_manifest, equation_hash,
        identity_sidecar_sha256=manifest["identity_provenance"]["sidecar_sha256"],
    )
