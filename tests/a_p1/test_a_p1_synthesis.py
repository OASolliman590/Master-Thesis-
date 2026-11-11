from __future__ import annotations

import pytest

from tools.a_p1 import synthesize_studies


def study(auc_orr, auc_dcr, *, status="informative"):
    return {
        "auc_orr": auc_orr,
        "auc_dcr": auc_dcr,
        "delta": None if auc_orr is None or auc_dcr is None else auc_dcr - auc_orr,
        "status": status,
        "informative": status == "informative",
    }


def contract():
    return {
        "collection_id": "invented-collection-v1",
        "decision_status": "INVENTED_FIXTURE",
        "studies": [
            {"study_id": "invented-a1", "cancer": "invented-a", "cancer_weight": 0.6, "study_weight": 0.75},
            {"study_id": "invented-a2", "cancer": "invented-a", "cancer_weight": 0.6, "study_weight": 0.25},
            {"study_id": "invented-b1", "cancer": "invented-b", "cancer_weight": 0.4, "study_weight": 0.25},
            {"study_id": "invented-b2", "cancer": "invented-b", "cancer_weight": 0.4, "study_weight": 0.75},
        ],
    }


def test_synthesis_uses_explicit_cancer_then_study_weights_on_within_study_aucs():
    summaries = {
        "invented-a1": study(0.25, 0.75),
        "invented-a2": study(0.75, 0.25),
        "invented-b1": study(0.5, 0.5),
        "invented-b2": study(0.9, 0.6),
    }

    result = synthesize_studies(summaries, contract(), data_classification="synthetic")

    assert result["status"] == "estimated_synthetic_fixture"
    assert result["weighting"] == pytest.approx({
        "invented-a1": 0.45,
        "invented-a2": 0.15,
        "invented-b1": 0.1,
        "invented-b2": 0.3,
    })
    assert result["weighted_mean_within_study_auc_orr"] == pytest.approx(0.545)
    assert result["weighted_mean_within_study_auc_dcr"] == pytest.approx(0.605)
    assert result["weighted_mean_within_study_delta"] == pytest.approx(0.06)
    assert result["cross_study_pooled_auc"] is None
    assert result["interval"] is None
    assert result["interval_status"] == "awaiting_joint_patient_bootstrap"
    assert result["decomposition_verified"] is True
    assert result["analysis_identity"] != "A_P2"
    assert "still required before real synthesis" in result["real_release_requirement"]


def test_noninformative_no_sd_study_is_not_silently_dropped_or_renormalized():
    summaries = {
        "invented-a1": study(0.5, 0.5),
        "invented-a2": study(0.4, 0.4, status="structurally_zero_no_sd"),
        "invented-b1": study(0.5, 0.5),
        "invented-b2": study(0.5, 0.5),
    }

    result = synthesize_studies(summaries, contract(), data_classification="synthetic")

    assert result["status"] == "not_estimable_noninformative_studies_in_declared_roster"
    assert result["cross_study_pooled_auc"] is None
    assert result["noninformative_studies"] == ["invented-a2"]


def test_no_sd_study_can_be_excluded_only_by_its_explicit_zero_weight():
    summaries = {
        "invented-a1": study(0.5, 0.5),
        "invented-a2": study(0.4, 0.4, status="structurally_zero_no_sd"),
        "invented-b1": study(0.5, 0.5),
        "invented-b2": study(0.5, 0.5),
    }
    declared = contract()
    declared["studies"][0]["study_weight"] = 1.0
    declared["studies"][1]["study_weight"] = 0.0

    result = synthesize_studies(summaries, declared, data_classification="synthetic")

    assert result["status"] == "estimated_synthetic_fixture"
    assert result["excluded_noninformative_studies"] == ["invented-a2"]
    assert "invented-a2" not in result["weighting"]


def test_real_synthesis_without_a_signed_setting_reports_the_release_requirement():
    result = synthesize_studies(
        {"invented-a1": study(0.5, 0.5)}, None, data_classification="real"
    )

    assert result["status"] == "blocked_missing_signed_synthesis_setting"
    assert "signed prospective A-P1 collection roster" in result["release_requirement"]
