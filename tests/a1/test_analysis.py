from __future__ import annotations

import hashlib
import csv
from dataclasses import replace

import pytest

from tools.a_meta.provenance import canonical_sha256, known_cohort_ids
from tools.a1.analysis import (
    N13Acceptance,
    N13Policy,
    RandomizationAdmission,
    _apply_scoped_fdr,
    fit_randomized_arm,
    fit_repeated_windows,
    fit_two_timepoint,
    model_effects_for_synthesis,
    run_released_analysis,
    run_released_synthesis,
    synthesize_effects,
    write_synthetic_analysis_manifest,
)


def _policy(*, covariates=(), windows=("baseline", "on")):
    return N13Policy(
        status="PROPOSED",
        decision_ref=None,
        delta_method_id="lm_change_response_covariates_v1",
        ancova_method_id="lm_on_response_baseline_covariates_sensitivity_v1",
        repeated_method_id="lmerTest_lme4_response_window_random_intercept_v1",
        randomized_arm_method_id="lm_randomized_arm_change_contrast_v1",
        meta_method_id="metafor_REML_modified_KH_v1",
        df_method_id="residual_t_and_Satterthwaite_v1",
        covariates=tuple(covariates),
        repeated_windows=tuple(windows),
        min_repeated_patients=4,
        min_per_response_group=2,
        min_meta_k_pool=4,
        confidence_level=0.95,
        fdr_scope_id="predeclared_panel_families_v1",
        repeated_selection_mode="complete_declared_windows",
        min_per_randomized_arm=2,
    )


def _acceptance():
    return N13Acceptance("N13", "invented-fixture-only", fixture_only=True)


def _synthesis_policy(panel_families, gene_members):
    return replace(
        _policy(),
        panel_family_members={name: tuple(members) for name, members in panel_families.items()},
        m5m6_family_members=tuple(gene_members),
        fdr_denominator_policy="all_predeclared_members_missing_as_p1_v1",
        source_overlap_contract_sha256=hashlib.sha256(b"fixture-only overlap contract").hexdigest(),
    )


def _pairwise_overlap_receipts(rows, *, status="DISJOINT_VERIFIED"):
    family_by_study = {}
    for row in rows:
        family_by_study.setdefault(row["study"], row["source_family_id"])
    studies = sorted(family_by_study)
    receipts = []
    for left_index, study_a in enumerate(studies):
        for study_b in studies[left_index + 1:]:
            source_family_a = family_by_study[study_a]
            source_family_b = family_by_study[study_b]
            receipt = {
                "study_a": study_a,
                "study_b": study_b,
                "source_family_a": source_family_a,
                "source_family_b": source_family_b,
                "overlap_status": status,
            }
            receipts.append({**receipt, "receipt_sha256": canonical_sha256(receipt)})
    return receipts


def test_released_model_api_defaults_locked_before_release_object_access():
    with pytest.raises(PermissionError, match="allow_outcomes=True"):
        run_released_analysis(
            "two-timepoint",
            released_inputs=object(),
            policy_payload={},
            output_dir="invented-output",
            retention_dir="invented-retention",
        )


def test_released_synthesis_api_defaults_locked_before_release_object_access():
    with pytest.raises(PermissionError, match="allow_outcomes=True"):
        run_released_synthesis(
            released_inputs=object(),
            policy_payload={},
            output_dir="invented-output",
            retention_dir="invented-retention",
        )


def _fit(rows, tmp_path, *, policy=None, acceptance=None):
    manifest = tmp_path / "input_manifest.json"
    write_synthetic_analysis_manifest(manifest, rows, study_ids=("fixture-study",))
    return fit_two_timepoint(
        rows,
        study_id="fixture-study",
        provenance_manifest=manifest,
        policy=policy or _policy(),
        acceptance=acceptance or _acceptance(),
        output_dir=tmp_path / "analysis",
        retention_dir=tmp_path / "retention",
    )


def _patient(index):
    return f"synthetic-{index:04d}"


def _identity(unit="panel-a", *, unit_family="panel", effect_scale_id="LOG2_TPMPLUS1_PANEL_MEAN", **overrides):
    identity = {
        "unit_family": unit_family,
        "feature_method_id": f"feature_method_{unit}",
        "analysis_method_id": "lm_change_response_covariates_v1",
        "endpoint_id": "RECIST_ORR",
        "regimen_id": "ICI_MONO",
        "window_id": "baseline_to_on_1",
        "assay_id": "rnaseq_tpm",
        "effect_scale_id": effect_scale_id,
        "panel_family": "fixture_panel_family",
        "multiplicity_family_id": "fixture_multiplicity_family",
        "source_family_id": "fixture_source_family",
        "overlap_receipt_id": "a" * 64,
        "overlap_status": "DISJOINT_VERIFIED",
    }
    identity.update(overrides)
    return identity


def test_change_model_reports_r_minus_nr_and_ancova_is_separate_sensitivity(tmp_path):
    rows = []
    baselines_r = (10, 12, 14, 16)
    baselines_nr = (0, 2, 4, 6)
    residuals = (0, 0, 0, 0)
    for label, baselines, intercept, start in (
        ("R", baselines_r, 3, 0),
        ("NR", baselines_nr, 0, 4),
    ):
        for index, (baseline, residual) in enumerate(zip(baselines, residuals), start=start):
            rows.append({
                "study_id": "fixture-study",
                "patient_key": _patient(index),
                "pair_id": f"pair-{index:04d}",
                "unit": "panel-a",
                "pre_value": baseline,
                "on_value": 0.5 * baseline + intercept + residual,
                "response": label,
                "age": 40 + (0, 2, 3, 1)[index % 4] * 5,
                **_identity(),
            })
    result = _fit(rows, tmp_path, policy=_policy(covariates=("age",)))

    primary = next(row for row in result.effects if row["model"] == "delta_primary")
    ancova = next(row for row in result.effects if row["model"] == "ancova_sensitivity")
    assert float(primary["estimate"]) == pytest.approx(-2.0, abs=1e-8)
    assert float(ancova["estimate"]) == pytest.approx(3.0, abs=1e-8)
    assert primary["contrast"] == "R_minus_NR_change"
    assert ancova["effect_role"] == "conditional_on_baseline_association"
    assert primary["n_R"] == "4" and primary["n_NR"] == "4"


def test_pair_sensitivities_use_only_prespecified_same_lesion_and_exact_days(tmp_path):
    selected = {0, 1, 4, 5}
    residual_by_index = {
        0: -0.4, 1: 0.4, 2: -0.2, 3: 0.2,
        4: -0.6, 5: -0.2, 6: 0.2, 7: 0.6,
    }
    rows = []
    for index in range(8):
        response = "R" if index >= 4 else "NR"
        rows.append({
            "study_id": "fixture-study",
            "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}",
            "unit": "panel-a",
            "pre_value": float(index),
            "on_value": float(index) + (3.0 if response == "R" else 1.0) + residual_by_index[index],
            "response": response,
            "same_lesion": "true" if index in selected else "false",
            "pre_day_precision": "exact" if index in selected else "unknown",
            "on_day_precision": "exact" if index in selected else "unknown",
            "pre_day_numeric": -2 if index in selected else None,
            "on_day_numeric": 9 if index in selected else None,
            "day_distance_to_target": 1 if index in selected else 8,
            **_identity(),
        })
    policy = replace(
        _policy(),
        sensitivity_modes=("same_lesion", "exact_day", "tighter_timing"),
        tighter_timing_max_deviation_days=1.0,
    )

    result = _fit(rows, tmp_path, policy=policy)

    sensitivities = {
        row["model"]: row
        for row in result.effects
        if row["model"] in {
            "delta_same_lesion_sensitivity",
            "delta_exact_day_sensitivity",
            "delta_tighter_timing_sensitivity",
        }
    }
    assert set(sensitivities) == {
        "delta_same_lesion_sensitivity",
        "delta_exact_day_sensitivity",
        "delta_tighter_timing_sensitivity",
    }
    assert all(row["status"] == "ESTIMABLE" for row in sensitivities.values())
    assert all(row["n_R"] == "2" and row["n_NR"] == "2" for row in sensitivities.values())
    with result.paths["longitudinal_support"].open(newline="", encoding="utf-8") as stream:
        support_rows = list(csv.DictReader(stream, delimiter="\t"))
    assert "patient_key" not in support_rows[0] and "patient_id" not in support_rows[0]
    sensitivity_support = {
        row["model"]: row for row in support_rows
        if row["record_type"] == "analysis_effect" and row["model"] in sensitivities
    }
    assert set(sensitivity_support) == set(sensitivities)
    assert all(row["n_pairs"] == "4" for row in sensitivity_support.values())
    assert all(row["n_patients_used"] == "4" for row in sensitivity_support.values())
    assert all(row["support_role"].startswith("prespecified_") for row in sensitivity_support.values())


def test_one_response_group_has_own_delta_but_no_response_interaction(tmp_path):
    rows = [
        {
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}", "unit": "panel-a",
            "pre_value": float(index), "on_value": float(index + 2),
            "response": "R",
            **_identity(),
        }
        for index in range(4)
    ]
    result = _fit(rows, tmp_path)

    primary = next(row for row in result.effects if row["model"] == "delta_primary")
    own_delta = next(row for row in result.within_group_deltas if row["response"] == "R")
    assert primary["status"] == "NOT_ESTIMABLE"
    assert primary["reason"] == "single_response_group"
    assert own_delta["estimate"] == "2"


def test_missing_endpoint_remains_in_attrition_support_and_is_not_a_class(tmp_path):
    residual_by_index = (-0.3, -0.1, 0.1, 0.3, -0.4, -0.1, 0.2, 0.3, 0.0)
    rows = []
    for index in range(9):
        response = "R" if index >= 4 else "NR"
        if index == 8:
            response = ""
        change = (2.0 if response == "R" else 0.0) + residual_by_index[index]
        rows.append({
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}", "unit": "panel-a",
            "pre_value": float(index), "on_value": float(index) + change,
            "response": response, **_identity(),
        })
    result = _fit(rows, tmp_path)

    primary = next(row for row in result.effects if row["model"] == "delta_primary")
    assert primary["status"] == "ESTIMABLE"
    assert primary["n_R"] == "4" and primary["n_NR"] == "4"
    assert result.support["n_input"] == "9"
    assert result.support["n_complete"] == "8"
    assert result.support["n_missing_endpoint"] == "1"


def test_full_rank_covariate_model_and_collinear_response_covariate_are_reported(tmp_path):
    residual_by_index = (0.0, 0.2, -0.1, 0.3, -0.2, 0.1, -0.3, 0.4)
    rows = []
    for index in range(8):
        response = "R" if index >= 4 else "NR"
        rows.append({
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}", "unit": "panel-a",
            "pre_value": index,
            "on_value": index + (2 if response == "R" else 0) + residual_by_index[index],
            "response": response, "age": 30 + index,
            "response_copy": 1 if response == "R" else 0,
            **_identity(),
        })
    full = _fit(rows, tmp_path / "full", policy=_policy(covariates=("age",)))
    deficient = _fit(rows, tmp_path / "deficient", policy=_policy(covariates=("response_copy",)))

    full_primary = next(row for row in full.effects if row["model"] == "delta_primary")
    deficient_primary = next(row for row in deficient.effects if row["model"] == "delta_primary")
    assert full_primary["status"] == "ESTIMABLE"
    assert int(full_primary["rank"]) == 3
    assert deficient_primary["status"] == "NOT_ESTIMABLE"
    assert deficient_primary["reason"] == "rank_deficient_design"


def test_repeated_windows_use_patient_random_intercept_and_report_fixed_patient_rank(tmp_path):
    rows = []
    offsets = (0.0, 1.5, -0.7, 0.8, -1.2, 0.4)
    for index, offset in enumerate(offsets):
        response = "R" if index >= 3 else "NR"
        baseline = 10 + index * 2 + offset
        for window, shift in (("baseline", 0.0), ("on_1", 1.0), ("on_2", 2.0)):
            group_effect = 0.0 if response == "NR" else (2.0 if window == "on_1" else 3.0 if window == "on_2" else 0.0)
            rows.append({
                "study_id": "fixture-study", "patient_key": _patient(index),
                "pair_id": f"pair-{index:04d}-{window}", "unit": "panel-a",
                "window": window, "value": baseline + shift + group_effect + (offset * (0.1 if window != "baseline" else 0)),
                "response": response,
                **_identity(
                    window_id="baseline_to_approved_windows",
                    analysis_method_id="lmerTest_lme4_response_window_random_intercept_v1",
                ),
            })
    manifest = tmp_path / "repeated_manifest.json"
    write_synthetic_analysis_manifest(manifest, rows, study_ids=("fixture-study",))
    result = fit_repeated_windows(
        rows,
        study_id="fixture-study",
        provenance_manifest=manifest,
        policy=_policy(windows=("baseline", "on_1", "on_2")),
        acceptance=_acceptance(),
        output_dir=tmp_path / "repeated",
        retention_dir=tmp_path / "repeated-retention",
    )

    interactions = [row for row in result.effects if row["contrast"].startswith("R_minus_NR_at_")]
    assert {row["contrast"] for row in interactions} == {
        "R_minus_NR_at_on_1_vs_baseline",
        "R_minus_NR_at_on_2_vs_baseline",
    }
    assert all(row["status"] == "ESTIMABLE" for row in interactions)
    assert all(float(row["estimate"]) > 0 for row in interactions)
    assert result.support["patient_aware_model"] == "lmerTest_lme4_response_window_random_intercept_v1"
    assert result.support["fixed_patient_response_covariate_rank_status"] == "RANK_DEFICIENT"
    assert result.support["corroboration_role"] == "one_way_corroboration_only"
    assert result.support["n_patients_used"] == "6"
    assert result.support["n_observations_used"] == "18"
    within = next(row for row in result.within_group_deltas if row["response"] == "R" and row["window"] == "on_1")
    assert within["effect_role"] == "descriptive_within_group_change"
    assert within["status"] == "DESCRIPTIVE_WITHIN_GROUP_CHANGE"
    assert float(within["se"]) >= 0
    with result.paths["longitudinal_support"].open(newline="", encoding="utf-8") as stream:
        support_rows = list(csv.DictReader(stream, delimiter="\t"))
    corroboration = [
        row for row in support_rows
        if row["record_type"] == "analysis_effect"
        and row["effect_role"] == "one_way_longitudinal_corroboration"
    ]
    assert len(corroboration) == 2
    assert all(row["n_patients_used"] == "6" for row in corroboration)
    assert all(row["support_role"] == "one_way_longitudinal_corroboration" for row in corroboration)

    unapproved_rows = [*rows, {**rows[0], "window": "not_approved"}]
    unapproved_manifest = tmp_path / "unapproved_manifest.json"
    write_synthetic_analysis_manifest(
        unapproved_manifest, unapproved_rows, study_ids=("fixture-study",)
    )
    with pytest.raises(ValueError, match="outside the accepted N13 set"):
        fit_repeated_windows(
            unapproved_rows,
            study_id="fixture-study",
            provenance_manifest=unapproved_manifest,
            policy=_policy(windows=("baseline", "on_1", "on_2")),
            acceptance=_acceptance(),
            output_dir=tmp_path / "unapproved",
            retention_dir=tmp_path / "unapproved-retention",
        )


def test_randomized_arm_change_contrast_requires_admission_and_estimates_combo_minus_ici(tmp_path):
    rows = []
    for index, (arm, pre, change) in enumerate((
        ("ICI_ONLY", 5, 1), ("ICI_ONLY", 8, 1), ("ICI_ONLY", 3, 1),
        ("COMBINATION", 6, 4), ("COMBINATION", 9, 4), ("COMBINATION", 4, 4),
    )):
        rows.append({
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}", "unit": "panel-a",
            "pre_value": pre, "on_value": pre + change, "arm": arm,
            **_identity(
                regimen_id="ICI_ONLY_VS_COMBINATION_RANDOMIZED",
                analysis_method_id="lm_randomized_arm_change_contrast_v1",
            ),
        })
    manifest = tmp_path / "arm_manifest.json"
    write_synthetic_analysis_manifest(manifest, rows, study_ids=("fixture-study",))
    admission = RandomizationAdmission(
        comparative_estimand_id="ICI_ONLY_VS_COMBINATION_CHANGE",
        record_ref="fixture-randomisation-record",
        randomization_verified=True,
        fixture_only=True,
    )
    result = fit_randomized_arm(
        rows,
        study_id="fixture-study",
        provenance_manifest=manifest,
        policy=_policy(),
        acceptance=_acceptance(),
        admission=admission,
        output_dir=tmp_path / "arm",
        retention_dir=tmp_path / "arm-retention",
    )

    effect = result.effects[0]
    assert float(effect["estimate"]) == pytest.approx(3.0)
    assert effect["contrast"] == "COMBINATION_minus_ICI_ONLY_change"
    assert effect["analysis_family"] == "randomized_arm"
    assert effect["n_arm_ici"] == "3" and effect["n_arm_combination"] == "3"
    assert effect["n_R"] == "0" and effect["n_NR"] == "0"


def test_unsigned_n13_and_known_real_ids_fail_before_rows_are_read(tmp_path):
    class UnreadableRows:
        def __iter__(self):
            raise AssertionError("guard must run before input access")

    manifest = tmp_path / "manifest.json"
    with pytest.raises(ValueError, match="unsigned"):
        fit_two_timepoint(
            UnreadableRows(),
            study_id="fixture-study",
            provenance_manifest=manifest,
            policy=_policy(),
            acceptance=None,
            output_dir=tmp_path / "analysis",
            retention_dir=tmp_path / "retention",
        )
    with pytest.raises(ValueError, match="locked final test"):
        fit_two_timepoint(
            UnreadableRows(),
            study_id="imvigor210",
            provenance_manifest=manifest,
            policy=_policy(),
            acceptance=_acceptance(),
            output_dir=tmp_path / "blocked",
            retention_dir=tmp_path / "blocked-retention",
        )
    registered = next(value for value in sorted(known_cohort_ids()) if value != "imvigor210")
    with pytest.raises(ValueError, match="known real cohort"):
        fit_two_timepoint(
            UnreadableRows(),
            study_id=registered.casefold(),
            provenance_manifest=manifest,
            policy=_policy(),
            acceptance=_acceptance(),
            output_dir=tmp_path / "registered",
            retention_dir=tmp_path / "registered-retention",
        )


def test_count_scale_cannot_fall_back_to_ordinary_least_squares(tmp_path):
    rows = [{
        "study_id": "fixture-study", "patient_key": _patient(0),
        "pair_id": "pair-0000", "unit": "gene-a",
        "pre_value": 10, "on_value": 12, "response": "R",
        **_identity(effect_scale_id="GENE_SOURCE_SCALE:counts"),
    }]
    manifest = tmp_path / "count_manifest.json"
    write_synthetic_analysis_manifest(manifest, rows, study_ids=("fixture-study",))

    with pytest.raises(ValueError, match="voom/dream route"):
        fit_two_timepoint(
            rows,
            study_id="fixture-study",
            provenance_manifest=manifest,
            policy=_policy(),
            acceptance=_acceptance(),
            output_dir=tmp_path / "count",
            retention_dir=tmp_path / "count-retention",
        )


def test_synthesis_keeps_families_separate_and_applies_holm_vs_m5m6_bh(tmp_path):
    rows = []
    for study_index in range(4):
        study = f"synthetic-study-{study_index:02d}"
        for panel_index in range(3):
            rows.append({
                "study": study, "patient_set_id": f"set-{study_index:02d}",
                "source_family_id": f"source-family-{study}",
                "overlap_receipt_id": hashlib.sha256(study.encode()).hexdigest(),
                "overlap_status": "DISJOINT_VERIFIED",
                "unit_family": "panel", "unit": f"panel-{panel_index}",
                "panel_family": "declared_immune_panel_family",
                "multiplicity_family_id": "predeclared_panels",
                "feature_method_id": "A_LONG_STRICT_CUSTOM_PANEL_MEAN_SOURCE_SCALE",
                "analysis_method_id": "lm_change_response_covariates_v1",
                "endpoint_id": "RECIST_ORR",
                "regimen_id": "ICI_MONO",
                "window_id": "baseline_to_on_1",
                "assay_id": "rnaseq_tpm",
                "effect_scale_id": "LOG2_TPMPLUS1_PANEL_MEAN",
                "estimate": 1.0 + panel_index * 0.1 + study_index * 0.02,
                "se": 0.2,
                    "ci_lb": 0.6 + panel_index * 0.1 + study_index * 0.02,
                    "ci_ub": 1.4 + panel_index * 0.1 + study_index * 0.02,
                "p_value": 0.01 * (panel_index + 1),
                "status": "ESTIMABLE", "reason": "",
            })
        for gene_index in range(3):
            rows.append({
                "study": study, "patient_set_id": f"set-{study_index:02d}",
                "source_family_id": f"source-family-{study}",
                "overlap_receipt_id": hashlib.sha256(study.encode()).hexdigest(),
                "overlap_status": "DISJOINT_VERIFIED",
                "unit_family": "m5m6_gene", "unit": f"gene-{gene_index}",
                "panel_family": "M5M6",
                "multiplicity_family_id": "M5M6_EXPLORATORY",
                "feature_method_id": "A_LONG_M5M6_INDIVIDUAL_GENE_SOURCE_SCALE",
                "analysis_method_id": "lm_change_response_covariates_v1",
                "endpoint_id": "RECIST_ORR",
                "regimen_id": "ICI_MONO",
                "window_id": "baseline_to_on_1",
                "assay_id": "microarray_log2",
                "effect_scale_id": "GENE_SOURCE_SCALE:log2_probe_intensity",
                "estimate": 0.5 + gene_index * 0.1 + study_index * 0.01,
                "se": 0.25,
                    "ci_lb": 0.0 + gene_index * 0.1 + study_index * 0.01,
                    "ci_ub": 1.0 + gene_index * 0.1 + study_index * 0.01,
                "p_value": 0.02 * (gene_index + 1),
                "status": "ESTIMABLE", "reason": "",
            })
    rows.append({
        **rows[0],
        "study": "synthetic-other-scale",
        "patient_set_id": "set-other",
        "source_family_id": "source-family-other-scale",
        "overlap_receipt_id": hashlib.sha256(b"other-scale").hexdigest(),
        "effect_scale_id": "OTHER_SCALE",
    })
    for study_index in range(3):
        rows.append({
            **rows[0],
            "study": f"synthetic-low-k-{study_index:02d}",
            "patient_set_id": f"low-k-set-{study_index:02d}",
            "source_family_id": f"source-family-low-k-{study_index:02d}",
            "overlap_receipt_id": hashlib.sha256(f"low-k-{study_index}".encode()).hexdigest(),
            "unit": "panel-low-k",
            "multiplicity_family_id": "low-k-family",
            "estimate": 0.4 + study_index * 0.01,
        })
    manifest = tmp_path / "meta_manifest.json"
    study_ids = tuple(sorted({row["study"] for row in rows}))
    write_synthetic_analysis_manifest(
        manifest, rows, study_ids=study_ids, kind="a_long_synthesis_input",
        overlap_receipts=_pairwise_overlap_receipts(rows),
    )
    result = synthesize_effects(
        rows,
        overlap_receipts=_pairwise_overlap_receipts(rows),
        study_ids=study_ids,
        provenance_manifest=manifest,
        policy=_synthesis_policy(
            {
                "predeclared_panels": ("panel-0", "panel-1", "panel-2"),
                "low-k-family": ("panel-low-k",),
            },
            ("gene-0", "gene-1", "gene-2"),
        ),
        acceptance=_acceptance(),
        output_dir=tmp_path / "meta",
        retention_dir=tmp_path / "meta-retention",
    )

    panels = [
        row for row in result.effects
        if row["unit_family"] == "panel"
        and row["unit"] in {"panel-0", "panel-1", "panel-2"}
        and row["effect_scale_id"] == "LOG2_TPMPLUS1_PANEL_MEAN"
    ]
    genes = [row for row in result.effects if row["unit_family"] == "m5m6_gene"]
    other_scale = [row for row in result.effects if row["effect_scale_id"] == "OTHER_SCALE"]
    assert len(panels) == 3 and all(row["k"] == "4" for row in panels)
    assert all(row["adjustment_method"] == "holm" for row in panels)
    assert len(genes) == 3 and all(row["adjustment_method"] == "BH_0.10_exploratory" for row in genes)
    assert len(other_scale) == 1 and other_scale[0]["k"] == "1"
    assert all(float(row["prediction_interval_lb"]) < float(row["prediction_interval_ub"]) for row in panels + genes)
    low_k = [row for row in result.effects if row["unit"] == "panel-low-k"]
    assert len(low_k) == 1 and low_k[0]["k"] == "3"
    assert low_k[0]["prediction_interval_lb"] == "NA"


def test_modified_kh_ad_hoc_variance_floor_does_not_shrink_below_fixed_effect_se(tmp_path):
    rows = []
    for index in range(3):
        rows.append({
            "study": f"invented-kh-study-{index}",
            "patient_set_id": f"invented-patient-family-{index}",
            "source_family_id": f"invented-source-family-{index}",
            "overlap_receipt_id": hashlib.sha256(f"kh-{index}".encode()).hexdigest(),
            "overlap_status": "DISJOINT_VERIFIED",
            "unit_family": "panel",
            "unit": "invented-panel",
            "panel_family": "invented-panel-family",
            "multiplicity_family_id": "invented-kh-family",
            "feature_method_id": "fixture-panel-score-v1",
            "analysis_method_id": "lm_change_response_covariates_v1",
            "endpoint_id": "invented-endpoint",
            "regimen_id": "invented-regimen",
            "window_id": "invented-window",
            "assay_id": "invented-assay",
            "effect_scale_id": "invented-log2-change",
            "estimate": 1.0,
            "se": 0.2,
            "ci_lb": 0.6,
            "ci_ub": 1.4,
            "p_value": 0.01,
            "status": "ESTIMABLE",
            "reason": "",
        })
    manifest = tmp_path / "kh_manifest.json"
    study_ids = tuple(row["study"] for row in rows)
    write_synthetic_analysis_manifest(
        manifest, rows, study_ids=study_ids, kind="a_long_synthesis_input",
        overlap_receipts=_pairwise_overlap_receipts(rows),
    )
    result = synthesize_effects(
        rows,
        overlap_receipts=_pairwise_overlap_receipts(rows),
        study_ids=study_ids,
        provenance_manifest=manifest,
        policy=_synthesis_policy({"invented-kh-family": ("invented-panel",)}, ("unused-gene",)),
        acceptance=_acceptance(),
        output_dir=tmp_path / "kh",
        retention_dir=tmp_path / "kh-retention",
    )
    pooled = result.effects[0]
    assert float(pooled["Q"]) == pytest.approx(0.0)
    # With QE/(k-1) = 0, ordinary KH would multiply the fixed-effect SE by
    # sqrt(0). The ad-hoc modification floors its scale factor at one.
    fixed_effect_se = 0.2 / (3 ** 0.5)
    ordinary_kh_se = fixed_effect_se * (0.0 / 2.0) ** 0.5
    assert ordinary_kh_se < fixed_effect_se
    assert float(pooled["se"]) == pytest.approx(fixed_effect_se)


def test_model_output_round_trips_into_synthesis_without_identity_relabeling(tmp_path):
    model_results = []
    study_ids = []
    for study_index in range(4):
        study = f"invented-e2e-study-{study_index}"
        study_ids.append(study)
        rows = []
        for index in range(8):
            response = "R" if index >= 4 else "NR"
            residual = (index % 4 - 1.5) * 0.2
            change = (3.0 if response == "R" else 2.0) + residual + study_index * 0.1
            rows.append({
                "study_id": study,
                "patient_key": f"invented-patient-{study_index}-{index}",
                "pair_id": f"invented-pair-{study_index}-{index}",
                "unit": "fixture-panel",
                "pre_value": float(index + 10),
                "on_value": float(index + 10) + change,
                "response": response,
                **_identity(
                    feature_method_id="A_LONG_FIXED_PANEL_SCORE",
                    panel_family="E2E_PANEL_FAMILY",
                    multiplicity_family_id="E2E_PANELS",
                    source_family_id=f"source-family-{study}",
                    overlap_receipt_id=hashlib.sha256(study.encode()).hexdigest(),
                ),
            })
        manifest = tmp_path / f"{study}-manifest.json"
        write_synthetic_analysis_manifest(manifest, rows, study_ids=(study,))
        model_results.append(fit_two_timepoint(
            rows,
            study_id=study,
            provenance_manifest=manifest,
            policy=_policy(),
            acceptance=_acceptance(),
            output_dir=tmp_path / f"{study}-model",
            retention_dir=tmp_path / f"{study}-retention",
        ))

    effects = model_effects_for_synthesis(model_results)
    assert len(effects) == 4
    assert {row["study"] for row in effects} == set(study_ids)
    assert all(row["patient_set_id"] and row["source_family_id"] for row in effects)
    synthesis_manifest = tmp_path / "e2e-synthesis-manifest.json"
    write_synthetic_analysis_manifest(
        synthesis_manifest,
        effects,
        study_ids=study_ids,
        kind="a_long_synthesis_input",
        overlap_receipts=_pairwise_overlap_receipts(effects),
    )
    result = synthesize_effects(
        effects,
        overlap_receipts=_pairwise_overlap_receipts(effects),
        study_ids=study_ids,
        provenance_manifest=synthesis_manifest,
        policy=_synthesis_policy({"E2E_PANELS": ("fixture-panel",)}, ("unused-gene",)),
        acceptance=_acceptance(),
        output_dir=tmp_path / "e2e-synthesis",
        retention_dir=tmp_path / "e2e-retention",
    )
    assert len(result.effects) == 1
    assert result.effects[0]["k"] == "4"
    assert result.effects[0]["independence_status"] == "DISJOINT_VERIFIED"
    assert result.effects[0]["adjustment_method"] == "holm"
    assert (tmp_path / "invented-e2e-study-0-model" / "longitudinal_support.tsv").is_file()


def test_partial_overlap_receipt_overrides_different_patient_set_ids(tmp_path):
    rows = []
    for index in range(2):
        rows.append({
            "study": f"invented-overlap-study-{index}",
            "patient_set_id": f"different-hash-looking-set-{index}",
            "source_family_id": f"source-family-{index}",
            "overlap_receipt_id": hashlib.sha256(f"overlap-{index}".encode()).hexdigest(),
            "overlap_status": "DISJOINT_VERIFIED",
            "unit_family": "panel",
            "unit": "fixture-panel",
            "panel_family": "OVERLAP_PANEL_FAMILY",
            "multiplicity_family_id": "OVERLAP_PANELS",
            "feature_method_id": "A_LONG_FIXED_PANEL_SCORE",
            "analysis_method_id": "lm_change_response_covariates_v1",
            "endpoint_id": "invented-endpoint",
            "regimen_id": "invented-regimen",
            "window_id": "invented-window",
            "assay_id": "invented-assay",
            "effect_scale_id": "invented-log2-change",
            "estimate": 0.4 + index * 0.1,
            "se": 0.2,
            "ci_lb": 0.0,
            "ci_ub": 0.8,
            "p_value": 0.04,
            "status": "ESTIMABLE",
            "reason": "",
        })
    manifest = tmp_path / "overlap-manifest.json"
    study_ids = tuple(row["study"] for row in rows)
    write_synthetic_analysis_manifest(
        manifest, rows, study_ids=study_ids, kind="a_long_synthesis_input",
        overlap_receipts=_pairwise_overlap_receipts(rows, status="OVERLAPPING"),
    )
    result = synthesize_effects(
        rows,
        overlap_receipts=_pairwise_overlap_receipts(rows, status="OVERLAPPING"),
        study_ids=study_ids,
        provenance_manifest=manifest,
        policy=_synthesis_policy({"OVERLAP_PANELS": ("fixture-panel",)}, ("unused-gene",)),
        acceptance=_acceptance(),
        output_dir=tmp_path / "overlap-synthesis",
        retention_dir=tmp_path / "overlap-retention",
    )
    summary = result.effects[0]
    assert summary["k"] == "0"
    assert summary["n_excluded"] == "2"
    assert summary["status"] == "NOT_ESTIMABLE"
    assert summary["reason"] == "source_independence_unresolved_or_overlapping"
    assert summary["p_value"] == "NA" and summary["adjusted_p"] == "NA"


def test_bh_uses_predeclared_denominator_and_keeps_unestimable_p_missing():
    policy = _synthesis_policy({}, ("gene-a", "gene-b", "gene-c"))
    rows = [
        {"unit_family": "m5m6_gene", "unit": "gene-a", "panel_family": "M5M6", "p_value": "0.02"},
        {"unit_family": "m5m6_gene", "unit": "gene-b", "panel_family": "M5M6", "p_value": "0.04"},
        {"unit_family": "m5m6_gene", "unit": "gene-c", "panel_family": "M5M6", "p_value": "NA"},
    ]

    _apply_scoped_fdr(rows, policy=policy)

    assert [float(rows[index]["adjusted_p"]) for index in (0, 1)] == pytest.approx([0.06, 0.06])
    assert rows[2]["adjusted_p"] == "NA"


def test_repeated_available_observations_keep_window_specific_support_and_synthesis_families(tmp_path):
    rows = []
    for index in range(8):
        response = "R" if index >= 4 else "NR"
        rows.append({
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}-baseline", "unit": "panel-a",
            "window": "baseline", "value": float(index + 10), "response": response,
            **_identity(
                window_id="baseline_to_approved_windows",
                analysis_method_id="lmerTest_lme4_response_window_random_intercept_v1",
            ),
        })
    for window, r_index in (("early", 4), ("late", 5)):
        for index in (0, 1, r_index):
            response = "R" if index >= 4 else "NR"
            rows.append({
                "study_id": "fixture-study", "patient_key": _patient(index),
                "pair_id": f"pair-{index:04d}-{window}", "unit": "panel-a",
                "window": window, "value": float(index + 12), "response": response,
                **_identity(
                    window_id="baseline_to_approved_windows",
                    analysis_method_id="lmerTest_lme4_response_window_random_intercept_v1",
                ),
            })
    policy = replace(
        _policy(windows=("baseline", "early", "late")),
        repeated_selection_mode="available_observations",
    )
    manifest = tmp_path / "available_manifest.json"
    write_synthetic_analysis_manifest(manifest, rows, study_ids=("fixture-study",))
    result = fit_repeated_windows(
        rows, study_id="fixture-study", provenance_manifest=manifest,
        policy=policy, acceptance=_acceptance(),
        output_dir=tmp_path / "available", retention_dir=tmp_path / "available-retention",
    )

    interactions = [row for row in result.effects if row["model"] == "repeated_response_by_window"]
    assert {row["window_id"] for row in interactions} == {"baseline_to_early", "baseline_to_late"}
    assert len(interactions) == 2
    assert all(row["status"] == "NOT_ESTIMABLE" for row in interactions)
    assert all(row["reason"] == "insufficient_response_group_precision_support_for_contrast" for row in interactions)
    assert all(row["n_R"] == "1" and row["n_NR"] == "2" for row in interactions)
    assert all(row["n_observations_fitted"] == "14" for row in interactions)
    assert all(row["n_observations_contrast"] == "6" for row in interactions)
    assert result.support["n_patients_used"] == "8"
    assert result.support["n_observations_used"] == "14"

    effects = model_effects_for_synthesis([result])
    assert {row["window_id"] for row in effects} == {"baseline_to_early", "baseline_to_late"}
    synthesis_policy = _synthesis_policy({"fixture_multiplicity_family": ("panel-a",)}, ("unused-gene",))
    synthesis_manifest = tmp_path / "available_synthesis_manifest.json"
    write_synthetic_analysis_manifest(
        synthesis_manifest, effects, study_ids=("fixture-study",),
        kind="a_long_synthesis_input", overlap_receipts=(),
    )
    synthesized = synthesize_effects(
        effects, overlap_receipts=(), study_ids=("fixture-study",),
        provenance_manifest=synthesis_manifest, policy=synthesis_policy,
        acceptance=_acceptance(), output_dir=tmp_path / "available-synthesis",
        retention_dir=tmp_path / "available-synthesis-retention",
    )
    assert len(synthesized.effects) == 2
    assert {row["window_id"] for row in synthesized.effects} == {"baseline_to_early", "baseline_to_late"}
    assert all(row["k"] == "0" and row["n_excluded"] == "1" for row in synthesized.effects)
    assert all(row["status"] == "NOT_ESTIMABLE" and row["reason"] == "no_estimable_effects" for row in synthesized.effects)
    assert all(row["p_value"] == "NA" and row["adjusted_p"] == "NA" for row in synthesized.effects)


def test_single_level_covariate_is_retained_as_nonestimable_while_other_unit_fits(tmp_path):
    rows = []
    for index in range(8):
        response = "R" if index >= 4 else "NR"
        noise = (index % 4 - 1.5) * 0.2
        for unit in ("single-level-unit", "valid-unit"):
            rows.append({
                "study_id": "fixture-study", "patient_key": _patient(index),
                "pair_id": f"pair-{index:04d}-{unit}", "unit": unit,
                "pre_value": float(index + 10),
                "on_value": float(index + 10) + (2.0 if response == "R" else 1.0) + noise,
                "response": response,
                "same_lesion": "true",
                "site": "one-level" if unit == "single-level-unit" else ("north" if index % 2 else "south"),
                **_identity(),
            })
    result = _fit(rows, tmp_path, policy=replace(
        _policy(covariates=("site",)), sensitivity_modes=("same_lesion",)
    ))

    by_unit = {row["unit"]: row for row in result.effects if row["model"] == "delta_primary"}
    assert by_unit["single-level-unit"]["status"] == "NOT_ESTIMABLE"
    assert by_unit["single-level-unit"]["reason"] == "model_matrix_error"
    assert by_unit["valid-unit"]["status"] == "ESTIMABLE"
    assert float(by_unit["valid-unit"]["estimate"]) == pytest.approx(1.0)
    sensitivity = {
        row["unit"]: row for row in result.effects if row["model"] == "delta_same_lesion_sensitivity"
    }
    assert sensitivity["single-level-unit"]["reason"] == "model_matrix_error"
    assert sensitivity["valid-unit"]["status"] == "ESTIMABLE"


def test_zero_uncertainty_is_not_estimable_and_is_preserved_as_synthesis_exclusion(tmp_path):
    rows = []
    for index in range(8):
        response = "R" if index >= 4 else "NR"
        rows.append({
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"pair-{index:04d}", "unit": "panel-a",
            "pre_value": float(index + 10), "on_value": float(index + 11),
            "response": response, **_identity(),
        })
    result = _fit(rows, tmp_path / "two-timepoint")
    primary = next(row for row in result.effects if row["model"] == "delta_primary")
    assert primary["status"] == "NOT_ESTIMABLE"
    assert primary["reason"] == "zero_residual_uncertainty"
    assert primary["se"] == "NA" and primary["p_value"] == "NA"

    effects = model_effects_for_synthesis([result])
    assert len(effects) == 1
    assert effects[0]["status"] == "NOT_ESTIMABLE"
    assert effects[0]["reason"] == "zero_residual_uncertainty"
    policy = _synthesis_policy({"fixture_multiplicity_family": ("panel-a",)}, ("unused-gene",))
    manifest = tmp_path / "zero_synthesis_manifest.json"
    write_synthetic_analysis_manifest(
        manifest, effects, study_ids=("fixture-study",), kind="a_long_synthesis_input", overlap_receipts=(),
    )
    synthesized = synthesize_effects(
        effects, overlap_receipts=(), study_ids=("fixture-study",), provenance_manifest=manifest,
        policy=policy, acceptance=_acceptance(), output_dir=tmp_path / "zero-synthesis",
        retention_dir=tmp_path / "zero-synthesis-retention",
    )
    assert synthesized.effects[0]["k"] == "0"
    assert synthesized.effects[0]["n_excluded"] == "1"
    assert synthesized.effects[0]["reason"] == "no_estimable_effects"
    assert synthesized.effects[0]["p_value"] == "NA"
    assert synthesized.effects[0]["adjusted_p"] == "NA"


def test_positive_uncertainty_is_invariant_to_expression_units(tmp_path):
    expected_values = (0.7, 0.9, 1.1, 1.3, 1.7, 1.9, 2.1, 2.3)
    results = []
    for scale, label in ((1.0, "unit-scale"), (1e-16, "tiny-scale")):
        rows = []
        for index, value in enumerate(expected_values):
            response = "NR" if index < 4 else "R"
            pre = (index + 1) * scale
            rows.append({
                "study_id": "fixture-study", "patient_key": _patient(index),
                "pair_id": f"scale-pair-{label}-{index:04d}", "unit": "scale-panel",
                "pre_value": pre, "on_value": pre + value * scale,
                "response": response, **_identity(),
            })
        result = _fit(rows, tmp_path / label)
        results.append(next(row for row in result.effects if row["model"] == "delta_primary"))

    ordinary, rescaled = results
    assert ordinary["status"] == rescaled["status"] == "ESTIMABLE"
    assert float(ordinary["estimate"]) == pytest.approx(1.0)
    assert float(ordinary["se"]) == pytest.approx(0.18257418583505539, rel=1e-12)
    assert float(ordinary["p_value"]) == pytest.approx(0.0015474212145409397, rel=1e-10)
    assert float(rescaled["estimate"]) == pytest.approx(float(ordinary["estimate"]) * 1e-16, rel=1e-10, abs=1e-32)
    assert float(rescaled["se"]) == pytest.approx(float(ordinary["se"]) * 1e-16, rel=1e-10, abs=1e-32)
    assert float(rescaled["p_value"]) == pytest.approx(float(ordinary["p_value"]), rel=1e-10, abs=1e-14)


def test_zero_uncertainty_randomized_and_repeated_contrasts_never_claim_estimability(tmp_path):
    arm_rows = []
    for index, arm in enumerate(("ICI_ONLY", "ICI_ONLY", "ICI_ONLY", "COMBINATION", "COMBINATION", "COMBINATION")):
        arm_rows.append({
            "study_id": "fixture-study", "patient_key": _patient(index),
            "pair_id": f"arm-pair-{index:04d}", "unit": "arm-panel",
            "pre_value": float(index), "on_value": float(index + 2), "arm": arm,
            **_identity(regimen_id="ICI_ONLY_VS_COMBINATION_RANDOMIZED",
                       analysis_method_id="lm_randomized_arm_change_contrast_v1"),
        })
    arm_manifest = tmp_path / "zero_arm_manifest.json"
    write_synthetic_analysis_manifest(arm_manifest, arm_rows, study_ids=("fixture-study",))
    arm_result = fit_randomized_arm(
        arm_rows, study_id="fixture-study", provenance_manifest=arm_manifest,
        policy=_policy(), acceptance=_acceptance(),
        admission=RandomizationAdmission("fixture-estimand", "TEST_ONLY", True, fixture_only=True),
        output_dir=tmp_path / "zero-arm", retention_dir=tmp_path / "zero-arm-retention",
    )
    assert arm_result.effects[0]["status"] == "NOT_ESTIMABLE"
    assert arm_result.effects[0]["reason"] == "zero_residual_uncertainty"
    assert arm_result.effects[0]["se"] == "NA" and arm_result.effects[0]["p_value"] == "NA"

    repeated_rows = []
    for index in range(8):
        response = "R" if index >= 4 else "NR"
        for window in ("baseline", "on"):
            repeated_rows.append({
                "study_id": "fixture-study", "patient_key": _patient(index),
                "pair_id": f"repeat-pair-{index:04d}-{window}", "unit": "repeat-panel",
                "window": window, "value": float(index + 10), "response": response,
                **_identity(window_id="baseline_to_on", analysis_method_id="lmerTest_lme4_response_window_random_intercept_v1"),
            })
    repeated_manifest = tmp_path / "zero_repeated_manifest.json"
    write_synthetic_analysis_manifest(repeated_manifest, repeated_rows, study_ids=("fixture-study",))
    repeated = fit_repeated_windows(
        repeated_rows, study_id="fixture-study", provenance_manifest=repeated_manifest,
        policy=_policy(), acceptance=_acceptance(),
        output_dir=tmp_path / "zero-repeated", retention_dir=tmp_path / "zero-repeated-retention",
    )
    effect = next(row for row in repeated.effects if row["model"] == "repeated_response_by_window")
    assert effect["status"] == "NOT_ESTIMABLE"
    assert effect["reason"] in {
        "singular_random_intercept_fit", "convergence_failure", "model_fit_error",
        "invalid_inference_precision", "interaction_contrast_missing",
    }
    assert effect["se"] == "NA" or float(effect["se"]) <= 0


def test_repeated_and_randomized_matrix_failures_do_not_drop_other_units(tmp_path):
    offsets = (0.0, 1.5, -0.7, 0.8, -1.2, 0.4, 0.6, -0.3)
    repeated_rows = []
    for index, offset in enumerate(offsets):
        response = "R" if index >= 4 else "NR"
        baseline = 10 + index * 2 + offset
        for unit in ("repeated-single-level", "repeated-valid"):
            for window, shift in (("baseline", 0.0), ("on", 1.0)):
                group_effect = 2.0 if response == "R" and window == "on" else 0.0
                repeated_rows.append({
                    "study_id": "fixture-study", "patient_key": _patient(index),
                    "pair_id": f"repeat-{index:04d}-{unit}-{window}", "unit": unit,
                    "window": window, "value": baseline + shift + group_effect + offset * (0.1 if window == "on" else 0),
                    "response": response,
                    "site": "one-level" if unit == "repeated-single-level" else ("north" if index % 2 else "south"),
                    **_identity(
                        window_id="baseline_to_on",
                        analysis_method_id="lmerTest_lme4_response_window_random_intercept_v1",
                    ),
                })
    repeated_manifest = tmp_path / "matrix_repeated_manifest.json"
    write_synthetic_analysis_manifest(repeated_manifest, repeated_rows, study_ids=("fixture-study",))
    repeated = fit_repeated_windows(
        repeated_rows, study_id="fixture-study", provenance_manifest=repeated_manifest,
        policy=_policy(covariates=("site",)), acceptance=_acceptance(),
        output_dir=tmp_path / "matrix-repeated", retention_dir=tmp_path / "matrix-repeated-retention",
    )
    repeated_by_unit = {
        unit: next(row for row in repeated.effects if row["unit"] == unit)
        for unit in ("repeated-single-level", "repeated-valid")
    }
    assert repeated_by_unit["repeated-single-level"]["reason"] == "model_matrix_error"
    assert repeated_by_unit["repeated-valid"]["reason"] != "model_matrix_error"

    randomized_rows = []
    arms = ("ICI_ONLY",) * 4 + ("COMBINATION",) * 4
    for index, (offset, arm) in enumerate(zip(offsets, arms)):
        pre = 10 + index * 2 + offset
        change = (3.0 if arm == "COMBINATION" else 1.0) + offset * 0.1
        for unit in ("arm-single-level", "arm-valid"):
            randomized_rows.append({
                "study_id": "fixture-study", "patient_key": _patient(index),
                "pair_id": f"arm-{index:04d}-{unit}", "unit": unit,
                "pre_value": pre, "on_value": pre + change, "arm": arm,
                "site": "one-level" if unit == "arm-single-level" else ("north" if index % 2 else "south"),
                **_identity(
                    regimen_id="ICI_ONLY_VS_COMBINATION_RANDOMIZED",
                    analysis_method_id="lm_randomized_arm_change_contrast_v1",
                ),
            })
    randomized_manifest = tmp_path / "matrix_randomized_manifest.json"
    write_synthetic_analysis_manifest(randomized_manifest, randomized_rows, study_ids=("fixture-study",))
    randomized = fit_randomized_arm(
        randomized_rows, study_id="fixture-study", provenance_manifest=randomized_manifest,
        policy=_policy(covariates=("site",)), acceptance=_acceptance(),
        admission=RandomizationAdmission("fixture-estimand", "TEST_ONLY", True, fixture_only=True),
        output_dir=tmp_path / "matrix-randomized", retention_dir=tmp_path / "matrix-randomized-retention",
    )
    randomized_by_unit = {row["unit"]: row for row in randomized.effects}
    assert randomized_by_unit["arm-single-level"]["reason"] == "model_matrix_error"
    assert randomized_by_unit["arm-valid"]["status"] == "ESTIMABLE"
    assert float(randomized_by_unit["arm-valid"]["estimate"]) == pytest.approx(2.0, abs=0.1)
