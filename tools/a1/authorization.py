"""A-LONG path boundaries and exact user-release bindings."""
from __future__ import annotations

import hashlib
import json
import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
DECISIONS_DIR = ROOT / "docs" / "decisions"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PACKET_TOKEN = "ingestionpacketjson"
_PROTECTED_TOKEN = "imvigor210"
_SCOPE_OPERATIONS = {
    "N12_PAIRING": "pair",
    "N12_GIDE_CROSSWALK": "accept_gide_crosswalk",
    "N13_FEATURE_JOIN": "pair_to_analysis",
    "N13_TWO_TIMEPOINT": "fit_two_timepoint",
    "N13_REPEATED": "fit_repeated_windows",
    "N13_RANDOMIZED_ARM": "fit_randomized_arm",
    "N13_SYNTHESIS": "synthesize_effects",
}
_OUTCOME_SCOPES = frozenset({
    "N13_FEATURE_JOIN", "N13_TWO_TIMEPOINT", "N13_REPEATED",
    "N13_RANDOMIZED_ARM", "N13_SYNTHESIS",
})
_SCOPE_BINDINGS = {
    "N12_PAIRING": frozenset({"source_column_map_sha256", "window_policy_sha256"}),
    "N12_GIDE_CROSSWALK": frozenset({"crosswalk_sha256", "crosswalk_source_manifest_sha256"}),
    "N13_FEATURE_JOIN": frozenset({"feature_membership_sha256", "pair_manifest_sha256", "representation_sha256"}),
    "N13_TWO_TIMEPOINT": frozenset({"ancova_method_id", "covariate_contract_sha256", "delta_method_id"}),
    "N13_REPEATED": frozenset({"repeated_method_id", "selection_mode", "window_set_sha256"}),
    "N13_RANDOMIZED_ARM": frozenset({"comparative_estimand_id", "randomization_receipt_sha256", "randomized_method_id"}),
    "N13_SYNTHESIS": frozenset({"meta_method_id", "multiplicity_contract_sha256", "source_overlap_contract_sha256"}),
}
_SCOPE_SOURCES = {
    "N12_PAIRING": frozenset({"specimens"}),
    "N13_FEATURE_JOIN": frozenset({"pairs", "expression", "endpoint"}),
    "N13_TWO_TIMEPOINT": frozenset({"design"}),
    "N13_REPEATED": frozenset({"design"}),
    "N13_RANDOMIZED_ARM": frozenset({"design"}),
    "N13_SYNTHESIS": frozenset({"effects", "overlap_receipts"}),
}
_HASH_SCOPE_BINDINGS = {
    "N12_PAIRING": frozenset({"source_column_map_sha256", "window_policy_sha256"}),
    "N12_GIDE_CROSSWALK": frozenset({"crosswalk_sha256", "crosswalk_source_manifest_sha256"}),
    "N13_FEATURE_JOIN": frozenset({"feature_membership_sha256", "pair_manifest_sha256", "representation_sha256"}),
    "N13_TWO_TIMEPOINT": frozenset({"covariate_contract_sha256"}),
    "N13_REPEATED": frozenset({"window_set_sha256"}),
    "N13_RANDOMIZED_ARM": frozenset({"randomization_receipt_sha256"}),
    "N13_SYNTHESIS": frozenset({"multiplicity_contract_sha256", "source_overlap_contract_sha256"}),
}
_RELEASE_TOKEN = object()
_TABLES_TOKEN = object()


@dataclass(frozen=True)
class AuthorizedRelease:
    record: dict
    record_sha256: str
    record_path: Path
    decision_path: str
    decision_sha256: str
    root: Path
    decisions_dir: Path
    source_sha256: dict[str, str]
    _token: object


@dataclass(frozen=True)
class ReleasedInputs:
    authorization: AuthorizedRelease
    manifest_path: Path
    manifest_sha256: str
    manifest: dict
    source_paths: dict[str, Path]
    tables: dict[str, list[dict[str, str]]]
    tables_sha256: str
    _token: object


def is_authorized_release(value, *, release_scope: str, operation: str) -> bool:
    return (
        isinstance(value, AuthorizedRelease)
        and value._token is _RELEASE_TOKEN
        and value.record.get("release_scope") == release_scope
        and value.record.get("operation") == operation
    )


def guard_path(path: Path | str, label: str) -> Path:
    """Resolve an A-LONG path only after rejecting protected and aliased paths."""
    original = Path(path).expanduser()
    if not original.is_absolute():
        original = Path.cwd() / original

    current = Path(original.anchor)
    for component in original.parts[1:]:
        if component in {"", "."}:
            continue
        current = current / component
        try:
            is_symlink = current.is_symlink()
        except OSError as error:
            raise PermissionError(f"A-LONG {label} path cannot be inspected") from error
        if is_symlink:
            raise PermissionError(f"A-LONG {label} path has symlink ancestry")

    try:
        resolved = original.resolve(strict=False)
    except OSError as error:
        raise PermissionError(f"A-LONG {label} path cannot be resolved") from error
    for component in (*original.parts, *resolved.parts):
        token = _path_token(component)
        if _PACKET_TOKEN in token:
            raise PermissionError("A-LONG never reads ingestion_packet.json")
        if _PROTECTED_TOKEN in token:
            raise PermissionError("A-LONG always refuses IMvigor210 paths")
    return resolved


def check_path_separation(
    *,
    inputs: Mapping[str, Path | str],
    outputs: Mapping[str, Path | str],
) -> tuple[dict[str, Path], dict[str, Path]]:
    """Guard every named path before checking aliases or directory overlap."""
    guarded_inputs = {name: guard_path(path, f"{name} input") for name, path in inputs.items()}
    guarded_outputs = {name: guard_path(path, f"{name} output") for name, path in outputs.items()}
    all_outputs = tuple(guarded_outputs.items())
    for input_name, input_path in guarded_inputs.items():
        for output_name, output_path in all_outputs:
            if _paths_overlap(input_path, output_path):
                raise ValueError(
                    f"A-LONG input/output path overlap between {input_name} and {output_name}"
                )
    for index, (left_name, left_path) in enumerate(all_outputs):
        for right_name, right_path in all_outputs[index + 1:]:
            if _paths_overlap(left_path, right_path):
                raise ValueError(
                    f"A-LONG output paths overlap between {left_name} and {right_name}"
                )
    return guarded_inputs, guarded_outputs


def prepare_output_directory(
    path: Path | str,
    *,
    private_root: Path | str | None = None,
) -> Path:
    """Create only an empty, symlink-free A-LONG output directory."""
    output = validate_output_directory(path, private_root=private_root)
    output.mkdir(parents=True, exist_ok=True)
    return output


def validate_output_directory(
    path: Path | str,
    *,
    private_root: Path | str | None = None,
) -> Path:
    """Check an output target without creating or modifying it."""
    output = guard_path(path, "output directory")
    if private_root is not None:
        root = guard_path(private_root, "private output root")
        try:
            output.relative_to(root)
        except ValueError as error:
            raise PermissionError("A-LONG patient-level output must stay under results/ or .scratch/") from error
    if output.is_symlink():
        raise PermissionError("A-LONG output directory cannot be a symlink")
    if output.exists():
        if not output.is_dir():
            raise FileExistsError("A-LONG output path is not a directory")
        if any(output.iterdir()):
            raise FileExistsError("A-LONG output directory is not empty")
    return output


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path | str, *, label: str = "input file") -> str:
    guarded = guard_path(path, label)
    try:
        digest = hashlib.sha256()
        with guarded.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise PermissionError(f"A-LONG {label} is unavailable") from error
    return digest.hexdigest()


def validate_user_release(
    record_path: Path | str,
    *,
    release_scope: str,
    operation: str,
    policy_sha256: str,
    input_manifest_sha256: str,
    source_paths: Mapping[str, Path | str],
    cohorts: tuple[str, ...] | list[str],
    permitted_fields: tuple[str, ...] | list[str],
    root: Path | str | None = None,
    decisions_dir: Path | str | None = None,
    extra_bindings: Mapping[str, object] | None = None,
    allow_outcomes: bool = False,
) -> dict:
    """Authorize scope first, then hash only the named source files bound by it."""
    required_scope_bindings = _SCOPE_BINDINGS.get(release_scope)
    if required_scope_bindings is None:
        raise PermissionError("A-LONG release scope is not recognized")
    if not isinstance(extra_bindings, Mapping) or set(extra_bindings) != required_scope_bindings:
        raise PermissionError("A-LONG release is missing exact scope-specific contract bindings")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in extra_bindings.values()
    ):
        raise PermissionError("A-LONG scope-specific release bindings must be non-empty")
    for name in _HASH_SCOPE_BINDINGS[release_scope]:
        if not _SHA256.fullmatch(extra_bindings[name]):
            raise PermissionError("A-LONG scope-specific hash bindings must be lowercase SHA256 values")
    if release_scope == "N13_REPEATED" and extra_bindings["selection_mode"] not in {
        "complete_declared_windows", "available_observations",
    }:
        raise PermissionError("A-LONG repeated release must bind a supported declared selection mode")
    if not cohorts or len(set(cohorts)) != len(cohorts) or any(not str(value).strip() for value in cohorts):
        raise PermissionError("A-LONG release cohort set must be explicit and unique")
    if not permitted_fields or len(set(permitted_fields)) != len(permitted_fields) or any(not str(value).strip() for value in permitted_fields):
        raise PermissionError("A-LONG release permitted fields must be explicit and unique")
    if any(_PROTECTED_TOKEN in _path_token(cohort) for cohort in cohorts):
        raise PermissionError("A-LONG always refuses the protected IMvigor210 cohort")
    if release_scope in _OUTCOME_SCOPES and allow_outcomes is not True:
        raise PermissionError("A-LONG real outcome access requires allow_outcomes=True")
    record_file = guard_path(record_path, "user-release record")
    if not source_paths or any(not isinstance(name, str) or not name.strip() for name in source_paths):
        raise PermissionError("A-LONG release needs explicit named source inputs")
    guarded_sources = {
        name: guard_path(path, f"released {name} source")
        for name, path in source_paths.items()
    }
    repo_root = guard_path(root or ROOT, "decision root")
    decision_root = guard_path(decisions_dir or DECISIONS_DIR, "decision directory")
    try:
        raw = record_file.read_bytes()
        record = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermissionError("A-LONG user-release record path is unavailable or malformed") from error
    if not isinstance(record, dict):
        raise PermissionError("A-LONG user-release record must be a JSON object")
    if (
        record.get("record_type") != "a_long_user_release_v1"
        or record.get("record_status") != "APPROVED"
        or record.get("data_classification") != "PRIVATE_PATIENT_LEVEL"
        or record.get("release_scope") != release_scope
    ):
        raise PermissionError("A-LONG user-release record is not approved for this scope")
    if _SCOPE_OPERATIONS.get(release_scope) != operation:
        raise PermissionError("A-LONG release scope is not bound to this operation")

    decision = record.get("decision")
    if not isinstance(decision, dict) or set(decision) != {"identity", "path", "sha256"}:
        raise PermissionError("A-LONG release record needs one exact docs/decisions decision reference")
    identity = decision.get("identity")
    decision_rel = decision.get("path")
    decision_hash = decision.get("sha256")
    if (
        not isinstance(identity, str)
        or not identity
        or not isinstance(decision_rel, str)
        or not decision_rel.startswith("docs/decisions/")
        or not isinstance(decision_hash, str)
        or not _SHA256.fullmatch(decision_hash)
    ):
        raise PermissionError("A-LONG decision identity, scoped path, or SHA256 is invalid")
    decision_file = guard_path(repo_root / decision_rel, "decision record")
    try:
        decision_file.relative_to(decision_root)
    except ValueError as error:
        raise PermissionError("A-LONG decision path is outside docs/decisions") from error
    if decision_file.stem != identity or sha256_file(decision_file, label="decision record") != decision_hash:
        raise PermissionError("A-LONG decision identity or hash does not match")

    raw_source_hashes = record.get("source_sha256")
    if not isinstance(raw_source_hashes, dict) or set(raw_source_hashes) != set(source_paths):
        raise PermissionError("A-LONG user-release source names do not match the requested inputs")
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in raw_source_hashes.values()):
        raise PermissionError("A-LONG user-release source hashes must be lowercase SHA256 values")
    expected = {
        "operation": operation,
        "policy_sha256": policy_sha256,
        "input_manifest_sha256": input_manifest_sha256,
        "source_sha256": dict(sorted(raw_source_hashes.items())),
        "cohorts": sorted(set(cohorts)),
        "permitted_fields": sorted(set(permitted_fields)),
        **dict(extra_bindings),
    }
    allowed = {
        "record_type", "record_status", "data_classification", "release_scope", "decision",
        *expected.keys(),
    }
    if set(record) != allowed:
        raise PermissionError("A-LONG user-release record has missing or contradictory fields")
    if any(record.get(key) != value for key, value in expected.items()):
        raise PermissionError("A-LONG user-release record does not match this operation, policy, input, and scope")
    actual_hashes = {name: sha256_file(path, label=f"released {name} source") for name, path in guarded_sources.items()}
    if actual_hashes != dict(sorted(raw_source_hashes.items())):
        raise PermissionError("A-LONG released source hash does not match the approved user record")
    return AuthorizedRelease(
        record=record,
        record_sha256=hashlib.sha256(raw).hexdigest(),
        record_path=record_file,
        decision_path=decision_rel,
        decision_sha256=decision_hash,
        root=repo_root,
        decisions_dir=decision_root,
        source_sha256=actual_hashes,
        _token=_RELEASE_TOKEN,
    )


def read_released_inputs(
    manifest_path: Path | str,
    record_path: Path | str,
    *,
    release_scope: str,
    operation: str,
    policy_sha256: str,
    expected_scope_bindings: Mapping[str, object] | None = None,
    output_paths: Mapping[str, Path | str] | None = None,
    root: Path | str | None = None,
    decisions_dir: Path | str | None = None,
    allow_outcomes: bool = False,
) -> ReleasedInputs:
    """Validate a real release before hashing or reading named clinical fields."""
    guarded_manifest = guard_path(manifest_path, "release input manifest")
    guarded_record = guard_path(record_path, "user-release record")
    if _paths_overlap(guarded_manifest, guarded_record):
        raise ValueError("A-LONG release manifest and user record paths overlap")
    try:
        manifest_bytes = guarded_manifest.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermissionError("A-LONG release input manifest is unavailable or malformed") from error
    required_manifest_keys = {
        "schema", "data_classification", "cohort_ids", "source_files",
        "field_maps", "identity_fields", "permitted_fields", "scope_bindings",
    }
    if not isinstance(manifest, dict) or set(manifest) != required_manifest_keys:
        raise PermissionError("A-LONG release input manifest has missing or contradictory fields")
    if (
        manifest.get("schema") != "a_long_release_input_manifest_v1"
        or manifest.get("data_classification") != "PRIVATE_PATIENT_LEVEL"
    ):
        raise PermissionError("A-LONG released input must use the private real-input schema")
    if expected_scope_bindings is not None:
        declared_bindings = manifest.get("scope_bindings")
        if (
            not isinstance(declared_bindings, dict)
            or not set(expected_scope_bindings) <= set(declared_bindings)
            or any(declared_bindings.get(name) != value for name, value in expected_scope_bindings.items())
        ):
            raise PermissionError("A-LONG release manifest scope bindings differ from the selected route policy")
    cohorts = manifest.get("cohort_ids")
    if not isinstance(cohorts, list) or not cohorts or any(not isinstance(value, str) or not value.strip() for value in cohorts):
        raise PermissionError("A-LONG release manifest must name its exact cohort set")
    if len(set(cohorts)) != len(cohorts) or any(_PROTECTED_TOKEN in _path_token(value) for value in cohorts):
        raise PermissionError("A-LONG release manifest names a duplicate or protected cohort")
    if release_scope in _OUTCOME_SCOPES and allow_outcomes is not True:
        raise PermissionError("A-LONG real outcome access requires allow_outcomes=True")
    sources = manifest.get("source_files")
    field_maps = manifest.get("field_maps")
    identity_fields = manifest.get("identity_fields")
    if (
        not isinstance(sources, dict) or not sources
        or not isinstance(field_maps, dict)
        or not isinstance(identity_fields, dict)
        or set(sources) != set(field_maps)
        or set(sources) != set(identity_fields)
    ):
        raise PermissionError("A-LONG release manifest source, field-map, and identity roles must match")
    expected_sources = _SCOPE_SOURCES.get(release_scope)
    if expected_sources is None or set(sources) != expected_sources:
        raise PermissionError("A-LONG release source roles do not match the selected operation scope")
    permitted = manifest.get("permitted_fields")
    if not isinstance(permitted, list) or len(set(permitted)) != len(permitted):
        raise PermissionError("A-LONG released named-field allowlist is malformed")
    permitted_by_source: dict[str, set[str]] = {name: set() for name in sources}
    for item in permitted:
        if not isinstance(item, str) or item.count(":") != 1:
            raise PermissionError("A-LONG permitted fields must use exact source:column names")
        source_name, field_name = item.split(":", 1)
        if source_name not in permitted_by_source or not field_name:
            raise PermissionError("A-LONG permitted field names an unknown source or empty column")
        permitted_by_source[source_name].add(field_name)

    source_paths: dict[str, Path] = {}
    for source_name, raw_path in sources.items():
        if not isinstance(source_name, str) or not source_name or not isinstance(raw_path, str) or not raw_path:
            raise PermissionError("A-LONG release source names and paths must be explicit")
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = guarded_manifest.parent / candidate
        source_paths[source_name] = guard_path(candidate, f"released {source_name} source")
    all_inputs = [guarded_manifest, guarded_record, *source_paths.values()]
    for index, left in enumerate(all_inputs):
        for right in all_inputs[index + 1:]:
            if _paths_overlap(left, right):
                raise ValueError("A-LONG release input paths overlap")
    if output_paths is not None:
        check_path_separation(
            inputs={
                "release manifest": guarded_manifest,
                "user-release record": guarded_record,
                **{f"released {name}": path for name, path in source_paths.items()},
            },
            outputs=output_paths,
        )

    for source_name in sources:
        mapping = field_maps[source_name]
        identity = identity_fields[source_name]
        if (
            not isinstance(mapping, dict) or not mapping
            or any(not isinstance(key, str) or not key or not isinstance(value, str) or not value for key, value in mapping.items())
            or len(set(mapping.values())) != len(mapping)
            or not isinstance(identity, list) or not identity
            or len(set(identity)) != len(identity)
            or any(not isinstance(value, str) or not value for value in identity)
        ):
            raise PermissionError("A-LONG source field maps and identity columns must be explicit and unique")
        mapped_columns = set(mapping.values())
        if not mapped_columns <= permitted_by_source[source_name] or not set(identity) <= permitted_by_source[source_name]:
            raise PermissionError("A-LONG source map requests a field outside the user-authorized named-field set")
        if release_scope == "N13_FEATURE_JOIN" and source_name == "endpoint":
            if not {"endpoint_id", "response"} <= set(mapping):
                raise PermissionError("N13 feature join must bind an explicit endpoint ID and response column")
        if release_scope == "N13_SYNTHESIS" and source_name == "overlap_receipts":
            identity_roles = ("study_a", "study_b", "source_family_a", "source_family_b")
            if any(mapping.get(name) not in identity for name in identity_roles):
                raise PermissionError("Synthesis overlap identity must name both studies and both source families")
        else:
            study_column = mapping.get("study_id") or mapping.get("study")
            if not study_column or study_column not in identity:
                raise PermissionError("A-LONG identity preflight must name the study field first")
            if release_scope == "N13_FEATURE_JOIN" and source_name == "expression":
                identity_name = mapping.get("sample_id")
            elif release_scope == "N13_SYNTHESIS" and source_name == "effects":
                identity_name = mapping.get("source_family_id")
            else:
                identity_name = next(
                    (mapping.get(name) for name in ("patient_id", "patient_key", "subject_id") if mapping.get(name)),
                    None,
                )
            if identity_name not in identity:
                raise PermissionError("A-LONG identity preflight must name the authorized opaque entity field")

    authorization = validate_user_release(
        guarded_record,
        release_scope=release_scope,
        operation=operation,
        policy_sha256=policy_sha256,
        input_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        source_paths=source_paths,
        cohorts=cohorts,
        permitted_fields=permitted,
        root=root,
        decisions_dir=decisions_dir,
        extra_bindings=manifest["scope_bindings"],
        allow_outcomes=allow_outcomes,
    )

    tables: dict[str, list[dict[str, str]]] = {}
    for source_name, path in source_paths.items():
        mapping = field_maps[source_name]
        identity_columns = tuple(identity_fields[source_name])
        identity_rows = _read_named_tsv(path, identity_columns, label=f"{source_name} identity fields")
        if release_scope == "N13_SYNTHESIS" and source_name == "overlap_receipts":
            study_columns = (mapping["study_a"], mapping["study_b"])
            entity_columns = (mapping["source_family_a"], mapping["source_family_b"])
            if any(
                row.get(column, "") not in cohorts
                for row in identity_rows for column in study_columns
            ):
                raise PermissionError("Synthesis overlap receipt study identities exceed the released cohort set")
            if any(not row.get(column, "") for row in identity_rows for column in (*study_columns, *entity_columns)):
                raise PermissionError("Synthesis overlap receipt identity fields contain an empty value")
        else:
            study_column = mapping.get("study_id") or mapping.get("study")
            if any(row.get(study_column, "") not in cohorts for row in identity_rows):
                raise PermissionError("A-LONG source identity rows do not match the released cohort set")
            entity_column = (
                mapping.get("sample_id") if release_scope == "N13_FEATURE_JOIN" and source_name == "expression"
                else mapping.get("source_family_id") if release_scope == "N13_SYNTHESIS" and source_name == "effects"
                else next(mapping[name] for name in ("patient_id", "patient_key", "subject_id") if mapping.get(name))
            )
            if any(not row.get(entity_column, "") for row in identity_rows):
                raise PermissionError("A-LONG source entity identity fields contain an empty value")
        if any(not row.get(column, "") for row in identity_rows for column in identity_columns):
            raise PermissionError("A-LONG source identity fields contain an empty value")
        selected_columns = tuple(sorted(permitted_by_source[source_name]))
        source_rows = _read_named_tsv(path, selected_columns, label=f"{source_name} authorized fields")
        reverse_map = {source: canonical for canonical, source in mapping.items()}
        tables[source_name] = [
            {reverse_map[column]: row[column] for column in selected_columns if column in reverse_map}
            for row in source_rows
        ]
    tables_digest = hashlib.sha256(
        json.dumps(tables, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return ReleasedInputs(
        authorization=authorization,
        manifest_path=guarded_manifest,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        manifest=manifest,
        source_paths=source_paths,
        tables=tables,
        tables_sha256=tables_digest,
        _token=_TABLES_TOKEN,
    )


def is_released_inputs(value, *, release_scope: str, operation: str) -> bool:
    if (
        not isinstance(value, ReleasedInputs)
        or value._token is not _TABLES_TOKEN
        or not is_authorized_release(
            value.authorization, release_scope=release_scope, operation=operation
        )
    ):
        return False
    current = hashlib.sha256(
        json.dumps(value.tables, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return current == value.tables_sha256


def _read_named_tsv(path: Path, columns: tuple[str, ...], *, label: str) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream, delimiter="\t")
            header = next(reader)
            if len(header) != len(set(header)) or any(column not in header for column in columns):
                raise PermissionError(f"A-LONG {label} columns are missing or ambiguous")
            indexes = {column: header.index(column) for column in columns}
            rows = []
            for line_number, values in enumerate(reader, start=2):
                if len(values) != len(header):
                    raise PermissionError(f"A-LONG {label} has a malformed row at line {line_number}")
                rows.append({column: values[index].strip() for column, index in indexes.items()})
    except StopIteration:
        raise PermissionError(f"A-LONG {label} source is empty") from None
    except OSError as error:
        raise PermissionError(f"A-LONG {label} source is unavailable") from error
    return rows


def _path_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents
