from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from tools.a_meta.provenance import known_cohort_ids
from tools.a1.pairing import (
    CrosswalkAcceptance,
    PairingPolicy,
    PolicyAcceptance,
    SourceColumns,
    WindowRule,
    build_pairs,
    read_specimens,
    validate_pairing_policy,
    write_synthetic_pair_manifest,
    write_pair_products,
)


def _policy(*, status="PROPOSED"):
    return PairingPolicy(
        study_id="fixture-study",
        status=status,
        decision_ref="fixture-policy" if status == "ACCEPTED" else None,
        baseline_window="baseline",
        windows=(
            WindowRule("baseline", "baseline", categories=("PRE",)),
            WindowRule(
                "on_day_10",
                "followup",
                categories=("ON",),
                day_interval=(8, 12),
                day_origin="first-dose",
                target_day=10,
            ),
        ),
        baseline_hierarchy=("research_core", "diagnostic_core"),
        allowed_prior_treatment=("none",),
        allowed_disease_states=("no_progression",),
        allowed_regimen_states=("stable",),
        prefer_same_lesion=True,
        allow_different_lesion=True,
        endpoint_id="fixture_endpoint",
        admission_receipt="invented-N12-receipt",
    )


def _acceptance():
    return PolicyAcceptance(
        decision_id="N12",
        record_ref="invented-fixture-only",
        fixture_only=True,
    )


def _row(*, patient, specimen, category, day="", lesion="lesion-a", assay=None, study="fixture-study", **changes):
    assay = assay or f"{specimen}-assay"
    row = {
        "study_id": study,
        "patient_id": patient,
        "specimen_id": specimen,
        "assay_id": assay,
        "timepoint_category": category,
        "collection_day": day,
        "day_precision": "exact" if day else "unknown",
        "index_episode": "episode-1",
        "exposure": "ici-only",
        "baseline_source": "research_core",
        "prior_treatment": "none",
        "disease_state": "no_progression",
        "regimen_state": "stable",
        "compartment": "tumour",
        "platform": "rnaseq",
        "unit": "tpm",
        "assay_method": "whole_transcriptome",
        "assay_qualified": "yes",
        "lesion_id": lesion,
        "source_locator": f"fixture://{specimen}",
        "source_confidence": "invented_high",
        "day_origin": "first-dose" if day else "unknown",
        "annotation_id": "fixture-annotation-v1",
        "measurement_comparability_id": "fixture-tpm-v1",
        "endpoint_id": "fixture_endpoint",
        "admission_receipt": "invented-N12-receipt",
    }
    row.update(changes)
    return row


def _pair_ids(result):
    return [(row["pair_id"], row["selected"]) for row in result.candidates]


def test_unsigned_window_policy_is_rejected_before_rows_are_consumed():
    class UnreadableRows:
        def __iter__(self):
            raise AssertionError("policy preflight must run before specimen access")

    with pytest.raises(ValueError, match="unsigned"):
        build_pairs(UnreadableRows(), _policy(), classification="synthetic")


def test_accepted_status_and_matching_arbitrary_reference_are_not_a_signature():
    arbitrary_policy = replace(
        _policy(), status="ACCEPTED", decision_ref="some-text",
        source_family_id="invented-family",
        overlap_receipt_id=hashlib.sha256(b"invented-overlap").hexdigest(),
        overlap_status="UNRESOLVED",
    )
    arbitrary_acceptance = PolicyAcceptance(
        decision_id="N12", record_ref="some-text", fixture_only=False,
    )
    with pytest.raises(PermissionError, match="scoped user-release"):
        validate_pairing_policy(
            arbitrary_policy,
            classification="real",
            acceptance=arbitrary_acceptance,
        )


def test_pair_ids_and_selection_are_invariant_to_input_permutation():
    rows = [
        _row(patient="patient-001", specimen="specimen-pre", category="PRE"),
        _row(patient="patient-001", specimen="specimen-on-a", category="ON", day="9"),
        _row(patient="patient-001", specimen="specimen-on-b", category="ON", day="11", lesion="lesion-b"),
    ]
    policy = _policy()
    first = build_pairs(rows, policy, classification="synthetic", acceptance=_acceptance())
    second = build_pairs(list(reversed(rows)), policy, classification="synthetic", acceptance=_acceptance())

    assert _pair_ids(first) == _pair_ids(second)
    selected = [row for row in first.candidates if row["selected"]]
    assert len(selected) == 1
    assert selected[0]["on_specimen_id"] == "specimen-on-a"
    assert selected[0]["pre_source_locator"] == "fixture://specimen-pre"
    assert selected[0]["on_source_confidence"] == "invented_high"
    assert selected[0]["pre_admission_receipt"] == "invented-N12-receipt"
    assert selected[0]["on_measurement_comparability_id"] == "fixture-tpm-v1"
    assert selected[0]["selected_reason"] == (
        "baseline_hierarchy_then_time_relevance_then_compatible_assay_"
        "then_allowed_same_lesion_then_opaque_tie_break"
    )


def test_pair_product_hashes_are_permutation_invariant_and_keep_empty_windows(tmp_path):
    rows = [
        _row(patient="patient-001", specimen="specimen-pre", category="PRE"),
        _row(patient="patient-001", specimen="specimen-on", category="ON", day="9"),
    ]
    policy = replace(
        _policy(),
        windows=(
            *_policy().windows,
            WindowRule(
                "on_day_20", "followup", categories=("ON_LATE",),
                day_interval=(18, 22), day_origin="first-dose", target_day=20,
            ),
        ),
    )
    first = build_pairs(rows, policy, classification="synthetic", acceptance=_acceptance())
    second = build_pairs(rows[::-1], policy, classification="synthetic", acceptance=_acceptance())
    first_paths = write_pair_products(first, tmp_path / "first")
    second_paths = write_pair_products(second, tmp_path / "second")

    first_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in first_paths.items()
    }
    second_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in second_paths.items()
    }
    assert first_hashes == second_hashes
    assert first.summary["selected_by_window"] == {"on_day_10": 1, "on_day_20": 0}
    support = first_paths["longitudinal_support"].read_text(encoding="utf-8")
    assert "on_day_20\t0\tone_way_corroboration_only" in support


def test_equal_day_ties_use_the_same_opaque_tie_break_after_permutation():
    rows = [
        _row(patient="patient-001", specimen="specimen-pre", category="PRE"),
        _row(patient="patient-001", specimen="specimen-on-a", category="ON", day="10", lesion="lesion-a"),
        _row(patient="patient-001", specimen="specimen-on-b", category="ON", day="10", lesion="lesion-b"),
    ]
    policy = _policy()
    first = build_pairs(rows, policy, classification="synthetic", acceptance=_acceptance())
    second = build_pairs(rows[::-1], policy, classification="synthetic", acceptance=_acceptance())

    selected_first = next(row for row in first.candidates if row["selected"])
    selected_second = next(row for row in second.candidates if row["selected"])
    assert selected_first["on_specimen_id"] == selected_second["on_specimen_id"]
    assert selected_first["on_day_raw"] == selected_second["on_day_raw"] == "10"


def test_baseline_hierarchy_and_all_approved_followup_windows_are_applied():
    policy = replace(
        _policy(),
        windows=(
            WindowRule("baseline", "baseline", categories=("PRE",)),
            WindowRule("on_early", "followup", categories=("ON_EARLY",), day_interval=(8, 12), day_origin="first-dose", target_day=10),
            WindowRule("on_late", "followup", categories=("ON_LATE",), day_interval=(20, 24), day_origin="first-dose", target_day=22),
        ),
    )
    rows = [
        _row(patient="patient-001", specimen="baseline-secondary", category="PRE", baseline_source="diagnostic_core"),
        _row(patient="patient-001", specimen="baseline-primary", category="PRE", baseline_source="research_core"),
        _row(patient="patient-001", specimen="followup-early", category="ON_EARLY", day="10"),
        _row(patient="patient-001", specimen="followup-late", category="ON_LATE", day="22"),
    ]
    result = build_pairs(rows, policy, classification="synthetic", acceptance=_acceptance())

    selected = [row for row in result.candidates if row["selected"]]
    assert {row["on_window"] for row in selected} == {"on_early", "on_late"}
    assert {row["pre_specimen_id"] for row in selected} == {"baseline-primary"}
    assert result.summary["selected_by_window"] == {"on_early": 1, "on_late": 1}


def test_higher_priority_baseline_is_selected_before_lesion_compatibility():
    rows = [
        _row(patient="patient-001", specimen="baseline-primary", category="PRE", lesion="lesion-a"),
        _row(patient="patient-001", specimen="baseline-secondary", category="PRE", lesion="lesion-b", baseline_source="diagnostic_core"),
        _row(patient="patient-001", specimen="followup-lesion-b", category="ON", day="10", lesion="lesion-b"),
    ]
    result = build_pairs(rows, replace(_policy(), allow_different_lesion=False), classification="synthetic", acceptance=_acceptance())

    assert result.summary["selected_pairs"] == 0
    assert any(
        row.get("pre_specimen_id") == "baseline-secondary" and row["reason"] == "lower_priority_baseline"
        for row in result.exclusions
    )
    assert result.missing_followups[0]["reason"] == "no_compatible_followup"


def test_categorical_window_keeps_day_unknown_and_timing_conflicts_need_adjudication():
    rows = [
        _row(patient="patient-001", specimen="specimen-pre", category="PRE"),
        _row(patient="patient-001", specimen="specimen-on-category-only", category="ON"),
        _row(patient="patient-001", specimen="specimen-on-day-unqualified", category="ON", day="10", day_precision="unknown"),
        _row(patient="patient-002", specimen="specimen-pre-2", category="PRE"),
        _row(patient="patient-002", specimen="specimen-conflict", category="ON", day="3"),
    ]
    result = build_pairs(rows, _policy(), classification="synthetic", acceptance=_acceptance())

    category_only = next(row for row in result.candidates if row["on_specimen_id"] == "specimen-on-category-only")
    assert category_only["on_day_raw"] == ""
    assert category_only["on_day_numeric"] is None
    assert category_only["day_distance_to_target"] is None
    assert category_only["on_window"] == "on_day_10"
    unqualified_day = next(row for row in result.candidates if row["on_specimen_id"] == "specimen-on-day-unqualified")
    assert unqualified_day["on_day_raw"] == "10"
    assert unqualified_day["on_day_numeric"] is None
    assert unqualified_day["day_distance_to_target"] is None
    assert any(row["specimen_id"] == "specimen-conflict" and row["reason"] == "timing_contradiction" for row in result.exclusions)


def test_missing_followup_and_endpoint_counts_are_unavailable_not_zero():
    result = build_pairs(
        [_row(patient="patient-001", specimen="specimen-pre", category="PRE")],
        _policy(),
        classification="synthetic",
        acceptance=_acceptance(),
    )

    assert result.summary["patients_with_baseline"] == 1
    assert result.summary["patients_with_followup"] == 0
    assert result.summary["patients_paired"] == 0
    assert result.summary["endpoint_evaluable_counts"] is None
    assert result.missing_followups[0]["reason"] == "no_followup_specimen"


def test_pairing_rejects_cross_patient_episode_exposure_platform_and_unit_mismatches():
    rows = [
        _row(patient="patient-001", specimen="pre-a", category="PRE"),
        _row(patient="patient-002", specimen="on-b", category="ON", day="10"),
        _row(patient="patient-003", specimen="pre-c", category="PRE"),
        _row(patient="patient-003", specimen="on-c", category="ON", day="10", index_episode="episode-2"),
        _row(patient="patient-004", specimen="pre-d", category="PRE"),
        _row(patient="patient-004", specimen="on-d", category="ON", day="10", exposure="ici-plus-chemo"),
        _row(patient="patient-005", specimen="pre-e", category="PRE"),
        _row(patient="patient-005", specimen="on-e-platform", category="ON", day="10", platform="microarray"),
        _row(patient="patient-006", specimen="pre-f", category="PRE"),
        _row(patient="patient-006", specimen="on-f-unit", category="ON", day="10", unit="fpkm"),
    ]
    result = build_pairs(rows, _policy(), classification="synthetic", acceptance=_acceptance())

    assert result.summary["patients_paired"] == 0
    reasons = {row["reason"] for row in result.exclusions}
    assert {"patient_mismatch", "episode_mismatch", "exposure_mismatch", "assay_incompatible"} <= reasons


def test_prior_treatment_switch_stop_progression_and_unqualified_assays_are_excluded():
    rows = [
        _row(patient="patient-001", specimen="pre-prior", category="PRE", prior_treatment="present"),
        _row(patient="patient-001", specimen="on-prior", category="ON", day="10"),
        _row(patient="patient-002", specimen="pre-switch", category="PRE"),
        _row(patient="patient-002", specimen="on-switch", category="ON", day="10", regimen_state="changed"),
        _row(patient="patient-003", specimen="pre-stop", category="PRE"),
        _row(patient="patient-003", specimen="on-stop", category="ON", day="10", regimen_state="after_stop"),
        _row(patient="patient-004", specimen="pre-progress", category="PRE"),
        _row(patient="patient-004", specimen="on-progress", category="ON", day="10", disease_state="progression"),
        _row(patient="patient-005", specimen="pre-qc", category="PRE"),
        _row(patient="patient-005", specimen="on-qc", category="ON", day="10", assay_qualified="no"),
    ]
    result = build_pairs(rows, _policy(), classification="synthetic", acceptance=_acceptance())

    reasons = {row["reason"] for row in result.exclusions}
    assert {"prior_treatment_baseline", "regimen_changed", "after_stop", "progression", "assay_not_qualified"} <= reasons
    assert result.summary["patients_paired"] == 0


def test_two_followups_technical_replicates_and_lesion_counts_are_retained():
    rows = [
        _row(patient="patient-001", specimen="pre", category="PRE", assay="pre-assay-a"),
        _row(patient="patient-001", specimen="pre", category="PRE", assay="pre-assay-b"),
        _row(patient="patient-001", specimen="on-1", category="ON", day="9", assay="on-assay-a"),
        _row(patient="patient-001", specimen="on-1", category="ON", day="9", assay="on-assay-b"),
        _row(patient="patient-001", specimen="on-2", category="ON", day="11", lesion="lesion-b", assay="on-assay-c"),
    ]
    result = build_pairs(rows, _policy(), classification="synthetic", acceptance=_acceptance())

    assert len(result.candidates) == 6
    assert sum(row["selected"] for row in result.candidates) == 1
    assert result.summary["technical_replicate_specimens"] == 2
    assert result.summary["same_lesion_pairs"] == 1
    assert result.summary["platform_counts"] == {"rnaseq/tpm": 1}


def test_source_reader_selects_only_named_columns_and_checks_manifest(tmp_path):
    input_path = tmp_path / "specimens.tsv"
    manifest_path = tmp_path / "manifest.json"
    columns = SourceColumns(
        study_id="study", patient_id="subject", specimen_id="specimen",
        assay_id="assay", timepoint_category="timepoint", collection_day="day",
        day_precision="precision", index_episode="episode", exposure="exposure",
        baseline_source="baseline_source", prior_treatment="prior", disease_state="disease",
        regimen_state="regimen", compartment="compartment", platform="platform",
        unit="unit", assay_method="method", assay_qualified="qualified", lesion_id="lesion",
    )
    input_path.write_text(
        "study\tsubject\tspecimen\tassay\ttimepoint\tday\tprecision\tepisode\texposure\tbaseline_source\tprior\tdisease\tregimen\tcompartment\tplatform\tunit\tmethod\tqualified\tlesion\tTumor_Shrinkage\n"
        "fixture-study\tpatient-001\tspecimen-pre\tassay-a\tPRE\t\tunknown\tepisode-1\tici-only\tresearch_core\tnone\tno_progression\tstable\ttumour\trnaseq\ttpm\twhole_transcriptome\tyes\tlesion-a\tSECRET\n",
        encoding="utf-8",
    )
    write_synthetic_pair_manifest(input_path, manifest_path, study_id="fixture-study")

    rows = read_specimens(
        input_path,
        columns=columns,
        study_id="fixture-study",
        classification="synthetic",
        provenance_manifest=manifest_path,
    )

    assert len(rows) == 1
    assert "Tumor_Shrinkage" not in rows[0]
    assert rows[0]["collection_day"] == ""


def test_gide_crosswalk_does_not_activate_from_presence_alone():
    rows = [_row(patient="patient-001", specimen="specimen-pre", category="PRE")]
    crosswalk = {"source-patient": "opaque-patient"}

    with pytest.raises(ValueError, match="explicit user acceptance"):
        build_pairs(
            rows,
            _policy(),
            classification="synthetic",
            acceptance=_acceptance(),
            crosswalk=crosswalk,
            use_gide_crosswalk=True,
        )


def test_gide_crosswalk_applies_only_with_explicit_fixture_record_and_option():
    policy = replace(_policy(), study_id="gide-invented-fixture")
    rows = [
        _row(patient="source-patient-a", specimen="specimen-pre", category="PRE", study="gide-invented-fixture"),
        _row(patient="source-patient-a", specimen="specimen-on", category="ON", day="10", study="gide-invented-fixture"),
    ]
    result = build_pairs(
        rows,
        policy,
        classification="synthetic",
        acceptance=_acceptance(),
        crosswalk=CrosswalkAcceptance(
            {"source-patient-a": "opaque-patient-a"},
            "invented-crosswalk-record",
            fixture_only=True,
        ),
        use_gide_crosswalk=True,
    )

    assert result.candidates[0]["patient_id"] == "opaque-patient-a"


def test_protected_or_registered_real_id_cannot_claim_synthetic_provenance():
    rows = [_row(patient="patient-001", specimen="specimen-pre", category="PRE")]
    policy = PairingPolicy(**{**_policy().__dict__, "study_id": "imvigor210"})

    with pytest.raises(ValueError, match="locked final test"):
        build_pairs(rows, policy, classification="synthetic", acceptance=_acceptance())

    registered = next(value for value in sorted(known_cohort_ids()) if value != "imvigor210")
    registered_policy = replace(_policy(), study_id=registered)
    with pytest.raises(ValueError, match="known real cohort"):
        build_pairs(rows, registered_policy, classification="synthetic", acceptance=_acceptance())
    lower_policy = replace(_policy(), study_id=registered.casefold())
    with pytest.raises(ValueError, match="known real cohort"):
        build_pairs(rows, lower_policy, classification="synthetic", acceptance=_acceptance())


def test_protected_real_source_is_refused_before_opening_its_path(tmp_path):
    with pytest.raises(ValueError, match="locked final test"):
        read_specimens(
            tmp_path / "unreadable.tsv",
            columns=SourceColumns(
                study_id="study", patient_id="patient", specimen_id="specimen",
                assay_id="assay", timepoint_category="timepoint", index_episode="episode",
                exposure="exposure", baseline_source="baseline_source", prior_treatment="prior",
                disease_state="disease", regimen_state="regimen", compartment="compartment",
                platform="platform", unit="unit", assay_method="method", assay_qualified="qualified",
            ),
            study_id="imvigor210",
            classification="real",
        )
