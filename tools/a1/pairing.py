"""Outcome-free, source-policy-driven specimen pairing for A-LONG."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from tools.a1.authorization import (
    check_path_separation,
    guard_path,
    is_authorized_release,
    prepare_output_directory,
)
from tools.a_meta.provenance import (
    canonical_sha256,
    file_sha256,
    is_locked_study,
    known_cohort_ids,
    write_synthetic_fixture_manifest,
)


CANONICAL_COLUMNS = (
    "study_id", "patient_id", "specimen_id", "assay_id", "timepoint_category",
    "collection_day", "day_precision", "index_episode", "exposure", "baseline_source",
    "prior_treatment", "disease_state", "regimen_state", "compartment", "platform",
    "unit", "assay_method", "assay_qualified", "lesion_id", "source_locator",
    "source_confidence", "day_origin", "annotation_id", "measurement_comparability_id",
    "endpoint_id", "admission_receipt",
)
_REQUIRED_NONEMPTY = (
    "study_id", "patient_id", "specimen_id", "assay_id", "timepoint_category",
    "index_episode", "exposure", "compartment", "platform", "unit", "assay_method",
)
_REQUIRED_REAL_PROVENANCE = (
    "source_locator", "source_confidence", "day_origin", "annotation_id",
    "measurement_comparability_id", "endpoint_id", "admission_receipt",
)
_QUALIFIED = {"yes", "true", "qualified"}
_EXACT_PRECISION = {"exact", "day", "days"}
_MANIFEST_PRODUCER = "tools.a_meta.synthetic_fixture"


@dataclass(frozen=True)
class WindowRule:
    window_id: str
    role: str
    categories: tuple[str, ...]
    day_interval: tuple[float, float] | None = None
    day_origin: str | None = None
    target_day: float | None = None
    transition_contrast_id: str | None = None
    allowed_window_disease_states: tuple[str, ...] = ()
    allowed_window_regimen_states: tuple[str, ...] = ()


@dataclass(frozen=True)
class PairingPolicy:
    study_id: str
    status: str
    decision_ref: str | None
    baseline_window: str
    windows: tuple[WindowRule, ...]
    baseline_hierarchy: tuple[str, ...]
    allowed_prior_treatment: tuple[str, ...]
    allowed_disease_states: tuple[str, ...]
    allowed_regimen_states: tuple[str, ...]
    prefer_same_lesion: bool
    allow_different_lesion: bool = False
    endpoint_id: str | None = None
    admission_receipt: str | None = None
    source_family_id: str | None = None
    overlap_receipt_id: str | None = None
    overlap_status: str | None = None


@dataclass(frozen=True)
class PolicyAcceptance:
    decision_id: str
    record_ref: str
    fixture_only: bool = False
    authorization: object | None = None


@dataclass(frozen=True)
class CrosswalkAcceptance:
    mapping: Mapping[str, str]
    record_ref: str
    fixture_only: bool = False
    authorization: object | None = None


@dataclass(frozen=True)
class SourceColumns:
    study_id: str
    patient_id: str
    specimen_id: str
    assay_id: str
    timepoint_category: str
    index_episode: str
    exposure: str
    baseline_source: str
    prior_treatment: str
    disease_state: str
    regimen_state: str
    compartment: str
    platform: str
    unit: str
    assay_method: str
    assay_qualified: str
    collection_day: str | None = None
    day_precision: str | None = None
    lesion_id: str | None = None
    source_locator: str | None = None
    source_confidence: str | None = None
    day_origin: str | None = None
    annotation_id: str | None = None
    measurement_comparability_id: str | None = None
    endpoint_id: str | None = None
    admission_receipt: str | None = None

    def mapping(self) -> dict[str, str]:
        result = {
            name: getattr(self, name)
            for name in CANONICAL_COLUMNS
            if getattr(self, name) is not None
        }
        source_names = list(result.values())
        if any(not isinstance(value, str) or not value.strip() for value in source_names):
            raise ValueError("Every selected source column must have an explicit name")
        if len(source_names) != len(set(source_names)):
            raise ValueError("Source column mappings must be one-to-one")
        missing = set(_REQUIRED_NONEMPTY) - result.keys()
        if missing:
            raise ValueError("Missing explicit source mappings: " + ", ".join(sorted(missing)))
        return result


@dataclass
class PairingResult:
    candidates: list[dict]
    exclusions: list[dict]
    missing_followups: list[dict]
    summary: dict
    policy_status: str
    data_classification: str


def validate_real_source_columns(mapping: Mapping[str, str]) -> None:
    """Require the complete named provenance map at every real pairing boundary."""
    if not isinstance(mapping, Mapping) or not set(_REQUIRED_REAL_PROVENANCE) <= mapping.keys():
        raise ValueError("Real pairing requires explicitly named source, annotation, comparability, endpoint, and admission fields")
    if any(not isinstance(mapping[name], str) or not mapping[name].strip() for name in _REQUIRED_REAL_PROVENANCE):
        raise ValueError("Real pairing provenance source columns must be named and non-empty")


def write_synthetic_pair_manifest(
    input_path: Path | str,
    manifest_path: Path | str,
    *,
    study_id: str,
) -> dict:
    """Create explicit, hash-matched provenance for invented specimen input."""
    _guard_study_id(study_id, "synthetic")
    inputs, outputs = check_path_separation(
        inputs={"specimen table": input_path},
        outputs={"fixture manifest": manifest_path},
    )
    input_path = inputs["specimen table"]
    manifest_path = outputs["fixture manifest"]
    if not input_path.is_file():
        raise ValueError("Synthetic specimen input is unavailable")
    if manifest_path.exists():
        raise FileExistsError("Synthetic specimen manifest output already exists")
    return write_synthetic_fixture_manifest(
        manifest_path,
        kind="a_long_specimen_input",
        payload_sha256=file_sha256(input_path),
        cohort_ids=(study_id,),
        output_path=input_path,
    )


def read_specimens(
    path: Path | str,
    *,
    columns: SourceColumns,
    study_id: str,
    classification: str,
    provenance_manifest: Path | str | None = None,
    release_authorization=None,
) -> list[dict[str, str]]:
    """Read only the named outcome-free columns from a source table.

    The classification and protected-study checks run before opening the input.
    Synthetic tables require the project fixture manifest and matching file hash.
    Extra source columns are ignored; they are never copied into returned rows.
    """
    _guard_study_id(study_id, classification)
    mapping = columns.mapping()
    if classification == "real":
        validate_real_source_columns(mapping)
    input_paths = {"specimen table": path}
    if provenance_manifest is not None:
        input_paths["provenance manifest"] = provenance_manifest
    guarded, _ = check_path_separation(inputs=input_paths, outputs={})
    path = guarded["specimen table"]
    if classification == "synthetic":
        _verify_synthetic_input(path, guarded["provenance manifest"], study_id)
    elif classification == "real":
        validate_real_source_columns(mapping)
        if not is_authorized_release(
            release_authorization, release_scope="N12_PAIRING", operation="pair"
        ):
            raise PermissionError("Real pairing requires an approved scoped N12 user-release record")
        if file_sha256(path) not in release_authorization.source_sha256.values():
            raise PermissionError("Real pairing source hash is not bound by the N12 release record")
        if not set(mapping.values()) <= set(release_authorization.record.get("permitted_fields", ())):
            raise PermissionError("Real pairing source columns exceed the N12 named-field release")
        if not re.fullmatch(r"[0-9a-f]{64}", str(release_authorization.record.get("window_policy_sha256", ""))):
            raise PermissionError("Real pairing user-release lacks the exact source-window policy hash")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Specimen input is empty") from None
        if len(header) != len(set(header)):
            raise ValueError("Specimen input has duplicate column names")
        positions = {}
        for canonical, source_name in mapping.items():
            if source_name not in header:
                raise ValueError(f"Required source column is missing: {source_name}")
            positions[canonical] = header.index(source_name)
        rows = []
        for line_number, values in enumerate(reader, start=2):
            if len(values) != len(header):
                raise ValueError(f"Malformed specimen row at line {line_number}")
            row = {name: values[index].strip() for name, index in positions.items()}
            for optional in set(CANONICAL_COLUMNS) - row.keys():
                row[optional] = ""
            if row["study_id"] != study_id:
                raise ValueError("Specimen row study ID does not match the declared study")
            if classification == "real":
                required_values = {
                    "source_locator", "source_confidence", "day_origin", "annotation_id",
                    "measurement_comparability_id", "endpoint_id", "admission_receipt",
                }
                if any(not row[name] for name in required_values):
                    raise PermissionError("Real pairing source row is missing an explicit provenance/admission field")
            rows.append(row)
    return rows


def build_pairs(
    rows: Iterable[Mapping[str, object]],
    policy: PairingPolicy,
    *,
    classification: str,
    acceptance: PolicyAcceptance | None = None,
    crosswalk: Mapping[str, str] | CrosswalkAcceptance | None = None,
    use_gide_crosswalk: bool = False,
) -> PairingResult:
    """Build deterministic candidate pairs without consulting response or benefit.

    A proposed policy is usable only for an explicitly fixture-only run. A
    production policy needs ACCEPTED status and a separate record reference.
    """
    fixture_policy = validate_pairing_policy(
        policy,
        classification=classification,
        acceptance=acceptance,
        crosswalk=crosswalk,
        use_gide_crosswalk=use_gide_crosswalk,
    )
    normalized_crosswalk = _accepted_crosswalk(
        policy.study_id,
        crosswalk,
        use_gide_crosswalk=use_gide_crosswalk,
        classification=classification,
    )

    specimens = []
    seen_assays = set()
    specimen_owners: dict[tuple[str, str], str] = {}
    for raw in rows:
        specimen = _normalise_specimen(raw, policy.study_id, classification=classification)
        if normalized_crosswalk is not None:
            source_patient = specimen["patient_id"]
            if source_patient not in normalized_crosswalk:
                raise ValueError("Accepted Gide crosswalk does not map every source patient")
            specimen["patient_id"] = normalized_crosswalk[source_patient]
        owner_key = (specimen["study_id"], specimen["specimen_id"])
        owner = specimen_owners.setdefault(owner_key, specimen["patient_id"])
        if owner != specimen["patient_id"]:
            raise ValueError("A specimen ID cannot belong to multiple patients within a study")
        assay_key = (specimen["study_id"], specimen["assay_id"])
        if assay_key in seen_assays:
            raise ValueError("Assay IDs must be unique within a study")
        seen_assays.add(assay_key)
        specimens.append(specimen)

    specimens.sort(key=_opaque_specimen_key)
    assay_counts = Counter(
        (row["study_id"], row["patient_id"], row["specimen_id"])
        for row in specimens
    )
    exclusions: list[dict] = []
    classified: list[dict] = []
    classified_all: list[dict] = []
    for row in specimens:
        role, window_id, day_numeric, timing_reason, window_rule = _classify_window(row, policy)
        item = dict(row)
        item.update(
            {
                "_role": role,
                "_window_id": window_id or (window_rule.window_id if window_rule is not None else ""),
                "_day_numeric": day_numeric,
                "_window_rule": window_rule,
                "_timing_reason": timing_reason,
                "_row_reason": None,
            }
        )
        if timing_reason:
            item["_row_reason"] = timing_reason
        elif role == "baseline":
            if row["baseline_source"].casefold() not in _fold_set(policy.baseline_hierarchy):
                item["_row_reason"] = "baseline_source_unranked"
            elif row["prior_treatment"].casefold() not in _fold_set(policy.allowed_prior_treatment):
                item["_row_reason"] = "prior_treatment_baseline"
        elif role == "followup":
            if window_rule is not None and window_rule.transition_contrast_id:
                if window_rule.allowed_window_disease_states and row["disease_state"].casefold() not in _fold_set(window_rule.allowed_window_disease_states):
                    item["_row_reason"] = "transition_disease_state_not_allowed"
                elif window_rule.allowed_window_regimen_states and row["regimen_state"].casefold() not in _fold_set(window_rule.allowed_window_regimen_states):
                    item["_row_reason"] = "transition_regimen_state_not_allowed"
            else:
                if row["disease_state"].casefold() == "progression":
                    item["_row_reason"] = "progression"
                elif row["regimen_state"].casefold() == "changed":
                    item["_row_reason"] = "regimen_changed"
                elif row["regimen_state"].casefold() == "after_stop":
                    item["_row_reason"] = "after_stop"
                elif row["disease_state"].casefold() not in _fold_set(policy.allowed_disease_states):
                    item["_row_reason"] = "disease_state_not_allowed"
                elif row["regimen_state"].casefold() not in _fold_set(policy.allowed_regimen_states):
                    item["_row_reason"] = "regimen_state_not_allowed"
        if item["_row_reason"] is None and row["assay_qualified"].casefold() not in _QUALIFIED:
            item["_row_reason"] = "assay_not_qualified"
        if item["_row_reason"] is not None:
            exclusions.append(_exclusion(item, item["_row_reason"], policy))
        if role is not None:
            classified.append(item)
        else:
            classified_all.append(item)

    baselines = [row for row in classified if row["_role"] == "baseline"]
    followups = [row for row in classified if row["_role"] == "followup"]
    baseline_order = {value.casefold(): index for index, value in enumerate(policy.baseline_hierarchy)}
    baseline_groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in baselines:
        key = (row["study_id"], row["patient_id"], row["index_episode"], row["exposure"])
        if row["_row_reason"] is None:
            baseline_groups[key].append(row)
    selected_baseline_keys = {}
    for key, group in baseline_groups.items():
        selected = min(
            group,
            key=lambda row: (
                baseline_order[row["baseline_source"].casefold()],
                _opaque_specimen_key(row),
            ),
        )
        selected_baseline_keys[key] = selected["specimen_id"]
    for row in baselines:
        key = (row["study_id"], row["patient_id"], row["index_episode"], row["exposure"])
        # Technical runs from the chosen specimen remain candidate rows; they
        # are resolved by the stable assay tie-break after specimen selection.
        row["_baseline_selected"] = selected_baseline_keys.get(key) == row["specimen_id"]
        if row["_row_reason"] is None and not row["_baseline_selected"]:
            exclusions.append(_exclusion(row, "lower_priority_baseline"))
    candidates: list[dict] = []
    by_patient: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"baseline": [], "followup": []})
    for row in baselines:
        by_patient[row["patient_id"]]["baseline"].append(row)
    for row in followups:
        by_patient[row["patient_id"]]["followup"].append(row)
    for patient_id, groups in sorted(by_patient.items()):
        if groups["followup"] and not groups["baseline"]:
            for on in groups["followup"]:
                cross_patient_baseline = any(
                    row["patient_id"] != patient_id
                    and row["index_episode"] == on["index_episode"]
                    and row["exposure"] == on["exposure"]
                    for row in baselines
                )
                exclusions.append(_exclusion(on, "patient_mismatch" if cross_patient_baseline else "no_baseline", policy))
        for pre in groups["baseline"]:
            for on in groups["followup"]:
                if not pre.get("_baseline_selected", False):
                    exclusions.append(_pair_exclusion(pre, on, "lower_priority_baseline", policy))
                    continue
                if pre["_row_reason"] is not None:
                    exclusions.append(_pair_exclusion(pre, on, pre["_row_reason"], policy))
                    continue
                if on["_row_reason"] is not None:
                    exclusions.append(_pair_exclusion(pre, on, on["_row_reason"], policy))
                    continue
                reason = _pair_reason(pre, on, policy)
                if reason:
                    exclusions.append(_pair_exclusion(pre, on, reason, policy))
                    continue
                candidates.append(_candidate(pre, on, policy, assay_counts, fixture_policy))

    _select_one_per_window(candidates, policy)
    candidates.sort(key=lambda row: row["pair_id"])
    exclusions.sort(key=lambda row: (
        row.get("patient_id", ""), row.get("specimen_id", ""), row.get("assay_id", ""), row["reason"]
    ))
    missing = _missing_followups(baselines, followups, candidates, [*classified, *classified_all], policy)
    selected = [row for row in candidates if row["selected"]]
    summary = _pair_summary(
        specimens, baselines, followups, candidates, selected, assay_counts, policy
    )
    for candidate in candidates:
        candidate.pop("_window_rule", None)
    return PairingResult(
        candidates=candidates,
        exclusions=exclusions,
        missing_followups=missing,
        summary=summary,
        policy_status="FIXTURE_ONLY_PROPOSAL" if fixture_policy else "ACCEPTED",
        data_classification=classification,
    )


def validate_pairing_policy(
    policy: PairingPolicy,
    *,
    classification: str,
    acceptance: PolicyAcceptance | None,
    crosswalk: Mapping[str, str] | CrosswalkAcceptance | None = None,
    use_gide_crosswalk: bool = False,
) -> bool:
    """Validate source policy and crosswalk authorization before source access."""
    if not isinstance(policy, PairingPolicy):
        raise ValueError("An explicit source-specific PairingPolicy is required")
    _guard_study_id(policy.study_id, classification)
    fixture_policy = _validate_policy(policy, classification, acceptance)
    _accepted_crosswalk(
        policy.study_id,
        crosswalk,
        use_gide_crosswalk=use_gide_crosswalk,
        classification=classification,
    )
    return fixture_policy

def write_pair_products(result: PairingResult, output_dir: Path | str) -> dict[str, Path]:
    """Write patient-level pairing receipts only under results/ or .scratch/."""
    root = Path(__file__).resolve().parents[2]
    output_dir = guard_path(output_dir, "pairing output directory")
    private_root = None
    try:
        relative = output_dir.relative_to(root.resolve())
    except ValueError:
        relative = None
    if relative is not None:
        if not relative.parts or relative.parts[0] not in {"results", ".scratch"}:
            raise ValueError("Patient-level pairing outputs must stay under results/ or .scratch/")
        private_root = root / relative.parts[0]
    elif result.data_classification == "real":
        raise PermissionError("Real patient-level pairing outputs must stay under results/ or .scratch/")
    output_dir = prepare_output_directory(output_dir, private_root=private_root)
    candidate_columns = (
        "pair_id", "study_id", "patient_id", "index_episode", "exposure", "pre_specimen_id",
        "pre_assay_id", "on_window", "on_specimen_id", "on_assay_id", "pre_category_raw",
        "pre_day_raw", "pre_day_precision", "pre_day_numeric", "pre_day_origin",
        "on_category_raw", "on_day_raw", "on_day_precision", "on_day_numeric", "on_day_origin",
        "day_distance_to_target", "pair_day_distance", "timing_ambiguity",
        "pre_source_locator", "on_source_locator", "pre_source_confidence", "on_source_confidence",
        "pre_annotation_id", "on_annotation_id", "measurement_comparability_id",
        "pre_measurement_comparability_id", "on_measurement_comparability_id",
        "pre_endpoint_id", "on_endpoint_id", "pre_admission_receipt", "on_admission_receipt",
        "endpoint_id", "admission_receipt", "pre_platform", "on_platform", "pre_unit", "on_unit", "same_lesion",
        "source_family_id", "overlap_receipt_id", "overlap_status",
        "pre_technical_replicates", "on_technical_replicates", "candidate_status", "selected",
        "reason", "selected_reason", "baseline_selected", "policy_status",
    )
    exclusion_columns = (
        "study_id", "patient_id", "index_episode", "exposure", "window_id", "specimen_id", "assay_id",
        "pre_specimen_id", "pre_assay_id", "on_specimen_id", "on_assay_id",
        "timepoint_category", "collection_day", "day_precision", "day_origin",
        "pre_category_raw", "pre_day_raw", "pre_day_precision", "pre_day_origin",
        "on_category_raw", "on_day_raw", "on_day_precision", "on_day_origin",
        "source_locator", "source_confidence", "annotation_id", "measurement_comparability_id",
        "endpoint_id", "admission_receipt", "source_family_id", "overlap_receipt_id", "overlap_status",
        "pre_source_locator", "on_source_locator", "pre_source_confidence", "on_source_confidence",
        "pre_annotation_id", "on_annotation_id", "pre_measurement_comparability_id",
        "on_measurement_comparability_id", "pre_endpoint_id", "on_endpoint_id",
        "pre_admission_receipt", "on_admission_receipt", "reason",
    )
    paths = {
        "pair_candidates": output_dir / "pair_candidates.tsv",
        "pairing_exclusions": output_dir / "pairing_exclusions.tsv",
        "missing_followups": output_dir / "missing_followups.tsv",
        "pairing_summary": output_dir / "pairing_summary.tsv",
        "longitudinal_support": output_dir / "longitudinal_support.tsv",
    }
    _write_tsv(paths["pair_candidates"], result.candidates, candidate_columns)
    _write_tsv(
        paths["pairing_exclusions"], result.exclusions,
        exclusion_columns,
    )
    _write_tsv(
        paths["missing_followups"], result.missing_followups,
        ("study_id", "patient_id", "index_episode", "exposure", "window_id", "reason", "candidate_reasons"),
    )
    _write_tsv(paths["pairing_summary"], [result.summary], tuple(result.summary))
    support_rows = [
        {
            "study_id": result.summary["study_id"],
            "window": window,
            "selected_pairs": count,
            "support_role": "one_way_corroboration_only",
        }
        for window, count in sorted(result.summary["selected_by_window"].items())
    ]
    _write_tsv(
        paths["longitudinal_support"], support_rows,
        ("study_id", "window", "selected_pairs", "support_role"),
    )
    return paths


def _guard_study_id(study_id: str, classification: str) -> None:
    if classification not in {"real", "synthetic"}:
        raise ValueError("Data classification must be explicitly real or synthetic")
    if not isinstance(study_id, str) or not study_id.strip():
        raise ValueError("Study ID must be explicit")
    if is_locked_study(study_id):
        raise ValueError("IMvigor210 is a locked final test and is refused")
    if classification == "synthetic" and study_id.casefold() in {
        value.casefold() for value in known_cohort_ids()
    }:
        raise ValueError("Synthetic provenance cannot name a known real cohort")


def _verify_synthetic_input(path, manifest_path, study_id):
    if manifest_path is None:
        raise ValueError("Synthetic specimen input requires a fixture provenance manifest")
    guarded, _ = check_path_separation(
        inputs={"specimen table": path, "provenance manifest": manifest_path},
        outputs={},
    )
    path = guarded["specimen table"]
    manifest_path = guarded["provenance manifest"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Synthetic specimen provenance manifest is missing or malformed") from error
    if (
        manifest.get("producer") != _MANIFEST_PRODUCER
        or manifest.get("manifest_version") != 1
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != "a_long_specimen_input"
    ):
        raise ValueError("Synthetic specimen manifest has the wrong producer, kind, or classification")
    if set(manifest.get("cohort_ids", ())) != {study_id}:
        raise ValueError("Synthetic specimen manifest study ID does not match the input")
    digest = file_sha256(path)
    if digest != manifest.get("payload_sha256"):
        raise ValueError("Synthetic specimen manifest payload hash does not match")
    if manifest.get("outputs_sha256", {}).get(path.name) != digest:
        raise ValueError("Synthetic specimen manifest output hash does not match")


def validate_pairing_policy_contract(policy, classification):
    if not isinstance(policy, PairingPolicy):
        raise ValueError("An explicit source-specific PairingPolicy is required")
    if not policy.windows or not policy.baseline_hierarchy:
        raise ValueError("Policy requires approved windows and an explicit baseline hierarchy")
    if not policy.allowed_prior_treatment or not policy.allowed_disease_states or not policy.allowed_regimen_states:
        raise ValueError("Policy must explicitly define prior-treatment, disease, and regimen states")
    if len({rule.window_id for rule in policy.windows}) != len(policy.windows):
        raise ValueError("Window IDs must be unique")
    baseline_rules = [rule for rule in policy.windows if rule.role == "baseline"]
    followup_rules = [rule for rule in policy.windows if rule.role == "followup"]
    if len(baseline_rules) != 1 or baseline_rules[0].window_id != policy.baseline_window or not followup_rules:
        raise ValueError("Policy requires one declared baseline and at least one follow-up window")
    category_owners = {}
    for rule in policy.windows:
        if rule.role not in {"baseline", "followup"} or not rule.categories:
            raise ValueError("Each window needs a baseline/follow-up role and source-specific categories")
        if rule.transition_contrast_id and rule.role != "followup":
            raise ValueError("A transition contrast must be a distinct follow-up window")
        if rule.transition_contrast_id and not (
            rule.allowed_window_disease_states or rule.allowed_window_regimen_states
        ):
            raise ValueError("A transition contrast must explicitly bind allowed disease or regimen states")
        if rule.day_interval is not None:
            lo, hi = rule.day_interval
            if not (math.isfinite(lo) and math.isfinite(hi) and lo <= hi):
                raise ValueError("Window day interval must be finite and ordered")
            if not rule.day_origin:
                raise ValueError("Exact-day windows require an explicit source-specific day origin")
            if rule.target_day is not None and not lo <= rule.target_day <= hi:
                raise ValueError("Window target day must fall inside its source interval")
        elif rule.day_origin is not None or rule.target_day is not None:
            raise ValueError("Day origin and target require a declared exact-day interval")
        for category in rule.categories:
            key = category.casefold()
            if key in category_owners:
                raise ValueError("Source timepoint categories cannot map to multiple windows")
            category_owners[key] = rule.window_id
    if policy.status not in {"PROPOSED", "ACCEPTED"}:
        raise ValueError("Policy status must be PROPOSED or ACCEPTED")
    if not isinstance(policy.allow_different_lesion, bool):
        raise ValueError("Different-lesion admission must be an explicit boolean policy field")
    if policy.endpoint_id is not None and not str(policy.endpoint_id).strip():
        raise ValueError("Endpoint binding must be non-empty when supplied")
    if classification == "real" and (
        not policy.source_family_id
        or not policy.overlap_receipt_id
        or policy.overlap_status not in {"DISJOINT_VERIFIED", "OVERLAPPING", "UNRESOLVED"}
        or not re.fullmatch(r"[0-9a-f]{64}", policy.overlap_receipt_id)
        or not policy.admission_receipt
    ):
        raise ValueError("Real pairing requires explicit source-family and overlap admission receipts")
    if classification == "real" and (policy.status != "ACCEPTED" or not policy.decision_ref):
        raise PermissionError("N12 status and decision reference must be accepted before source access")
    return True


def _validate_policy(policy, classification, acceptance):
    validate_pairing_policy_contract(policy, classification)
    if acceptance is None or not acceptance.record_ref or not acceptance.decision_id:
        raise ValueError("Window policy is unsigned; an explicit acceptance record is required")
    if acceptance.fixture_only:
        if classification != "synthetic":
            raise ValueError("Fixture-only policy acceptance is restricted to synthetic data")
        return True
    if not is_authorized_release(
        acceptance.authorization, release_scope="N12_PAIRING", operation="pair"
    ):
        raise PermissionError("N12 status and record_ref are not signatures; use the scoped user-release record")
    record = acceptance.authorization.record
    if (
        policy.status != "ACCEPTED"
        or record.get("policy_sha256") != canonical_sha256(asdict(policy))
        or record.get("cohorts") != [policy.study_id]
        or not isinstance(record.get("decision"), dict)
        or record["decision"].get("identity") != policy.decision_ref
    ):
        raise PermissionError("N12 user-release record does not bind this accepted source policy")
    return False


def _accepted_crosswalk(study_id, crosswalk, *, use_gide_crosswalk, classification):
    if use_gide_crosswalk:
        if crosswalk is None:
            raise ValueError("Gide crosswalk requires explicit user acceptance and a mapping")
        if not isinstance(crosswalk, CrosswalkAcceptance) or not crosswalk.record_ref:
            raise ValueError("Gide crosswalk requires explicit user acceptance from a user record")
        if "gide" not in study_id.casefold():
            raise ValueError("The accepted run crosswalk is restricted to an explicit Gide study")
        if crosswalk.fixture_only and classification != "synthetic":
            raise ValueError("Fixture-only Gide crosswalk acceptance is restricted to synthetic data")
        if not crosswalk.fixture_only:
            if not is_authorized_release(
                crosswalk.authorization,
                release_scope="N12_GIDE_CROSSWALK",
                operation="accept_gide_crosswalk",
            ):
                raise PermissionError("Gide crosswalk references are not signatures; use its scoped user-release record")
            record = crosswalk.authorization.record
            if (
                record.get("crosswalk_sha256") != canonical_sha256(dict(crosswalk.mapping))
                or record.get("cohorts") != [study_id]
            ):
                raise PermissionError("Gide crosswalk record does not bind this exact mapping and study")
        mapping = dict(crosswalk.mapping)
        if not mapping or len(mapping.values()) != len(set(mapping.values())):
            raise ValueError("Accepted Gide crosswalk must be an explicit one-to-one mapping")
        if any(not source or not target for source, target in mapping.items()):
            raise ValueError("Accepted Gide crosswalk has an empty mapping value")
        return mapping
    if crosswalk is not None:
        raise ValueError("Crosswalk material is present but activation was not explicitly requested")
    return None


def _normalise_specimen(raw, study_id, *, classification="synthetic"):
    if not isinstance(raw, Mapping) or set(raw) != set(CANONICAL_COLUMNS):
        raise ValueError("Specimen rows must contain only the canonical outcome-free columns")
    row = {column: "" if raw[column] is None else str(raw[column]).strip() for column in CANONICAL_COLUMNS}
    for name in _REQUIRED_NONEMPTY:
        if not row[name]:
            raise ValueError(f"Required specimen field is empty: {name}")
    if row["study_id"] != study_id:
        raise ValueError("Specimen row study ID does not match the declared study")
    if not row["patient_id"] or not row["specimen_id"] or not row["assay_id"]:
        raise ValueError("Study, patient, specimen, and assay identities must be explicit")
    if classification == "real" and any(not row[name] for name in _REQUIRED_REAL_PROVENANCE):
        raise PermissionError("Real pairing source row is missing explicit provenance/admission fields")
    return row


def _classify_window(row, policy):
    raw_day = row["collection_day"]
    precision = row["day_precision"].casefold()
    day_numeric = None
    if raw_day:
        if precision in _EXACT_PRECISION:
            try:
                day_numeric = float(raw_day)
            except ValueError:
                return None, None, None, "invalid_collection_day", None
            if not math.isfinite(day_numeric):
                return None, None, None, "invalid_collection_day", None

    category = row["timepoint_category"].casefold()
    category_window = next(
        (rule for rule in policy.windows if category in {value.casefold() for value in rule.categories}),
        None,
    )
    day_windows = []
    if day_numeric is not None:
        for rule in policy.windows:
            if rule.day_interval is not None and rule.day_interval[0] <= day_numeric <= rule.day_interval[1]:
                day_windows.append(rule)
    if category_window is not None and category_window.day_interval is not None and day_numeric is not None:
        lo, hi = category_window.day_interval
        if not lo <= day_numeric <= hi:
            return None, None, day_numeric, "timing_contradiction", category_window
    if category_window is not None and day_windows and all(rule.window_id != category_window.window_id for rule in day_windows):
        return None, None, day_numeric, "timing_contradiction", category_window
    if len(day_windows) > 1:
        return None, None, day_numeric, "timing_contradiction", None
    chosen = category_window or (day_windows[0] if day_windows else None)
    if chosen is None:
        if raw_day and precision not in _EXACT_PRECISION:
            return None, None, None, "day_precision_unqualified", None
        return None, None, day_numeric, "outside_approved_windows", None
    if day_numeric is not None and chosen.day_origin and row["day_origin"] != chosen.day_origin:
        return None, None, day_numeric, "day_origin_mismatch", chosen
    return chosen.role, chosen.window_id, day_numeric, None, chosen


def _pair_reason(pre, on, policy):
    if pre["index_episode"] != on["index_episode"]:
        return "episode_mismatch"
    if pre["exposure"] != on["exposure"]:
        return "exposure_mismatch"
    compatible = (
        "compartment", "platform", "unit", "assay_method", "annotation_id",
        "measurement_comparability_id", "endpoint_id",
    )
    if any(pre[name] != on[name] for name in compatible):
        return "assay_incompatible"
    if policy.endpoint_id and pre["endpoint_id"] != policy.endpoint_id:
        return "endpoint_binding_mismatch"
    if not policy.allow_different_lesion and (pre["lesion_id"] or on["lesion_id"]) and pre["lesion_id"] != on["lesion_id"]:
        return "different_lesion_not_admitted"
    return None


def _candidate(pre, on, policy, assay_counts, fixture_policy):
    same_lesion = bool(pre["lesion_id"] and pre["lesion_id"] == on["lesion_id"])
    pair_key = {
        "study": pre["study_id"], "patient": pre["patient_id"],
        "episode": pre["index_episode"], "exposure": pre["exposure"],
        "window": on["_window_id"], "pre_specimen": pre["specimen_id"],
        "pre_assay": pre["assay_id"], "on_specimen": on["specimen_id"],
        "on_assay": on["assay_id"],
    }
    pair_id = hashlib.sha256(_canonical_json(pair_key).encode("utf-8")).hexdigest()[:24]
    rule = next(rule for rule in policy.windows if rule.window_id == on["_window_id"])
    distance = (
        abs(on["_day_numeric"] - rule.target_day)
        if on["_day_numeric"] is not None and rule.target_day is not None
        else None
    )
    opaque_tie = _opaque_pair_key(pre, on)
    return {
        "pair_id": pair_id,
        "study_id": pre["study_id"],
        "patient_id": pre["patient_id"],
        "index_episode": pre["index_episode"],
        "exposure": pre["exposure"],
        "pre_specimen_id": pre["specimen_id"],
        "pre_assay_id": pre["assay_id"],
        "on_window": on["_window_id"],
        "on_specimen_id": on["specimen_id"],
        "on_assay_id": on["assay_id"],
        "pre_category_raw": pre["timepoint_category"],
        "pre_day_raw": pre["collection_day"],
        "pre_day_precision": pre["day_precision"],
        "pre_day_numeric": pre["_day_numeric"],
        "pre_day_origin": pre["day_origin"],
        "on_category_raw": on["timepoint_category"],
        "on_day_raw": on["collection_day"],
        "on_day_precision": on["day_precision"],
        "on_day_numeric": on["_day_numeric"],
        "on_day_origin": on["day_origin"],
        "day_distance_to_target": distance,
        "pair_day_distance": abs(on["_day_numeric"] - pre["_day_numeric"])
        if on["_day_numeric"] is not None and pre["_day_numeric"] is not None else None,
        "timing_ambiguity": "none" if on["_day_numeric"] is not None and pre["_day_numeric"] is not None else "exact_day_unknown",
        "pre_source_locator": pre["source_locator"],
        "on_source_locator": on["source_locator"],
        "pre_source_confidence": pre["source_confidence"],
        "on_source_confidence": on["source_confidence"],
        "pre_annotation_id": pre["annotation_id"],
        "on_annotation_id": on["annotation_id"],
        "measurement_comparability_id": pre["measurement_comparability_id"],
        "pre_measurement_comparability_id": pre["measurement_comparability_id"],
        "on_measurement_comparability_id": on["measurement_comparability_id"],
        "pre_endpoint_id": pre["endpoint_id"],
        "on_endpoint_id": on["endpoint_id"],
        "pre_admission_receipt": pre["admission_receipt"],
        "on_admission_receipt": on["admission_receipt"],
        "endpoint_id": pre["endpoint_id"],
        "admission_receipt": policy.admission_receipt or "",
        "source_family_id": policy.source_family_id or "",
        "overlap_receipt_id": policy.overlap_receipt_id or "",
        "overlap_status": policy.overlap_status or "UNRESOLVED",
        "pre_platform": pre["platform"],
        "on_platform": on["platform"],
        "pre_unit": pre["unit"],
        "on_unit": on["unit"],
        "same_lesion": same_lesion,
        "pre_technical_replicates": assay_counts[(pre["study_id"], pre["patient_id"], pre["specimen_id"])],
        "on_technical_replicates": assay_counts[(on["study_id"], on["patient_id"], on["specimen_id"])],
        "candidate_status": "eligible",
        "selected": False,
        "baseline_selected": bool(pre.get("_baseline_selected", False)),
        "reason": "",
        "selected_reason": "",
        "policy_status": "FIXTURE_ONLY_PROPOSAL" if fixture_policy else "ACCEPTED",
        "_time_distance": math.inf if distance is None else distance,
        "_same_lesion_rank": 0 if policy.prefer_same_lesion and same_lesion else 1,
        "_opaque_tie": opaque_tie,
    }


def _select_one_per_window(candidates, policy):
    grouped = defaultdict(list)
    for row in candidates:
        grouped[(row["study_id"], row["patient_id"], row["index_episode"], row["exposure"], row["on_window"])].append(row)
    for group in grouped.values():
        eligible = [row for row in group if row["baseline_selected"]]
        if not eligible:
            for row in group:
                row["candidate_status"] = "rejected_lower_priority_baseline"
                row["reason"] = "lower_priority_baseline"
            continue
        selected = min(
            eligible,
            key=lambda row: (
                row["_time_distance"],
                row["_same_lesion_rank"],
                row["_opaque_tie"],
            ),
        )
        selected["selected"] = True
        selected["selected_reason"] = (
            "baseline_hierarchy_then_time_relevance_then_compatible_assay_"
            "then_allowed_same_lesion_then_opaque_tie_break"
        )
    for row in candidates:
        row.pop("_time_distance", None)
        row.pop("_same_lesion_rank", None)
        row.pop("_opaque_tie", None)


def _missing_followups(baselines, followups, candidates, classified, policy):
    selected = {
        (row["study_id"], row["patient_id"], row["index_episode"], row["exposure"], row["on_window"])
        for row in candidates if row["selected"]
    }
    baseline_by_key = {}
    for row in baselines:
        if row["_row_reason"] is None and row.get("_baseline_selected", False):
            key = (row["study_id"], row["patient_id"], row["index_episode"], row["exposure"])
            baseline_by_key[key] = row
    by_key_window = defaultdict(list)
    for row in classified:
        window = row.get("_window_id")
        if window:
            key = (row["study_id"], row["patient_id"], row["index_episode"], row["exposure"], window)
            by_key_window[key].append(row)
    followup_rules = [rule for rule in policy.windows if rule.role == "followup"]
    missing = []
    for key in sorted(baseline_by_key):
        for rule in followup_rules:
            selected_key = (*key, rule.window_id)
            if selected_key in selected:
                continue
            rows = by_key_window.get(selected_key, [])
            followup_rows = [row for row in rows if row["_role"] == "followup"]
            eligible = [row for row in followup_rows if row["_row_reason"] is None]
            if not rows:
                reason = "no_followup_specimen"
            elif not eligible:
                reason = "no_eligible_followup"
            else:
                reason = "no_compatible_followup"
            reasons = sorted({str(row["_row_reason"]) for row in rows if row.get("_row_reason")})
            missing.append({
                "study_id": key[0], "patient_id": key[1], "index_episode": key[2],
                "exposure": key[3], "window_id": rule.window_id, "reason": reason,
                "candidate_reasons": ",".join(reasons),
            })
    return missing


def _pair_summary(specimens, baselines, followups, candidates, selected, assay_counts, policy):
    selected_counts = Counter(row["on_window"] for row in selected)
    selected_by_window = {
        rule.window_id: selected_counts.get(rule.window_id, 0)
        for rule in policy.windows if rule.role == "followup"
    }
    platform_counts = dict(sorted(Counter(f"{row['pre_platform']}/{row['pre_unit']}" for row in selected).items()))
    baseline_patients = {row["patient_id"] for row in baselines if row["_row_reason"] is None}
    followup_patients = {row["patient_id"] for row in followups if row["_row_reason"] is None}
    return {
        "study_id": specimens[0]["study_id"] if specimens else "",
        "specimens_in": len({row["specimen_id"] for row in specimens}),
        "assays_in": len(specimens),
        "patients_in": len({row["patient_id"] for row in specimens}),
        "patients_with_baseline": len(baseline_patients),
        "patients_with_followup": len(followup_patients),
        "patients_paired": len({row["patient_id"] for row in selected}),
        "candidate_pairs": len(candidates),
        "selected_pairs": len(selected),
        "technical_replicate_specimens": sum(count > 1 for count in assay_counts.values()),
        "same_lesion_pairs": sum(bool(row["same_lesion"]) for row in selected),
        "platform_counts": platform_counts,
        "selected_by_window": selected_by_window,
        "endpoint_evaluable_counts": None,
        "endpoint_status": "UNAVAILABLE_OUTCOME_LOCKED",
    }


def _exclusion(row, reason, policy=None):
    return {
        "study_id": row["study_id"], "patient_id": row["patient_id"],
        "index_episode": row["index_episode"], "exposure": row["exposure"],
        "window_id": row.get("_window_id", ""), "specimen_id": row["specimen_id"],
        "assay_id": row["assay_id"], "pre_specimen_id": "", "pre_assay_id": "",
        "on_specimen_id": "", "on_assay_id": "",
        "timepoint_category": row["timepoint_category"], "collection_day": row["collection_day"],
        "day_precision": row["day_precision"], "day_origin": row["day_origin"],
        "pre_category_raw": "", "pre_day_raw": "", "pre_day_precision": "", "pre_day_origin": "",
        "on_category_raw": "", "on_day_raw": "", "on_day_precision": "", "on_day_origin": "",
        "source_locator": row["source_locator"], "source_confidence": row["source_confidence"],
        "annotation_id": row["annotation_id"], "measurement_comparability_id": row["measurement_comparability_id"],
        "endpoint_id": row["endpoint_id"], "admission_receipt": row["admission_receipt"],
        "source_family_id": policy.source_family_id or "" if policy else "",
        "overlap_receipt_id": policy.overlap_receipt_id or "" if policy else "",
        "overlap_status": policy.overlap_status or "" if policy else "",
        "pre_source_locator": "", "on_source_locator": "",
        "pre_source_confidence": "", "on_source_confidence": "",
        "pre_annotation_id": "", "on_annotation_id": "",
        "pre_measurement_comparability_id": "", "on_measurement_comparability_id": "",
        "pre_endpoint_id": "", "on_endpoint_id": "",
        "pre_admission_receipt": "", "on_admission_receipt": "", "reason": reason,
    }


def _pair_exclusion(pre, on, reason, policy=None):
    return {
        **_exclusion(pre, reason, policy),
        "window_id": on.get("_window_id", ""), "specimen_id": "", "assay_id": "",
        "pre_specimen_id": pre["specimen_id"], "pre_assay_id": pre["assay_id"],
        "on_specimen_id": on["specimen_id"], "on_assay_id": on["assay_id"],
        "pre_category_raw": pre["timepoint_category"], "pre_day_raw": pre["collection_day"],
        "pre_day_precision": pre["day_precision"], "pre_day_origin": pre["day_origin"],
        "on_category_raw": on["timepoint_category"], "on_day_raw": on["collection_day"],
        "on_day_precision": on["day_precision"], "on_day_origin": on["day_origin"],
        "pre_source_locator": pre["source_locator"], "on_source_locator": on["source_locator"],
        "pre_source_confidence": pre["source_confidence"], "on_source_confidence": on["source_confidence"],
        "pre_annotation_id": pre["annotation_id"], "on_annotation_id": on["annotation_id"],
        "pre_measurement_comparability_id": pre["measurement_comparability_id"],
        "on_measurement_comparability_id": on["measurement_comparability_id"],
        "pre_endpoint_id": pre["endpoint_id"], "on_endpoint_id": on["endpoint_id"],
        "pre_admission_receipt": pre["admission_receipt"], "on_admission_receipt": on["admission_receipt"],
    }


def _opaque_specimen_key(row):
    return hashlib.sha256(_canonical_json({
        "study": row["study_id"], "patient": row["patient_id"],
        "episode": row["index_episode"], "specimen": row["specimen_id"],
        "assay": row["assay_id"],
    }).encode("utf-8")).hexdigest()


def _opaque_pair_key(pre, on):
    return hashlib.sha256(_canonical_json({
        "pre": _opaque_specimen_key(pre), "on": _opaque_specimen_key(on),
    }).encode("utf-8")).hexdigest()


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fold_set(values):
    return {str(value).casefold() for value in values}


def _write_tsv(path, rows, columns):
    path = guard_path(path, "TSV output")
    if path.exists():
        raise FileExistsError("A-LONG TSV output already exists")
    if not path.parent.is_dir():
        raise FileNotFoundError("A-LONG TSV output directory was not prepared")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(columns), delimiter="\t",
            lineterminator="\n", extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format_cell(row.get(key)) for key in columns})


def _format_cell(value):
    if value is None:
        return "NA"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and not math.isfinite(value):
        return "NA"
    return value
