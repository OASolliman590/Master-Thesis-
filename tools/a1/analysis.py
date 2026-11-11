"""Synthetic-only A-LONG model, randomized-arm, and synthesis interfaces."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from tools.a_meta.provenance import canonical_sha256, is_locked_study, known_cohort_ids
from tools.a1.authorization import (
    check_path_separation,
    guard_path,
    is_authorized_release,
    is_released_inputs,
    prepare_output_directory,
    sha256_file,
    validate_output_directory,
)
from tools.r_bridge import run_r


_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "r" / "R" / "a_long.R"
_MANIFEST_PRODUCER = "tools.a_meta.synthetic_fixture"
_IDENTITY_COLUMNS = (
    "unit_family", "feature_method_id", "analysis_method_id", "endpoint_id",
    "regimen_id", "window_id", "assay_id", "effect_scale_id",
    "panel_family", "multiplicity_family_id", "source_family_id",
    "overlap_receipt_id", "overlap_status",
)
_SYNTHESIS_COLUMNS = (
    "study", "patient_set_id", "source_family_id", "overlap_receipt_id", "overlap_status",
    "unit_family", "unit", "panel_family", "multiplicity_family_id",
    "feature_method_id", "analysis_method_id", "endpoint_id", "regimen_id",
    "window_id", "assay_id", "effect_scale_id", "estimate", "se",
    "ci_lb", "ci_ub", "p_value", "status", "reason",
)
_OVERLAP_RECEIPT_COLUMNS = (
    "study_a", "study_b", "source_family_a", "source_family_b",
    "overlap_status", "receipt_sha256",
)
_EXPECTED_MODELS = {
    "delta_method_id": "lm_change_response_covariates_v1",
    "ancova_method_id": "lm_on_response_baseline_covariates_sensitivity_v1",
    "repeated_method_id": "lmerTest_lme4_response_window_random_intercept_v1",
    "randomized_arm_method_id": "lm_randomized_arm_change_contrast_v1",
    "meta_method_id": "metafor_REML_modified_KH_v1",
    "df_method_id": "residual_t_and_Satterthwaite_v1",
    "same_lesion_sensitivity_method_id": "lm_change_response_covariates_same_lesion_sensitivity_v1",
    "exact_day_sensitivity_method_id": "lm_change_response_covariates_exact_day_sensitivity_v1",
    "tighter_timing_sensitivity_method_id": "lm_change_response_covariates_tighter_timing_sensitivity_v1",
}


@dataclass(frozen=True)
class N13Policy:
    status: str
    decision_ref: str | None
    delta_method_id: str
    ancova_method_id: str
    repeated_method_id: str
    randomized_arm_method_id: str
    meta_method_id: str
    df_method_id: str
    covariates: tuple[str, ...]
    repeated_windows: tuple[str, ...]
    min_repeated_patients: int
    min_per_response_group: int
    min_meta_k_pool: int
    confidence_level: float
    fdr_scope_id: str
    repeated_selection_mode: str | None = None
    min_per_randomized_arm: int | None = None
    panel_family_members: Mapping[str, tuple[str, ...]] | None = None
    m5m6_family_members: tuple[str, ...] = ()
    fdr_denominator_policy: str | None = None
    source_overlap_contract_sha256: str | None = None
    same_lesion_sensitivity_method_id: str = _EXPECTED_MODELS["same_lesion_sensitivity_method_id"]
    exact_day_sensitivity_method_id: str = _EXPECTED_MODELS["exact_day_sensitivity_method_id"]
    tighter_timing_sensitivity_method_id: str = _EXPECTED_MODELS["tighter_timing_sensitivity_method_id"]
    sensitivity_modes: tuple[str, ...] = ()
    tighter_timing_max_deviation_days: float | None = None


@dataclass(frozen=True)
class N13Acceptance:
    decision_id: str
    record_ref: str
    fixture_only: bool = False
    authorization: object | None = None


@dataclass(frozen=True)
class RandomizationAdmission:
    comparative_estimand_id: str
    record_ref: str
    randomization_verified: bool
    fixture_only: bool = False
    authorization: object | None = None


@dataclass
class AnalysisResult:
    effects: list[dict[str, str]]
    within_group_deltas: list[dict[str, str]]
    support: dict[str, str]
    paths: dict[str, Path]
    policy_status: str


def run_released_analysis(
    route: str,
    *,
    released_inputs,
    policy_payload: Mapping,
    output_dir: Path | str,
    retention_dir: Path | str,
    allow_outcomes: bool = False,
    runner=None,
) -> AnalysisResult:
    """Execute one model route from a two-phase, user-record-validated input."""
    if allow_outcomes is not True:
        raise PermissionError("A-LONG released models require allow_outcomes=True")
    route_specs = {
        "two-timepoint": ("N13_TWO_TIMEPOINT", "fit_two_timepoint", "two_timepoint"),
        "ancova": ("N13_TWO_TIMEPOINT", "fit_two_timepoint", "two_timepoint"),
        "repeated": ("N13_REPEATED", "fit_repeated_windows", "repeated"),
        "randomized-arm": ("N13_RANDOMIZED_ARM", "fit_randomized_arm", "randomized_arm"),
    }
    if route not in route_specs:
        raise ValueError("Released model route is unsupported")
    scope, operation, mode = route_specs[route]
    if not is_released_inputs(released_inputs, release_scope=scope, operation=operation):
        raise PermissionError("A-LONG model route needs validated user-release inputs")
    record = released_inputs.authorization.record
    if canonical_sha256(policy_payload) != record.get("policy_sha256"):
        raise PermissionError("N13 policy payload differs from the approved user-release hash")
    if len(record.get("cohorts", ())) != 1:
        raise ValueError("Each A-LONG model command must analyze one declared study at a time")
    if set(released_inputs.tables) != {"design"}:
        raise ValueError("Released model input requires exactly one named design table")

    payload = dict(policy_payload)
    randomization = payload.pop("randomization_admission", None)
    allowed_policy_fields = {field.name for field in fields(N13Policy)}
    if set(payload) != allowed_policy_fields:
        raise ValueError("Released N13 model policy must supply every numerical field exactly")
    for name in ("covariates", "repeated_windows", "m5m6_family_members", "sensitivity_modes"):
        payload[name] = tuple(payload[name])
    if payload.get("panel_family_members") is not None:
        payload["panel_family_members"] = {
            key: tuple(value) for key, value in payload["panel_family_members"].items()
        }
    policy = N13Policy(**payload)
    decision = record["decision"]["identity"]
    acceptance = N13Acceptance(
        decision_id=decision,
        record_ref=released_inputs.authorization.record_sha256,
        authorization=released_inputs.authorization,
    )
    fixture_policy = _validate_n13(
        policy,
        acceptance,
        route=mode,
        authorized_policy_sha256=record["policy_sha256"],
    )
    rows = [dict(row) for row in released_inputs.tables["design"]]
    study_id = record["cohorts"][0]
    if {str(row.get("study_id", "")) for row in rows} != {study_id}:
        raise PermissionError("Released model rows do not match the authorized study identity")
    if not rows:
        raise ValueError("Released model table is empty")
    from tools.a1.features import fixed_long_feature_memberships

    fixed = fixed_long_feature_memberships()
    expected_units = {
        *(f"AP2:{panel}" for panel in fixed.ap2_panels), "CYT",
        *(f"CUSTOM:{panel}" for panel in fixed.custom_panels),
        *(f"M5M6:{gene}" for gene in fixed.m5m6_genes),
    }
    if {str(row.get("unit", "")) for row in rows} != expected_units:
        raise ValueError("Released A-LONG model input must contain the complete fixed feature set")
    expected_method = {
        "two_timepoint": policy.delta_method_id,
        "repeated": policy.repeated_method_id,
        "randomized_arm": policy.randomized_arm_method_id,
    }[mode]
    normalized, identities = _normalise_model_rows(
        rows,
        mode=mode,
        covariates=policy.covariates,
        expected_analysis_method=expected_method,
    )
    if mode == "repeated":
        _ensure_patient_response_consistent(normalized)
    if mode == "randomized_arm":
        expected_keys = {"comparative_estimand_id", "randomization_verified", "receipt_sha256"}
        if not isinstance(randomization, Mapping) or set(randomization) != expected_keys:
            raise PermissionError("Randomized-arm release needs a bound comparative-estimand receipt")
        bindings = released_inputs.manifest["scope_bindings"]
        if (
            randomization["randomization_verified"] is not True
            or not randomization["comparative_estimand_id"]
            or bindings["comparative_estimand_id"] != randomization["comparative_estimand_id"]
            or bindings["randomization_receipt_sha256"] != randomization["receipt_sha256"]
        ):
            raise PermissionError("Randomized-arm release does not bind its within-study randomization admission")
        if {row["arm"] for row in normalized} - {"ICI_ONLY", "COMBINATION"}:
            raise ValueError("Randomized-arm model rows must use the explicit ICI_ONLY/COMBINATION arms")

    if mode == "two_timepoint":
        if "pre_value" in policy.covariates or "baseline" in {item.casefold() for item in policy.covariates}:
            raise ValueError("Primary change covariates cannot include baseline expression")
        config = {
            "covariates": list(policy.covariates),
            "confidence_level": policy.confidence_level,
            "min_per_response_group": policy.min_per_response_group,
            "sensitivity_modes": list(policy.sensitivity_modes),
            "tighter_timing_max_deviation_days": policy.tighter_timing_max_deviation_days,
            "policy_status": "USER_RECORD_BOUND",
            "requested_models": ["ancova_sensitivity"] if route == "ancova" else None,
            "method_ids": {
                "delta": policy.delta_method_id,
                "ancova": policy.ancova_method_id,
                "df": policy.df_method_id,
                "same_lesion_sensitivity": policy.same_lesion_sensitivity_method_id,
                "exact_day_sensitivity": policy.exact_day_sensitivity_method_id,
                "tighter_timing_sensitivity": policy.tighter_timing_sensitivity_method_id,
            },
        }
        mode_name = "fit_two_timepoint"
        analysis_family = "observational_response"
    elif mode == "repeated":
        if len(policy.repeated_windows) < 2 or policy.repeated_windows[0] != "baseline":
            raise ValueError("N13 repeated-window policy must declare baseline first and every admitted window")
        observed = {str(row.get("window") or "") for row in normalized}
        if observed != set(policy.repeated_windows):
            raise ValueError("Released repeated model rows do not match the exact N13 window set")
        config = {
            "window_levels": list(policy.repeated_windows),
            "repeated_selection_mode": policy.repeated_selection_mode,
            "min_repeated_patients": policy.min_repeated_patients,
            "min_per_response_group": policy.min_per_response_group,
            "covariates": list(policy.covariates),
            "confidence_level": policy.confidence_level,
            "policy_status": "USER_RECORD_BOUND",
            "method_ids": {"repeated": policy.repeated_method_id, "df": policy.df_method_id},
        }
        mode_name = "fit_repeated"
        analysis_family = "observational_response"
    else:
        config = {
            "comparative_estimand_id": randomization["comparative_estimand_id"],
            "randomization_verified": True,
            "min_per_randomized_arm": policy.min_per_randomized_arm,
            "covariates": list(policy.covariates),
            "confidence_level": policy.confidence_level,
            "policy_status": "USER_RECORD_BOUND",
            "method_ids": {
                "randomized_arm": policy.randomized_arm_method_id,
                "df": policy.df_method_id,
            },
        }
        mode_name = "fit_randomized_arm"
        analysis_family = "randomized_arm"
    return _run_model(
        normalized,
        identities,
        policy,
        output_dir=output_dir,
        retention_dir=retention_dir,
        runner=runner,
        mode=mode_name,
        provenance_manifest=released_inputs.manifest_path,
        config=config,
        expected_outputs=("effects.tsv", "within_group_deltas.tsv", "model_support.tsv"),
        analysis_family=analysis_family,
        released_inputs=released_inputs,
        allow_outcomes=allow_outcomes,
        release_policy_payload=policy_payload,
    )


def model_effects_for_synthesis(results: Iterable[AnalysisResult | Mapping]) -> list[dict]:
    """Select model effects with synthesis roles, keeping their emitted identities intact."""
    selected = []
    allowed_roles = {
        "central_change_contrast",
        "prespecified_same_lesion_sensitivity",
        "prespecified_exact_day_sensitivity",
        "prespecified_tighter_timing_sensitivity",
        "randomized_within_study_comparative_estimand",
        "one_way_longitudinal_corroboration",
    }
    for item in results:
        rows = item.effects if isinstance(item, AnalysisResult) else [item]
        for raw in rows:
            if raw.get("effect_role") not in allowed_roles:
                continue
            row = {key: raw.get(key) for key in _SYNTHESIS_COLUMNS}
            for field in ("estimate", "se", "ci_lb", "ci_ub", "p_value"):
                value = row[field]
                row[field] = None if value in (None, "", "NA") else float(value)
            row["status"] = str(raw.get("status") or "NOT_ESTIMABLE")
            row["reason"] = str(raw.get("reason") or "")
            selected.append(row)
    if not selected:
        raise ValueError("No model output rows have an admitted synthesis role")
    selected.sort(key=lambda row: (row["unit"], row["study"], row["window_id"]))
    return selected


def write_synthetic_analysis_manifest(
    path: Path | str,
    rows: Sequence[Mapping],
    *,
    study_ids: Sequence[str],
    kind: str = "a_long_analysis_input",
    overlap_receipts: Sequence[Mapping] | None = None,
) -> dict:
    """Write hash-matched provenance for invented model or synthesis rows."""
    studies = tuple(sorted({str(value) for value in study_ids}))
    _guard_study_ids(studies)
    if not studies:
        raise ValueError("Synthetic provenance requires explicit study IDs")
    records = [dict(row) for row in rows]
    _check_study_ids(
        records,
        studies,
        key="study" if kind == "a_long_synthesis_input" else "study_id",
    )
    from tools.a_meta.provenance import write_synthetic_fixture_manifest

    path = guard_path(path, "synthetic analysis manifest output")
    if path.exists():
        raise FileExistsError("Synthetic analysis manifest output already exists")
    if kind == "a_long_synthesis_input" and overlap_receipts is None:
        raise ValueError("Synthetic synthesis provenance must bind pairwise overlap receipts")
    manifest = write_synthetic_fixture_manifest(
        path,
        kind=kind,
        payload=records,
        cohort_ids=studies,
    )
    if kind == "a_long_synthesis_input":
        manifest["overlap_receipts_sha256"] = canonical_sha256([dict(row) for row in overlap_receipts or ()])
        with path.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def fit_two_timepoint(
    rows: Iterable[Mapping],
    *,
    study_id: str,
    provenance_manifest: Path | str,
    policy: N13Policy,
    acceptance: N13Acceptance | None,
    output_dir: Path | str,
    retention_dir: Path | str,
    runner=None,
) -> AnalysisResult:
    """Fit primary change and ANCOVA sensitivity on invented rows only."""
    _preflight_analysis_paths(provenance_manifest, output_dir, retention_dir)
    _guard_study_ids((study_id,))
    fixture_policy = _validate_n13(policy, acceptance, route="two_timepoint")
    if "pre_value" in policy.covariates or "baseline" in {value.casefold() for value in policy.covariates}:
        raise ValueError("Primary change covariates cannot include baseline expression")
    manifest = _read_fixture_manifest(provenance_manifest, "a_long_analysis_input", (study_id,))
    records = [dict(row) for row in rows]
    _check_study_ids(records, (study_id,))
    _verify_payload_hash(records, manifest)
    normalized, identities = _normalise_model_rows(
        records,
        mode="two_timepoint",
        covariates=policy.covariates,
        expected_analysis_method=policy.delta_method_id,
    )
    return _run_model(
        normalized,
        identities,
        policy,
        output_dir=output_dir,
        retention_dir=retention_dir,
        runner=runner,
        mode="fit_two_timepoint",
        provenance_manifest=provenance_manifest,
        config={
            "covariates": list(policy.covariates),
            "confidence_level": policy.confidence_level,
            "min_per_response_group": policy.min_per_response_group,
            "sensitivity_modes": list(policy.sensitivity_modes),
            "tighter_timing_max_deviation_days": policy.tighter_timing_max_deviation_days,
            "policy_status": _policy_status(policy, fixture_policy),
            "method_ids": {
                "delta": policy.delta_method_id,
                "ancova": policy.ancova_method_id,
                "df": policy.df_method_id,
                "same_lesion_sensitivity": policy.same_lesion_sensitivity_method_id,
                "exact_day_sensitivity": policy.exact_day_sensitivity_method_id,
                "tighter_timing_sensitivity": policy.tighter_timing_sensitivity_method_id,
            },
        },
        expected_outputs=("effects.tsv", "within_group_deltas.tsv", "model_support.tsv"),
    )


def fit_repeated_windows(
    rows: Iterable[Mapping],
    *,
    study_id: str,
    provenance_manifest: Path | str,
    policy: N13Policy,
    acceptance: N13Acceptance | None,
    output_dir: Path | str,
    retention_dir: Path | str,
    runner=None,
) -> AnalysisResult:
    """Fit response-by-window mixed models for invented, complete patients."""
    _preflight_analysis_paths(provenance_manifest, output_dir, retention_dir)
    _guard_study_ids((study_id,))
    fixture_policy = _validate_n13(policy, acceptance, route="repeated")
    if len(policy.repeated_windows) < 2 or policy.repeated_windows[0] != "baseline":
        raise ValueError("N13 must declare baseline first and every approved repeated window")
    manifest = _read_fixture_manifest(provenance_manifest, "a_long_analysis_input", (study_id,))
    records = [dict(row) for row in rows]
    _check_study_ids(records, (study_id,))
    _verify_payload_hash(records, manifest)
    approved_windows = set(policy.repeated_windows)
    observed_windows = {str(row.get("window") or "") for row in records}
    if observed_windows - approved_windows:
        raise ValueError("Repeated-window input contains windows outside the accepted N13 set")
    normalized, identities = _normalise_model_rows(
        records,
        mode="repeated",
        covariates=policy.covariates,
        expected_analysis_method=policy.repeated_method_id,
    )
    _ensure_patient_response_consistent(normalized)
    return _run_model(
        normalized,
        identities,
        policy,
        output_dir=output_dir,
        retention_dir=retention_dir,
        runner=runner,
        mode="fit_repeated",
        provenance_manifest=provenance_manifest,
        config={
            "window_levels": list(policy.repeated_windows),
            "repeated_selection_mode": policy.repeated_selection_mode,
            "min_repeated_patients": policy.min_repeated_patients,
            "min_per_response_group": policy.min_per_response_group,
            "covariates": list(policy.covariates),
            "confidence_level": policy.confidence_level,
            "policy_status": _policy_status(policy, fixture_policy),
            "method_ids": {
                "repeated": policy.repeated_method_id,
                "df": policy.df_method_id,
            },
        },
        expected_outputs=("effects.tsv", "within_group_deltas.tsv", "model_support.tsv"),
    )


def fit_randomized_arm(
    rows: Iterable[Mapping],
    *,
    study_id: str,
    provenance_manifest: Path | str,
    policy: N13Policy,
    acceptance: N13Acceptance | None,
    admission: RandomizationAdmission,
    output_dir: Path | str,
    retention_dir: Path | str,
    runner=None,
) -> AnalysisResult:
    """Estimate an admitted within-study randomized arm change contrast."""
    _preflight_analysis_paths(provenance_manifest, output_dir, retention_dir)
    _guard_study_ids((study_id,))
    fixture_policy = _validate_n13(policy, acceptance, route="randomized_arm")
    if (
        admission is None
        or not admission.randomization_verified
        or not admission.comparative_estimand_id
        or not admission.record_ref
    ):
        raise ValueError("Randomized-arm analysis requires explicit randomization and comparative-estimand admission")
    if admission.fixture_only is False and admission.record_ref != policy.decision_ref:
        raise ValueError("Randomized-arm admission must reference the accepted N13 record")
    if admission.fixture_only and admission.record_ref == "" :
        raise ValueError("Fixture randomized-arm admission requires a record label")
    manifest = _read_fixture_manifest(provenance_manifest, "a_long_analysis_input", (study_id,))
    records = [dict(row) for row in rows]
    _check_study_ids(records, (study_id,))
    _verify_payload_hash(records, manifest)
    normalized, identities = _normalise_model_rows(
        records,
        mode="randomized_arm",
        covariates=policy.covariates,
        expected_analysis_method=policy.randomized_arm_method_id,
    )
    arms = {row["arm"] for row in normalized if row["arm"]}
    if not arms <= {"ICI_ONLY", "COMBINATION"}:
        raise ValueError("Randomized-arm labels must be ICI_ONLY or COMBINATION")
    return _run_model(
        normalized,
        identities,
        policy,
        output_dir=output_dir,
        retention_dir=retention_dir,
        runner=runner,
        mode="fit_randomized_arm",
        provenance_manifest=provenance_manifest,
        config={
            "comparative_estimand_id": admission.comparative_estimand_id,
            "randomization_verified": True,
            "min_per_randomized_arm": policy.min_per_randomized_arm,
            "covariates": list(policy.covariates),
            "confidence_level": policy.confidence_level,
            "policy_status": _policy_status(policy, fixture_policy),
            "method_ids": {
                "randomized_arm": policy.randomized_arm_method_id,
                "df": policy.df_method_id,
            },
        },
        expected_outputs=("effects.tsv", "within_group_deltas.tsv", "model_support.tsv"),
        analysis_family="randomized_arm",
    )


def synthesize_effects(
    rows: Iterable[Mapping],
    *,
    overlap_receipts: Iterable[Mapping],
    study_ids: Sequence[str],
    provenance_manifest: Path | str,
    policy: N13Policy,
    acceptance: N13Acceptance | None,
    output_dir: Path | str,
    retention_dir: Path | str,
    runner=None,
) -> AnalysisResult:
    """Synthesize only compatible study-first effects and scope FDR by family."""
    _preflight_analysis_paths(provenance_manifest, output_dir, retention_dir)
    studies = tuple(sorted({str(value) for value in study_ids}))
    _guard_study_ids(studies)
    fixture_policy = _validate_n13(policy, acceptance, route="synthesis")
    manifest = _read_fixture_manifest(provenance_manifest, "a_long_synthesis_input", studies)
    records = [dict(row) for row in rows]
    overlap_rows = [dict(row) for row in overlap_receipts]
    if canonical_sha256(overlap_rows) != manifest.get("overlap_receipts_sha256"):
        raise ValueError("Synthetic synthesis manifest does not match the pairwise overlap receipts")
    _check_study_ids(records, studies, key="study")
    _verify_payload_hash(records, manifest)
    normalized, groups = _normalise_synthesis_rows(records, studies, overlap_rows)

    output_dir = prepare_output_directory(_safe_patient_output_dir(output_dir))
    retention_dir = validate_output_directory(_safe_patient_output_dir(retention_dir))
    input_path = output_dir / "synthesis_input.tsv"
    _write_tsv(input_path, normalized, tuple(normalized[0]) if normalized else _SYNTHESIS_COLUMNS)
    group_path = output_dir / "synthesis_groups.tsv"
    _write_tsv(
        group_path,
        groups,
        tuple(groups[0]) if groups else ("analysis_group_id", "preflight_reason", "k", "n_input", "n_excluded", "independence_status"),
    )
    overlap_path = output_dir / "overlap_receipts.tsv"
    _write_tsv(overlap_path, overlap_rows, _OVERLAP_RECEIPT_COLUMNS)
    expected = ("synthesis.tsv",)
    bridge_manifest_path = output_dir.parent / f".{output_dir.name}_r_provenance.json"
    bridge_manifest_path = guard_path(bridge_manifest_path, "synthetic R provenance manifest")
    check_path_separation(
        inputs={"R provenance manifest": bridge_manifest_path},
        outputs={"analysis output": output_dir, "R retention": retention_dir},
    )
    if bridge_manifest_path.exists():
        raise FileExistsError("Synthetic R provenance manifest already exists")
    bridge_manifest = _write_synthetic_r_manifest(
        bridge_manifest_path,
        kind="a_long_synthesis_input",
        source_paths={"effects": input_path, "overlap_receipts": overlap_path, "groups": group_path},
        cohorts=studies,
        identity_fields={
            "effects": ["study"],
            "overlap_receipts": ["study_a", "study_b"],
            "groups": ["analysis_group_id"],
        },
    )
    synthesis_config = {
        "mode": "synthesize",
        "expected_outputs": list(expected),
        "method_id": policy.meta_method_id,
        "confidence_level": policy.confidence_level,
        "minimum_k_for_pooling": policy.min_meta_k_pool,
        "policy_status": _policy_status(policy, fixture_policy),
    }
    synthesis_config["boundary"] = {
        "data_classification": "synthetic",
        "manifest_kind": "a_long_synthesis_input",
        "manifest_sha256": sha256_file(bridge_manifest_path, label="synthetic R provenance manifest"),
        "cohorts": list(studies),
        "source_inputs": ["effects", "overlap_receipts", "groups"],
        "input_sha256": {
            "effects": sha256_file(input_path, label="invented synthesis effects"),
            "overlap_receipts": sha256_file(overlap_path, label="invented synthesis overlap receipts"),
            "groups": sha256_file(group_path, label="invented synthesis groups"),
        },
        "input_fields": {
            "effects": list(normalized[0]) if normalized else list(_SYNTHESIS_COLUMNS),
            "overlap_receipts": list(overlap_rows[0]) if overlap_rows else list(_OVERLAP_RECEIPT_COLUMNS),
            "groups": list(groups[0]) if groups else ["analysis_group_id", "preflight_reason", "k", "n_input", "n_excluded", "independence_status"],
        },
        "identity_fields": bridge_manifest["identity_fields"],
        "permitted_fields": [
            *(f"effects:{name}" for name in (list(normalized[0]) if normalized else _SYNTHESIS_COLUMNS)),
            *(f"overlap_receipts:{name}" for name in (list(overlap_rows[0]) if overlap_rows else _OVERLAP_RECEIPT_COLUMNS)),
            *(f"groups:{name}" for name in (list(groups[0]) if groups else ("analysis_group_id", "preflight_reason", "k", "n_input", "n_excluded", "independence_status"))),
        ],
        "policy_sha256": canonical_sha256(asdict(policy)),
        "retention_dir": str(retention_dir),
    }
    result = run_r(
        _SCRIPT,
        {
            "effects": input_path,
            "overlap_receipts": overlap_path,
            "groups": group_path,
            "provenance_manifest": bridge_manifest_path,
        },
        synthesis_config,
        output_dir / "R",
        runner=runner,
        retention_dir=retention_dir,
    )
    effects = _read_tsv(result.outputs["synthesis.tsv"])
    _apply_scoped_fdr(effects, policy=policy, q=0.10)
    out_path = output_dir / "a_long_synthesis.tsv"
    _write_tsv(out_path, effects, tuple(effects[0]) if effects else ())
    return AnalysisResult(
        effects=effects,
        within_group_deltas=[],
        support={
            "data_classification": "synthetic",
            "policy_status": _policy_status(policy, fixture_policy),
            "meta_method_id": policy.meta_method_id,
            "study_first": "true",
            "cross_family_pooling": "forbidden",
        },
        paths={
            "input": input_path,
            "overlap_receipts": overlap_path,
            "groups": group_path,
            "synthesis": out_path,
            "r_manifest": output_dir / "R" / "manifest.json",
        },
        policy_status=_policy_status(policy, fixture_policy),
    )


def run_released_synthesis(
    *,
    released_inputs,
    policy_payload: Mapping,
    output_dir: Path | str,
    retention_dir: Path | str,
    allow_outcomes: bool = False,
    runner=None,
) -> AnalysisResult:
    """Synthesize released study effects after validating the scoped N13 record."""
    if allow_outcomes is not True:
        raise PermissionError("A-LONG released synthesis requires allow_outcomes=True")
    if not is_released_inputs(
        released_inputs,
        release_scope="N13_SYNTHESIS",
        operation="synthesize_effects",
    ):
        raise PermissionError("A-LONG synthesis needs validated N13_SYNTHESIS inputs")
    record = released_inputs.authorization.record
    if canonical_sha256(policy_payload) != record.get("policy_sha256"):
        raise PermissionError("N13 synthesis policy differs from the approved user-release hash")
    studies = tuple(sorted(record.get("cohorts", ())))
    if not studies or len(set(studies)) != len(studies) or any(is_locked_study(study) for study in studies):
        raise PermissionError("N13 synthesis cohort identity is empty, duplicated, or protected")
    if set(released_inputs.tables) != {"effects", "overlap_receipts"}:
        raise ValueError("Released synthesis requires effects and pairwise overlap-receipt tables")
    if (
        released_inputs.manifest["scope_bindings"]["source_overlap_contract_sha256"]
        != policy_payload.get("source_overlap_contract_sha256")
    ):
        raise PermissionError("N13 source-overlap contract hash differs from the accepted policy")
    payload = dict(policy_payload)
    allowed_policy_fields = {field.name for field in fields(N13Policy)}
    if set(payload) != allowed_policy_fields:
        raise ValueError("Released N13 synthesis policy must supply every numerical field exactly")
    for name in ("covariates", "repeated_windows", "m5m6_family_members", "sensitivity_modes"):
        payload[name] = tuple(payload[name])
    if payload["panel_family_members"] is not None:
        payload["panel_family_members"] = {
            name: tuple(members) for name, members in payload["panel_family_members"].items()
        }
    policy = N13Policy(**payload)
    decision = record["decision"]["identity"]
    acceptance = N13Acceptance(
        decision_id=decision,
        record_ref=released_inputs.authorization.record_sha256,
        authorization=released_inputs.authorization,
    )
    fixture_policy = _validate_n13(
        policy,
        acceptance,
        route="synthesis",
        authorized_policy_sha256=record["policy_sha256"],
    )
    records = [dict(row) for row in released_inputs.tables["effects"]]
    overlap_rows = [dict(row) for row in released_inputs.tables["overlap_receipts"]]
    _check_study_ids(records, studies, key="study")
    normalized, groups = _normalise_synthesis_rows(records, studies, overlap_rows)

    output_dir = _safe_real_output_dir(output_dir)
    retention_dir = _safe_real_output_dir(retention_dir)
    check_path_separation(
        inputs={
            "R script": _SCRIPT,
            "release manifest": released_inputs.manifest_path,
            "user-release record": released_inputs.authorization.record_path,
            **{f"released {name}": path for name, path in released_inputs.source_paths.items()},
        },
        outputs={"synthesis output": output_dir, "R retention": retention_dir},
    )
    output_dir = prepare_output_directory(output_dir)
    retention_dir = prepare_output_directory(retention_dir)
    effects_path = output_dir / "synthesis_input.tsv"
    overlap_path = output_dir / "overlap_receipts.tsv"
    groups_path = output_dir / "synthesis_groups.tsv"
    _write_tsv(effects_path, normalized, tuple(normalized[0]))
    _write_tsv(overlap_path, overlap_rows, _OVERLAP_RECEIPT_COLUMNS)
    _write_tsv(groups_path, groups, tuple(groups[0]))
    derived_inputs = {
        "effects": effects_path,
        "overlap_receipts": overlap_path,
        "groups": groups_path,
    }
    input_fields = {
        "effects": list(normalized[0]),
        "overlap_receipts": list(overlap_rows[0]) if overlap_rows else list(_OVERLAP_RECEIPT_COLUMNS),
        "groups": list(groups[0]),
    }
    config = {
        "mode": "synthesize",
        "expected_outputs": ["synthesis.tsv"],
        "method_id": policy.meta_method_id,
        "confidence_level": policy.confidence_level,
        "minimum_k_for_pooling": policy.min_meta_k_pool,
        "policy_status": "USER_RECORD_BOUND",
        "boundary": {
            "data_classification": "real",
            "manifest_kind": "a_long_release_input_manifest_v1",
            "manifest_sha256": released_inputs.manifest_sha256,
            "cohorts": list(studies),
            "source_inputs": sorted(released_inputs.source_paths),
            "source_paths": {name: str(path) for name, path in released_inputs.source_paths.items()},
            "source_sha256": released_inputs.authorization.source_sha256,
            "source_identity_fields": released_inputs.manifest["identity_fields"],
            "source_field_maps": released_inputs.manifest["field_maps"],
            "scope_bindings": released_inputs.manifest["scope_bindings"],
            "input_sha256": {
                name: sha256_file(path, label=f"released synthesis {name}")
                for name, path in derived_inputs.items()
            },
            "input_fields": input_fields,
            "permitted_fields": record["permitted_fields"],
            "policy_sha256": record["policy_sha256"],
            "policy_payload": dict(policy_payload),
            "release_scope": record["release_scope"],
            "operation": record["operation"],
            "allow_outcomes": allow_outcomes,
            "release_record_path": str(released_inputs.authorization.record_path),
            "release_record_sha256": released_inputs.authorization.record_sha256,
            "release_root": str(released_inputs.authorization.root),
            "decisions_dir": str(released_inputs.authorization.decisions_dir),
            "retention_dir": str(retention_dir),
        },
    }
    result = run_r(
        _SCRIPT,
        {**derived_inputs, "provenance_manifest": released_inputs.manifest_path},
        config,
        output_dir / "R",
        runner=runner,
        retention_dir=retention_dir,
    )
    effects = _read_tsv(result.outputs["synthesis.tsv"])
    _apply_scoped_fdr(effects, policy=policy, q=0.10)
    product_path = output_dir / "a_long_synthesis.tsv"
    _write_tsv(product_path, effects, tuple(effects[0]) if effects else ())
    support_path = output_dir / "synthesis_support.tsv"
    _write_tsv(support_path, groups, tuple(groups[0]))
    support = {
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "policy_status": "USER_RECORD_BOUND",
        "meta_method_id": policy.meta_method_id,
        "study_first": "true",
        "cross_family_pooling": "forbidden",
    }
    return AnalysisResult(
        effects=effects,
        within_group_deltas=[],
        support=support,
        paths={
            "input": effects_path,
            "overlap_receipts": overlap_path,
            "groups": support_path,
            "synthesis": product_path,
            "r_manifest": output_dir / "R" / "manifest.json",
        },
        policy_status="USER_RECORD_BOUND",
    )


def _run_model(
    rows,
    identities,
    policy,
    *,
    output_dir,
    retention_dir,
    runner,
    mode,
    provenance_manifest,
    config,
    expected_outputs,
    analysis_family="observational_response",
    released_inputs=None,
    allow_outcomes: bool = False,
    release_policy_payload: Mapping | None = None,
):
    if released_inputs is not None:
        if allow_outcomes is not True:
            raise PermissionError("A-LONG real model bridge requires allow_outcomes=True")
        output_dir = _safe_real_output_dir(output_dir)
        retention_dir = _safe_real_output_dir(retention_dir)
    else:
        output_dir = _safe_patient_output_dir(output_dir)
        retention_dir = _safe_patient_output_dir(retention_dir)
    check_inputs = {"R script": _SCRIPT}
    if released_inputs is not None:
        check_inputs["release manifest"] = released_inputs.manifest_path
        check_inputs["user-release record"] = released_inputs.authorization.record_path
        check_inputs.update({f"released {name}": path for name, path in released_inputs.source_paths.items()})
    else:
        check_inputs["provenance manifest"] = provenance_manifest
    check_path_separation(
        inputs=check_inputs,
        outputs={"analysis output": output_dir, "R retention": retention_dir},
    )
    output_dir = prepare_output_directory(output_dir)
    retention_dir = prepare_output_directory(retention_dir)
    input_path = output_dir / "model_input.tsv"
    _write_tsv(input_path, rows, tuple(rows[0]) if rows else ())
    input_fields = list(rows[0]) if rows else []
    if released_inputs is None:
        bridge_manifest = output_dir.parent / f".{output_dir.name}_r_provenance.json"
        bridge_manifest = guard_path(bridge_manifest, "synthetic R provenance manifest")
        check_path_separation(
            inputs={"R provenance manifest": bridge_manifest},
            outputs={"analysis output": output_dir, "R retention": retention_dir},
        )
        if bridge_manifest.exists():
            raise FileExistsError("Synthetic R provenance manifest already exists")
        boundary_manifest = _write_synthetic_r_manifest(
            bridge_manifest,
            kind="a_long_analysis_input",
            source_paths={"design": input_path},
            cohorts=sorted({row["study_id"] for row in rows}),
            identity_fields={"design": ["study_id"]},
        )
        boundary = {
            "data_classification": "synthetic",
            "manifest_kind": "a_long_analysis_input",
            "manifest_sha256": sha256_file(bridge_manifest, label="synthetic R provenance manifest"),
            "cohorts": sorted({row["study_id"] for row in rows}),
            "source_inputs": ["design"],
            "input_sha256": {"design": sha256_file(input_path, label="invented model design")},
            "input_fields": {"design": input_fields},
            "identity_fields": boundary_manifest["identity_fields"],
            "permitted_fields": [f"design:{name}" for name in input_fields],
            "policy_sha256": canonical_sha256(asdict(policy)),
            "retention_dir": str(retention_dir),
        }
        bridge_inputs = {"design": input_path, "provenance_manifest": bridge_manifest}
        classification = "synthetic"
    else:
        if not is_released_inputs(
            released_inputs,
            release_scope=released_inputs.authorization.record["release_scope"],
            operation=released_inputs.authorization.record["operation"],
        ):
            raise PermissionError("A-LONG R bridge input no longer matches its validated release receipt")
        boundary = {
            "data_classification": "real",
            "manifest_kind": "a_long_release_input_manifest_v1",
            "manifest_sha256": released_inputs.manifest_sha256,
            "cohorts": released_inputs.authorization.record["cohorts"],
            "source_inputs": sorted(released_inputs.source_paths),
            "source_paths": {name: str(path) for name, path in released_inputs.source_paths.items()},
            "source_sha256": released_inputs.authorization.source_sha256,
            "source_identity_fields": released_inputs.manifest["identity_fields"],
            "source_field_maps": released_inputs.manifest["field_maps"],
            "scope_bindings": released_inputs.manifest["scope_bindings"],
            "input_sha256": {"design": sha256_file(input_path, label="released model design")},
            "input_fields": {"design": input_fields},
            "permitted_fields": released_inputs.authorization.record["permitted_fields"],
            "policy_sha256": released_inputs.authorization.record["policy_sha256"],
            "policy_payload": dict(release_policy_payload or {}),
            "release_scope": released_inputs.authorization.record["release_scope"],
            "operation": released_inputs.authorization.record["operation"],
            "allow_outcomes": allow_outcomes,
            "release_record_path": str(released_inputs.authorization.record_path),
            "release_record_sha256": released_inputs.authorization.record_sha256,
            "release_root": str(released_inputs.authorization.root),
            "decisions_dir": str(released_inputs.authorization.decisions_dir),
            "retention_dir": str(retention_dir),
        }
        bridge_inputs = {"design": input_path, "provenance_manifest": released_inputs.manifest_path}
        classification = "real"
    config["boundary"] = boundary
    config["identities"] = identities
    config["analysis_family"] = analysis_family
    result = run_r(
        _SCRIPT,
        bridge_inputs,
        {"mode": mode, "expected_outputs": list(expected_outputs), **config},
        output_dir / "R",
        runner=runner,
        retention_dir=retention_dir,
    )
    effects = _read_tsv(result.outputs["effects.tsv"])
    within = _read_tsv(result.outputs["within_group_deltas.tsv"])
    support_rows = _read_tsv(result.outputs["model_support.tsv"])
    for row in support_rows:
        row.update({
            "data_classification": "synthetic" if classification == "synthetic" else "PRIVATE_PATIENT_LEVEL",
            "policy_status": config["policy_status"],
            "analysis_family": analysis_family,
        })
    support = dict(support_rows[0]) if support_rows else {
        "data_classification": "synthetic" if classification == "synthetic" else "PRIVATE_PATIENT_LEVEL",
        "policy_status": config["policy_status"],
        "analysis_family": analysis_family,
    }
    effects_path = output_dir / "a_long_effects.tsv"
    within_path = output_dir / "within_group_deltas.tsv"
    _write_tsv(effects_path, effects, tuple(effects[0]) if effects else ())
    _write_tsv(within_path, within, tuple(within[0]) if within else ())
    support_path = output_dir / "model_support.tsv"
    _write_tsv(
        support_path,
        support_rows,
        tuple(support_rows[0]) if support_rows else tuple(support),
    )
    longitudinal_rows = _longitudinal_support_rows(rows, support_rows, effects)
    longitudinal_path = output_dir / "longitudinal_support.tsv"
    _write_tsv(
        longitudinal_path,
        longitudinal_rows,
        tuple(longitudinal_rows[0]) if longitudinal_rows else (
            "study_id", "unit", "window_id", "record_type", "model", "effect_role",
            "n_pairs", "n_patients_input", "n_patients_used", "n_observations_used", "n_observations_fitted",
            "n_R", "n_NR", "n_arm_ici", "n_arm_combination", "status", "reason",
            "support_role",
        ),
    )
    return AnalysisResult(
        effects=effects,
        within_group_deltas=within,
        support=support,
        paths={
            "input": input_path,
            "effects": effects_path,
            "within_group_deltas": within_path,
            "support": support_path,
            "longitudinal_support": longitudinal_path,
            "r_manifest": output_dir / "R" / "manifest.json",
        },
        policy_status=config["policy_status"],
    )


def _longitudinal_support_rows(rows, support_rows, effects):
    grouped = defaultdict(list)
    for row in rows:
        window = str(row.get("window") or row.get("window_id") or "baseline_to_on")
        grouped[(str(row["study_id"]), str(row["unit"]), window)].append(row)
    support_by_unit = {row.get("unit"): row for row in support_rows}
    output = []
    for (study, unit, window), items in sorted(grouped.items()):
        support = support_by_unit.get(unit, {})
        output.append({
            "study_id": study,
            "unit": unit,
            "window_id": window,
            "record_type": "pairing_model_input",
            "model": "",
            "effect_role": "",
            "n_pairs": len({str(row["pair_id"]) for row in items}),
            "n_patients_input": support.get("n_patients_input", len({row["patient_key"] for row in items})),
            "n_patients_used": support.get("n_patients_used", "NA"),
            "n_observations_used": support.get("n_observations_used", len(items)),
            "n_observations_fitted": support.get("n_observations_used", len(items)),
            "n_R": support.get("n_R", "NA"),
            "n_NR": support.get("n_NR", "NA"),
            "n_arm_ici": support.get("n_arm_ici", "NA"),
            "n_arm_combination": support.get("n_arm_combination", "NA"),
            "status": support.get("status", "INPUT_RETAINED"),
            "reason": support.get("reason", ""),
            "support_role": "pairing_model_input_support",
        })
    for effect in effects:
        model = str(effect.get("model", ""))
        is_two_timepoint = model.startswith("delta_") or model == "ancova_sensitivity"
        is_randomized = model == "randomized_arm_change"
        n_r = int(effect.get("n_R") or 0)
        n_nr = int(effect.get("n_NR") or 0)
        n_ici = int(effect.get("n_arm_ici") or 0)
        n_combination = int(effect.get("n_arm_combination") or 0)
        patients_used = n_ici + n_combination if is_randomized else n_r + n_nr
        input_support = support_by_unit.get(str(effect.get("unit", "")), {})
        output.append({
            "study_id": str(effect.get("study") or (rows[0]["study_id"] if rows else "")),
            "unit": str(effect.get("unit", "")),
            "window_id": str(effect.get("window_id") or "baseline_to_on"),
            "record_type": "analysis_effect",
            "model": model,
            "effect_role": str(effect.get("effect_role", "")),
            "n_pairs": effect.get("n") if is_two_timepoint or is_randomized else None,
            "n_patients_input": input_support.get("n_patients_input", "NA"),
            "n_patients_used": patients_used,
            "n_observations_used": effect.get("n_observations_contrast", effect.get("n", "NA")),
            "n_observations_fitted": effect.get("n_observations_fitted", effect.get("n", "NA")),
            "n_R": n_r if not is_randomized else "NA",
            "n_NR": n_nr if not is_randomized else "NA",
            "n_arm_ici": n_ici if is_randomized else "NA",
            "n_arm_combination": n_combination if is_randomized else "NA",
            "status": str(effect.get("status", "NOT_ESTIMABLE")),
            "reason": str(effect.get("reason", "")),
            "support_role": str(effect.get("effect_role") or "analysis_effect"),
        })
    return output


def _normalise_model_rows(records, *, mode, covariates, expected_analysis_method):
    if not records:
        raise ValueError("Analysis requires invented rows")
    metadata = {}
    normalized = []
    required = {
        "study_id", "patient_key", "pair_id", "unit", *_IDENTITY_COLUMNS,
    }
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]*", str(name)) for name in covariates):
        raise ValueError("N13 covariates must be explicit simple column names")
    reserved = {"study_id", "patient_key", "pair_id", "unit", "response", "arm", "window", "value"}
    if reserved & set(covariates):
        raise ValueError("N13 covariates cannot replace model identity, response, arm, or repeated-window terms")
    required |= {"pre_value", "on_value"} if mode in {"two_timepoint", "randomized_arm"} else {"window", "value"}
    if mode != "randomized_arm":
        required.add("response")
    if mode == "randomized_arm":
        required.add("arm")
    required.update(covariates)
    for raw in records:
        if not required <= raw.keys():
            raise ValueError("Analysis row is missing explicitly named model or effect-identity fields")
        study_id = str(raw["study_id"])
        identity = {key: str(raw[key]) for key in _IDENTITY_COLUMNS}
        unit = str(raw["unit"])
        if not unit or any(not value for value in identity.values()):
            raise ValueError("Analysis identity fields must be explicit and non-empty")
        if identity["overlap_status"] not in {"DISJOINT_VERIFIED", "OVERLAPPING", "UNRESOLVED"}:
            raise ValueError("Analysis overlap status must be an explicit source-contract value")
        if len(identity["overlap_receipt_id"]) != 64 or any(
            character not in "0123456789abcdef" for character in identity["overlap_receipt_id"]
        ):
            raise ValueError("Overlap receipt identity must be a lowercase SHA256")
        if identity["analysis_method_id"] != expected_analysis_method:
            raise ValueError("Model method identity does not match the explicit N13 method")
        if "count" in identity["effect_scale_id"].casefold():
            raise ValueError("Count-derived precision requires the unavailable voom/dream route; no OLS fallback is allowed")
        if unit in metadata and metadata[unit] != identity:
            raise ValueError("A feature unit cannot mix method, endpoint, regimen, window, assay, or effect scale")
        metadata[unit] = identity
        patient_key = _opaque_patient_key(study_id, str(raw["patient_key"]))
        row = {
            "study_id": study_id,
            "patient_key": patient_key,
            "pair_id": str(raw["pair_id"]),
            "unit": unit,
            **identity,
        }
        for name in (
            "same_lesion", "pre_day_precision", "on_day_precision", "timing_ambiguity",
        ):
            row[name] = "" if raw.get(name) is None else str(raw.get(name)).strip()
        for name in ("pre_day_numeric", "on_day_numeric", "day_distance_to_target", "pair_day_distance"):
            row[name] = _optional_numeric_cell(raw.get(name))
        if not row["pair_id"]:
            raise ValueError("Pair key must be explicit")
        if mode in {"two_timepoint", "randomized_arm"}:
            row["pre_value"] = _numeric_cell(raw.get("pre_value"))
            row["on_value"] = _numeric_cell(raw.get("on_value"))
        else:
            row["window"] = str(raw.get("window") or "")
            row["value"] = _numeric_cell(raw.get("value"))
        if mode != "randomized_arm":
            response = "" if raw.get("response") is None else str(raw.get("response")).strip()
            if response not in {"", "R", "NR"}:
                raise ValueError("Invented endpoint labels must be R, NR, or missing")
            row["response"] = response
        if mode == "randomized_arm":
            row["arm"] = "" if raw.get("arm") is None else str(raw["arm"]).strip()
        for name in covariates:
            value = raw.get(name)
            row[name] = _numeric_cell(value) if isinstance(value, (float, int)) else ("" if value is None else str(value))
        normalized.append(row)
    normalized.sort(key=lambda row: (row["unit"], row["patient_key"], row["pair_id"], row.get("window", "")))
    if mode != "repeated":
        keys = [(row["study_id"], row["patient_key"], row["unit"]) for row in normalized]
        if len(keys) != len(set(keys)):
            raise ValueError("Two-timepoint model input must have one row per patient and feature")
    else:
        keys = [(row["study_id"], row["patient_key"], row["unit"], row["window"]) for row in normalized]
        if len(keys) != len(set(keys)):
            raise ValueError("Repeated model input has duplicate patient/unit/window rows")
    for unit, identity in metadata.items():
        patients = sorted({row["patient_key"] for row in normalized if row["unit"] == unit})
        identity["study"] = normalized[0]["study_id"]
        identity["patient_set_id"] = hashlib.sha256(
            json.dumps(patients, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    return normalized, metadata


def _normalise_synthesis_rows(records, study_ids, overlap_receipts):
    if not records:
        raise ValueError("Synthesis requires invented study effects")
    receipts = _normalise_overlap_receipts(overlap_receipts, study_ids)
    normalized = []
    grouped = defaultdict(list)
    seen_studies = set()
    for raw in records:
        missing = set(_SYNTHESIS_COLUMNS) - raw.keys()
        if missing:
            raise ValueError("Synthesis row misses required identities or effect values: " + ", ".join(sorted(missing)))
        study = str(raw["study"])
        if study not in study_ids:
            raise ValueError("Synthesis row names a study absent from the synthetic manifest")
        string_fields = set(_SYNTHESIS_COLUMNS) - {"estimate", "se", "ci_lb", "ci_ub", "p_value"}
        row = {name: str(raw.get(name) or "").strip() for name in string_fields}
        numeric_fields = ("estimate", "se", "ci_lb", "ci_ub", "p_value")
        for name in numeric_fields:
            value = raw.get(name)
            if value in (None, "", "NA", "NaN", "nan"):
                row[name] = None
                continue
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("Synthesis estimates, SEs, and p values must be finite or missing")
            row[name] = number
        if row["status"] == "ESTIMABLE":
            if any(row[name] is None for name in numeric_fields):
                raise ValueError("Estimable synthesis rows require finite estimates, intervals, and p values")
            if row["se"] <= 0 or not 0 <= row["p_value"] <= 1 or row["ci_lb"] > row["ci_ub"]:
                raise ValueError("Synthesis SE must be positive and p value must be in [0, 1]")
        elif row["status"] == "NOT_ESTIMABLE":
            if not row["reason"]:
                raise ValueError("Nonestimable synthesis rows require an explicit reason")
        else:
            raise ValueError("Synthesis row status must be ESTIMABLE or NOT_ESTIMABLE")
        if any(not row[name] for name in (
            "study", "patient_set_id", "source_family_id", "overlap_receipt_id", "unit_family",
            "unit", "panel_family", "multiplicity_family_id", "feature_method_id",
            "analysis_method_id", "endpoint_id", "regimen_id", "window_id", "assay_id",
            "effect_scale_id",
        )):
            raise ValueError("Synthesis identity and source-family receipt fields must be explicit")
        if row["overlap_status"] not in {"DISJOINT_VERIFIED", "OVERLAPPING", "UNRESOLVED"}:
            raise ValueError("Synthesis independence status must be explicit")
        if len(row["overlap_receipt_id"]) != 64 or any(
            character not in "0123456789abcdef" for character in row["overlap_receipt_id"]
        ):
            raise ValueError("Synthesis overlap receipt must be a lowercase SHA256")
        if "count" in row["effect_scale_id"].casefold():
            raise ValueError("Count-derived synthesis requires the unavailable voom/dream route")
        family_key = tuple(row[name] for name in (
            "unit_family", "unit", "panel_family", "multiplicity_family_id",
            "feature_method_id", "analysis_method_id",
            "endpoint_id", "regimen_id", "window_id", "assay_id", "effect_scale_id",
        ))
        if (family_key, study) in seen_studies:
            raise ValueError("Study-first synthesis requires one effect per study within each family")
        seen_studies.add((family_key, study))
        group_id = hashlib.sha256(json.dumps(family_key, separators=(",", ":")).encode()).hexdigest()[:24]
        row["analysis_group_id"] = group_id
        grouped[family_key].append(row)
        normalized.append(row)
    group_rows = []
    for family_key, family_rows in sorted(grouped.items(), key=lambda item: item[0]):
        patient_sets = [row["patient_set_id"] for row in family_rows]
        statuses = {row["overlap_status"] for row in family_rows}
        reason = ""
        if len(patient_sets) != len(set(patient_sets)):
            reason = "duplicate_patient_set_identity"
        elif statuses != {"DISJOINT_VERIFIED"}:
            reason = "source_independence_unresolved_or_overlapping"
        elif len(family_rows) > 1:
            for index, left in enumerate(family_rows):
                for right in family_rows[index + 1:]:
                    key = tuple(sorted((left["study"], right["study"])))
                    receipt = receipts.get(key)
                    expected_families = {
                        left["study"]: left["source_family_id"],
                        right["study"]: right["source_family_id"],
                    }
                    if (
                        receipt is None
                        or receipt["overlap_status"] != "DISJOINT_VERIFIED"
                        or receipt["source_family_by_study"] != expected_families
                    ):
                        reason = "source_independence_unresolved_or_overlapping"
                        break
                if reason:
                    break
        eligible = [row for row in family_rows if row["status"] == "ESTIMABLE"]
        if reason:
            eligible = []
        group_rows.append({
            "analysis_group_id": family_rows[0]["analysis_group_id"],
            "preflight_reason": reason,
            "k": len(eligible),
            "n_input": len(family_rows),
            "n_excluded": len(family_rows) - len(eligible),
            "independence_status": (
                "NOT_RESOLVED" if reason else
                "SINGLE_STUDY_NO_CROSS_STUDY_CHECK" if len(family_rows) == 1 else
                "DISJOINT_VERIFIED"
            ),
        })
    normalized.sort(key=lambda row: (row["analysis_group_id"], row["study"]))
    return normalized, group_rows


def _normalise_overlap_receipts(records, study_ids):
    receipts = {}
    for raw in records:
        if set(raw) != set(_OVERLAP_RECEIPT_COLUMNS):
            raise ValueError("Source-overlap receipt must have the exact declared fields")
        row = {name: str(raw.get(name) or "").strip() for name in _OVERLAP_RECEIPT_COLUMNS}
        study_a, study_b = row["study_a"], row["study_b"]
        if (
            not study_a or not study_b or study_a == study_b
            or study_a not in study_ids or study_b not in study_ids
            or not row["source_family_a"] or not row["source_family_b"]
            or row["overlap_status"] not in {"DISJOINT_VERIFIED", "OVERLAPPING", "UNRESOLVED"}
            or not re.fullmatch(r"[0-9a-f]{64}", row["receipt_sha256"])
        ):
            raise ValueError("Source-overlap receipt identities, status, or hash are invalid")
        receipt_body = {name: row[name] for name in _OVERLAP_RECEIPT_COLUMNS if name != "receipt_sha256"}
        if canonical_sha256(receipt_body) != row["receipt_sha256"]:
            raise ValueError("Source-overlap receipt hash does not match its declared relation")
        key = tuple(sorted((study_a, study_b)))
        source_family_by_study = {
            study_a: row["source_family_a"],
            study_b: row["source_family_b"],
        }
        receipt = {
            "source_family_by_study": source_family_by_study,
            "overlap_status": row["overlap_status"],
            "receipt_sha256": row["receipt_sha256"],
        }
        if key in receipts:
            raise ValueError("Source-overlap receipt repeats a study pair")
        receipts[key] = receipt
    return receipts


def _apply_scoped_fdr(rows, *, policy, q=0.10):
    families = defaultdict(list)
    for index, row in enumerate(rows):
        if row.get("unit_family") in {"m5m6_gene", "m5m6"} or row.get("panel_family") == "M5M6":
            members = set(policy.m5m6_family_members)
            adjustment = "BH_0.10_exploratory"
            method = "bh"
            denominator = len(members)
            if row.get("unit") not in members:
                raise ValueError("M5/M6 output unit is outside the predeclared BH family")
        elif row.get("unit_family") in {"panel", "custom_panel"}:
            family_id = row.get("multiplicity_family_id")
            members = set((policy.panel_family_members or {}).get(family_id, ()))
            adjustment = "holm"
            method = "holm"
            denominator = len(members)
            if row.get("unit") not in members:
                raise ValueError("Panel output unit is outside the predeclared Holm family")
        else:
            row["adjustment_method"] = "NONE_OUT_OF_SCOPE"
            row["adjusted_p"] = "NA"
            continue
        if denominator < 1:
            raise ValueError("Multiplicity family has no predeclared members")
        scope = (
            row.get("unit_family"), row.get("feature_method_id"), row.get("analysis_method_id"),
            row.get("endpoint_id"), row.get("regimen_id"), row.get("window_id"),
            row.get("assay_id"), row.get("effect_scale_id"),
            row.get("multiplicity_family_id"),
        )
        row["adjustment_method"] = adjustment
        row["adjusted_p"] = "NA"
        families[(method, scope, denominator)].append(index)
    for (method, _scope, denominator), indexes in families.items():
        estimable = [index for index in indexes if _finite_text(rows[index].get("p_value"))]
        raw = [float(rows[index]["p_value"]) for index in estimable]
        adjusted = _holm(raw, denominator=denominator) if method == "holm" else _bh(raw, denominator=denominator)
        for index, value in zip(estimable, adjusted):
            rows[index]["adjusted_p"] = value


def _holm(values, *, denominator=None):
    order = sorted(range(len(values)), key=lambda index: values[index])
    adjusted = [0.0] * len(values)
    previous = 0.0
    count = len(values) if denominator is None else denominator
    for rank, index in enumerate(order):
        previous = max(previous, min(1.0, (count - rank) * values[index]))
        adjusted[index] = previous
    return adjusted


def _bh(values, *, denominator=None):
    actual_count = len(values)
    count = actual_count if denominator is None else denominator
    if count < actual_count:
        raise ValueError("Multiplicity denominator cannot be smaller than the observed p-value count")
    extended = [*values, *([1.0] * (count - actual_count))]
    order = sorted(range(len(extended)), key=lambda index: extended[index])
    adjusted = [0.0] * len(extended)
    previous = 1.0
    for rank in range(count - 1, -1, -1):
        index = order[rank]
        previous = min(previous, extended[index] * count / (rank + 1))
        adjusted[index] = min(1.0, previous)
    return adjusted[:actual_count]


def validate_n13_policy_payload(payload: Mapping, *, route: str) -> N13Policy:
    """Validate a real-route N13 policy before released clinical inputs are hashed."""
    if not isinstance(payload, Mapping):
        raise ValueError("N13 route policy must be an object")
    values = dict(payload)
    randomization = values.pop("randomization_admission", None)
    required = {field.name for field in fields(N13Policy)}
    if set(values) != required:
        raise ValueError("N13 route policy must supply every numerical field exactly")
    for name in ("covariates", "repeated_windows", "m5m6_family_members", "sensitivity_modes"):
        if not isinstance(values[name], (list, tuple)):
            raise ValueError(f"N13 {name} must be an explicit list")
        values[name] = tuple(values[name])
    if values["panel_family_members"] is not None:
        if not isinstance(values["panel_family_members"], Mapping):
            raise ValueError("N13 panel family membership must be a mapping")
        values["panel_family_members"] = {
            name: tuple(members) for name, members in values["panel_family_members"].items()
        }
    policy = N13Policy(**values)
    if policy.status != "ACCEPTED" or not policy.decision_ref:
        raise PermissionError("N13 status and decision reference must be accepted before input access")
    _validate_n13_configuration(policy, route)
    if route == "randomized_arm":
        if not isinstance(randomization, Mapping) or set(randomization) != {
            "comparative_estimand_id", "randomization_verified", "receipt_sha256",
        }:
            raise PermissionError("Randomized-arm route requires a separate declared admission receipt")
        if (
            randomization["randomization_verified"] is not True
            or not isinstance(randomization["comparative_estimand_id"], str)
            or not randomization["comparative_estimand_id"].strip()
            or not isinstance(randomization["receipt_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", randomization["receipt_sha256"])
        ):
            raise PermissionError("Randomized-arm route admission receipt is malformed")
    elif randomization is not None:
        raise ValueError("Randomization admission is valid only for randomized-arm analysis")
    return policy


def _validate_n13_configuration(policy, route):
    if not isinstance(policy, N13Policy):
        raise ValueError("An explicit N13 numerical policy is required before model fitting")
    if policy.status not in {"PROPOSED", "ACCEPTED"} or not policy.decision_ref and policy.status == "ACCEPTED":
        raise ValueError("N13 policy status/reference is invalid")
    if (
        policy.min_repeated_patients < 1
        or policy.min_per_response_group < 1
        or policy.min_meta_k_pool < 4
        or not 0 < policy.confidence_level < 1
        or policy.fdr_scope_id != "predeclared_panel_families_v1"
        or len(set(policy.repeated_windows)) != len(policy.repeated_windows)
        or len(set(policy.sensitivity_modes)) != len(policy.sensitivity_modes)
        or any(mode not in {"same_lesion", "exact_day", "tighter_timing"} for mode in policy.sensitivity_modes)
    ):
        raise ValueError(
            "N13 support thresholds, confidence level, windows, and the supported FDR scope must be explicit"
        )
    for field, expected in _EXPECTED_MODELS.items():
        if getattr(policy, field) != expected:
            raise ValueError(f"N13 has no supported explicit method selection for {field}")
    if len(set(policy.covariates)) != len(policy.covariates) or any(
        not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]*", str(name)) for name in policy.covariates
    ):
        raise ValueError("N13 covariates must be unique explicit source-column names")
    if set(policy.covariates) & {"study_id", "patient_key", "pair_id", "unit", "response", "arm", "window", "value"}:
        raise ValueError("N13 covariates cannot replace model identity or endpoint terms")
    if route == "two_timepoint" and (
        "pre_value" in policy.covariates or "baseline" in {name.casefold() for name in policy.covariates}
    ):
        raise ValueError("Primary two-timepoint covariates cannot include baseline expression")
    if route == "repeated" and policy.repeated_selection_mode not in {
        "complete_declared_windows", "available_observations",
    }:
        raise ValueError("N13 must explicitly select a supported repeated-window missingness mode")
    if route == "repeated" and (
        len(policy.repeated_windows) < 2 or policy.repeated_windows[0] != "baseline"
    ):
        raise ValueError("N13 repeated models must explicitly declare baseline and at least one follow-up window")
    if policy.sensitivity_modes and route != "two_timepoint":
        raise ValueError("Same-lesion and timing sensitivities are supported only on the paired two-timepoint route")
    if "tighter_timing" in policy.sensitivity_modes:
        threshold = policy.tighter_timing_max_deviation_days
        if threshold is None or not math.isfinite(float(threshold)) or float(threshold) <= 0:
            raise ValueError("N13 tighter-timing sensitivity needs an explicit positive source-specific day cutoff")
    elif policy.tighter_timing_max_deviation_days is not None:
        raise ValueError("N13 tighter-timing cutoff is forbidden unless that sensitivity is explicitly selected")
    if route == "randomized_arm" and (
        policy.min_per_randomized_arm is None or policy.min_per_randomized_arm < 1
    ):
        raise ValueError("N13 must declare minimum support for each randomized arm")
    if route == "synthesis":
        if policy.fdr_denominator_policy != "all_predeclared_members_missing_as_p1_v1":
            raise ValueError("N13 must declare how missing members enter the multiplicity denominator")
        if not isinstance(policy.source_overlap_contract_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", policy.source_overlap_contract_sha256
        ):
            raise ValueError("N13 synthesis requires the exact source-overlap contract hash")
        if not policy.panel_family_members or not policy.m5m6_family_members:
            raise ValueError("N13 synthesis requires predeclared panel and M5/M6 family membership")
        if any(not members or len(set(members)) != len(members) for members in policy.panel_family_members.values()):
            raise ValueError("N13 panel multiplicity family membership must be explicit and unique")
        if len(set(policy.m5m6_family_members)) != len(policy.m5m6_family_members):
            raise ValueError("N13 M5/M6 multiplicity family membership must be unique")


def _validate_n13(policy, acceptance, *, route, authorized_policy_sha256=None):
    _validate_n13_configuration(policy, route)
    if acceptance is None or not acceptance.decision_id or not acceptance.record_ref:
        raise ValueError("N13 numerical policy is unsigned; an explicit acceptance record is required")
    if acceptance.fixture_only:
        return True
    release_contract = {
        "two_timepoint": ("N13_TWO_TIMEPOINT", "fit_two_timepoint"),
        "repeated": ("N13_REPEATED", "fit_repeated_windows"),
        "randomized_arm": ("N13_RANDOMIZED_ARM", "fit_randomized_arm"),
        "synthesis": ("N13_SYNTHESIS", "synthesize_effects"),
    }.get(route)
    expected_policy_sha = authorized_policy_sha256 or canonical_sha256(asdict(policy))
    if release_contract is not None and is_authorized_release(
        acceptance.authorization,
        release_scope=release_contract[0],
        operation=release_contract[1],
    ):
        record = acceptance.authorization.record
        if (
            policy.status != "ACCEPTED"
            or record.get("policy_sha256") != expected_policy_sha
            or not isinstance(record.get("decision"), dict)
            or record["decision"].get("identity") != policy.decision_ref
        ):
            raise PermissionError("N13 user-release record does not bind the accepted numerical policy")
        return False
    raise PermissionError("N13 status and record_ref are not signatures; use the scoped user-release boundary")


def _policy_status(policy, fixture_policy):
    return "FIXTURE_ONLY_PROPOSAL" if fixture_policy else policy.status


def _preflight_analysis_paths(provenance_manifest, output_dir, retention_dir):
    inputs = {"R script": _SCRIPT}
    if provenance_manifest is not None:
        inputs["provenance manifest"] = provenance_manifest
    guarded_inputs, guarded_outputs = check_path_separation(
        inputs=inputs,
        outputs={"analysis output": output_dir, "R retention": retention_dir},
    )
    validate_output_directory(guarded_outputs["analysis output"])
    validate_output_directory(guarded_outputs["R retention"])
    return guarded_inputs, guarded_outputs


def _read_fixture_manifest(path, kind, study_ids):
    try:
        manifest = json.loads(guard_path(path, "synthetic analysis manifest").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Synthetic analysis requires a readable provenance manifest") from error
    if (
        manifest.get("producer") != _MANIFEST_PRODUCER
        or manifest.get("manifest_version") != 1
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != kind
    ):
        raise ValueError("Synthetic analysis manifest has the wrong producer, kind, or classification")
    if set(manifest.get("cohort_ids", ())) != set(study_ids):
        raise ValueError("Synthetic analysis manifest study IDs do not match the declared IDs")
    return manifest


def _write_synthetic_r_manifest(path, *, kind, source_paths, cohorts, identity_fields):
    """Bind each invented bridge payload hash and its named identity columns."""
    source_hashes = {
        name: sha256_file(source_path, label=f"invented R {name} payload")
        for name, source_path in sorted(source_paths.items())
    }
    normalized_cohorts = sorted({str(value) for value in cohorts})
    manifest = {
        "manifest_version": 1,
        "producer": _MANIFEST_PRODUCER,
        "data_classification": "synthetic",
        "kind": kind,
        "cohort_ids": normalized_cohorts,
        "source_sha256": source_hashes,
        "identity_fields": {name: list(fields) for name, fields in sorted(identity_fields.items())},
        "payload_sha256": canonical_sha256({
            "cohorts": normalized_cohorts,
            "source_sha256": source_hashes,
        }),
    }
    path = guard_path(path, "synthetic R provenance manifest output")
    if path.exists():
        raise FileExistsError("Synthetic R provenance manifest output already exists")
    with path.open("x", encoding="utf-8", newline="") as stream:
        json.dump(manifest, stream, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    return manifest


def _verify_payload_hash(rows, manifest):
    if canonical_sha256(rows) != manifest.get("payload_sha256"):
        raise ValueError("Synthetic analysis manifest does not match the input rows")


def _guard_study_ids(study_ids):
    if not study_ids:
        raise ValueError("Explicit study IDs are required")
    known = {value.casefold() for value in known_cohort_ids()}
    for study_id in study_ids:
        if not isinstance(study_id, str) or not study_id.strip():
            raise ValueError("Study IDs must be non-empty")
        if is_locked_study(study_id):
            raise ValueError("IMvigor210 is a locked final test and is refused")
        if study_id.casefold() in known:
            raise ValueError("Synthetic A-LONG analysis cannot use a known real cohort ID")


def _check_study_ids(rows, expected, *, key="study_id"):
    actual = {str(row.get(key, "")) for row in rows}
    if actual != set(expected):
        raise ValueError("Input study IDs differ from the synthetic provenance declaration")


def _ensure_patient_response_consistent(rows):
    values = defaultdict(set)
    for row in rows:
        if row.get("response"):
            values[(row["unit"], row["patient_key"])].add(row["response"])
    if any(len(labels) > 1 for labels in values.values()):
        raise ValueError("Repeated model response labels must be constant within patient")


def _opaque_patient_key(study_id, value):
    if not value:
        raise ValueError("Patient key must be present in invented model rows")
    return hashlib.sha256(f"{study_id}\0{value}".encode("utf-8")).hexdigest()[:24]


def _numeric_cell(value):
    if value is None or value == "":
        return ""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Model numeric values must be finite or missing")
    return number


def _optional_numeric_cell(value):
    if value in (None, "", "NA", "NaN", "nan"):
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Optional model timing values must be finite or missing")
    return number


def _safe_patient_output_dir(path):
    path = guard_path(path, "patient-level output directory")
    try:
        relative = path.resolve().relative_to(_ROOT.resolve())
    except ValueError:
        return path
    if not relative.parts or relative.parts[0] not in {"results", ".scratch"}:
        raise ValueError("Patient-level analysis outputs must stay under results/ or .scratch/")
    return path


def _safe_real_output_dir(path):
    path = guard_path(path, "real patient-level output directory")
    try:
        relative = path.relative_to(_ROOT.resolve())
    except ValueError as error:
        raise PermissionError("Real A-LONG outputs must stay under results/ or .scratch/") from error
    if not relative.parts or relative.parts[0] not in {"results", ".scratch"}:
        raise PermissionError("Real A-LONG outputs must stay under results/ or .scratch/")
    return path


def _write_tsv(path, rows, columns):
    path = guard_path(path, "analysis TSV output")
    if path.exists():
        raise FileExistsError("A-LONG analysis output already exists")
    if not path.parent.is_dir():
        raise FileNotFoundError("A-LONG analysis output directory was not prepared")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in columns})


def _read_tsv(path):
    with guard_path(path, "analysis TSV input").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _finite_text(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
