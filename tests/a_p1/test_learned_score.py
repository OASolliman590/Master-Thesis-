from __future__ import annotations

import csv
from collections import Counter

import pytest

from tools.a_meta.provenance import is_locked_study, known_cohort_ids
from tools.a_p1 import (
    analyze_records,
    create_synthetic_learned_manifest,
    create_synthetic_manifest,
    learned_score_sensitivity,
)


PRIMARY = [
    {"study_id": "invented-study-a", "patient_key": f"invented-{key}",
     "index_episode_id": "invented-episode-1", "category": category}
    for key, category in (("01", "O"), ("02", "SD"), ("03", "PD"))
]
SCORES = [
    {"study_id": "invented-study-a", "patient_key": f"invented-{key}",
     "index_episode_id": "invented-episode-1", "score": score}
    for key, score in (("01", 0.9), ("02", 0.5), ("03", 0.1))
]


def tsv_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def manifest(scores=SCORES, *, score_kind="single_frozen_equation", fitting=()):
    return create_synthetic_learned_manifest(
        scores,
        equation_id="invented-frozen-equation-v1",
        equation_sha256="1" * 64,
        feature_selection_patients=list(fitting),
        fitting_patients=[],
        tuning_patients=[],
        score_kind=score_kind,
        training_source_sha256=["2" * 64],
    )


def test_future_frozen_learned_score_requires_disjoint_predictions_and_one_equation():
    provenance = manifest()

    result = learned_score_sensitivity(SCORES, provenance, PRIMARY)

    assert result["status"] == "estimated_synthetic_fixture"
    assert result["equation_id"] == "invented-frozen-equation-v1"
    assert result["score_kind"] == "single_frozen_equation"
    assert result["studies"]["invented-study-a"]["auc_orr"] == 1.0
    assert result["studies"]["invented-study-a"]["auc_dcr"] == 1.0
    assert result["analysis_identity"] == "A_P1_LEARNED_SCORE_SECONDARY_V1"
    assert result["prediction_payload_sha256"] == provenance["payload_sha256"]
    assert len(result["score_hash_sha256"]) == 64
    assert result["score_mapping_version"] == "A_P1_SINGLE_FROZEN_EQUATION_V1"
    assert result["endpoint_mapping_version"] == "A_P1_ORR_DCR_CRPR_SD_PD_V1"
    assert result["uncertainty_status"] == (
        "not_run_standalone_point_summary_requires_joint_a_p1_analysis"
    )


def test_prediction_overlap_with_feature_selection_is_rejected():
    bad = manifest(fitting=[{"study_id": "invented-study-a", "patient_key": "invented-01"}])

    with pytest.raises(ValueError, match="disjoint"):
        learned_score_sensitivity(SCORES, bad, PRIMARY)


def test_outer_fold_scores_and_missing_prediction_provenance_are_rejected():
    with pytest.raises(ValueError, match="single frozen equation"):
        learned_score_sensitivity(SCORES, manifest(score_kind="outer_fold_scores"), PRIMARY)

    bad = manifest()
    bad["prediction_patients"] = []
    with pytest.raises(ValueError, match="prediction set"):
        learned_score_sensitivity(SCORES, bad, PRIMARY)


def test_public_learned_api_preflights_release_before_traversing_rows():
    class UntouchedRows:
        def __iter__(self):
            raise AssertionError("learned predictions were traversed before release preflight")

        def __len__(self):
            raise AssertionError("learned predictions were measured before release preflight")

        def __getitem__(self, index):
            raise AssertionError("learned predictions were indexed before release preflight")

    known_id = next(
        value
        for value in sorted(known_cohort_ids())
        if "invented" not in value.casefold() and not is_locked_study(value)
    )
    locked = {
        "manifest_version": 1,
        "kind": "a_p1_learned_score",
        "data_classification": "real",
        "cohort_ids": [known_id],
    }

    with pytest.raises(PermissionError, match="allow-outcomes"):
        learned_score_sensitivity(
            UntouchedRows(), locked, [], data_classification="real", allow_outcomes=False
        )


@pytest.mark.requires_r
def test_learned_score_uses_category_eligible_patients_independently_of_cyt(tmp_path):
    source_rows = []
    patient_categories = (
        ("01", "CR", 9.0), ("02", "PR", 4.0),
        ("03", "SD", None), ("04", "SD", 1.0),
        ("05", "PD", 1.0), ("06", "PD", 4.0),
    )
    for key, category, gzma in patient_categories:
        source_rows.append({
            "study_id": "invented-study-a",
            "cancer": "invented-cancer-a",
            "patient_key": f"invented-patient-{key}",
            "specimen_key": f"invented-specimen-{key}",
            "index_episode_id": "invented-index-episode",
            "is_index_specimen": True,
            "expression_episode_id": "invented-index-episode",
            "outcome_episode_id": "invented-index-episode",
            "response_category": category,
            "source_criteria": "invented-criteria-v1",
            "evaluation_window": "invented-window-v1",
            "TPM_GZMA": gzma,
            "TPM_PRF1": 9.0,
        })
    scores = [
        {
            "study_id": "invented-study-a",
            "patient_key": f"invented-patient-{key}",
            "index_episode_id": "invented-index-episode",
            "score": score,
        }
        for key, score in (("01", 0.9), ("02", 0.8), ("03", 0.6),
                           ("04", 0.4), ("05", 0.2), ("06", 0.1))
    ]
    provenance = create_synthetic_learned_manifest(
        scores,
        equation_id="invented-frozen-equation-v1",
        equation_sha256="1" * 64,
        feature_selection_patients=[{"study_id": "invented-study-a", "patient_key": "invented-feature-fit"}],
        fitting_patients=[{"study_id": "invented-study-a", "patient_key": "invented-model-fit"}],
        tuning_patients=[{"study_id": "invented-study-a", "patient_key": "invented-model-tune"}],
        score_kind="single_frozen_equation",
        training_source_sha256=["2" * 64],
    )
    measurement = {
        "representation_id": "invented-qualified-tpm-v1",
        "unit": "TPM",
        "transform": "unlogged_abundance",
        "gene_mapping": "unique",
        "qualification_status": "qualified",
    }

    result = analyze_records(
        source_rows,
        create_synthetic_manifest(source_rows, measurement),
        tmp_path / "independent-eligibility",
        synthesis_contract={
            "collection_id": "invented-independent-score-collection",
            "decision_status": "INVENTED_FIXTURE",
            "studies": [{
                "study_id": "invented-study-a",
                "cancer": "invented-cancer-a",
                "cancer_weight": 1.0,
                "study_weight": 1.0,
            }],
        },
        learned_score_records=scores,
        learned_score_provenance=provenance,
    )

    cyt = result["studies"]["invented-study-a"]
    learned = result["learned_score_secondary"]["studies"]["invented-study-a"]
    assert cyt["category_counts"] == {"O": 2, "SD": 1, "PD": 2}
    assert learned["category_counts"] == {"O": 2, "SD": 2, "PD": 2}
    assert learned["status"] == "informative"
    assert learned["bootstrap"]["status"] == "estimated"
    assert learned["bootstrap"]["stream"] == cyt["bootstrap"]["stream"] == "a_p1_bootstrap"
    assert learned["bootstrap"]["assignment_receipt_sha256"] == cyt["bootstrap"]["assignment_receipt_sha256"]
    assert result["learned_score_secondary"]["uncertainty_status"] == (
        "per_study_bootstrap_intervals_available"
    )
    assert result["learned_score_secondary"]["synthesis"]["interval_status"] == (
        "estimated_conditional_on_original_category_counts"
    )
    assert result["learned_score_secondary"]["synthesis"]["bootstrap"]["seed"] == 20261108
    assert result["learned_score_secondary"]["prediction_payload_sha256"] == provenance["payload_sha256"]

    r_input_path = next((tmp_path / "independent-eligibility" / ".a_p1_work").rglob("analysis_input.tsv"))
    r_rows = tsv_rows(r_input_path)
    assert Counter(row["score_method"] for row in r_rows) == {"CYT": 5, "LEARNED": 6}
    assert any(row["score_method"] == "LEARNED" and row["patient_key"] == "invented-patient-03"
               for row in r_rows)
    assert not any(row["score_method"] == "CYT" and row["patient_key"] == "invented-patient-03"
                   for row in r_rows)
    assignment_rows = tsv_rows(
        tmp_path / "independent-eligibility" / "r" / "bootstrap_assignments.tsv"
    )
    for assignment in assignment_rows:
        sampled = r_rows[int(assignment["row_index"]) - 1]
        assert sampled["score_method"] == assignment["series"]
        assert sampled["study_id"] == assignment["study"]
        assert sampled["category"] == assignment["stratum"]
