from __future__ import annotations

from copy import deepcopy

import pytest

from tools.a_p1 import summarize_records


def record(
    patient_key,
    response_category,
    gzma,
    prf1,
    *,
    specimen_key=None,
    index_episode_id="episode-1",
    expression_episode_id=None,
    outcome_episode_id=None,
    is_index_specimen=True,
):
    return {
        "study_id": "invented-study-a",
        "cancer": "invented-cancer-a",
        "patient_key": patient_key,
        "specimen_key": specimen_key or f"invented-{patient_key}-specimen",
        "index_episode_id": index_episode_id,
        "is_index_specimen": is_index_specimen,
        "expression_episode_id": expression_episode_id or index_episode_id,
        "outcome_episode_id": outcome_episode_id or index_episode_id,
        "response_category": response_category,
        "source_criteria": "invented-source-criteria-v1",
        "evaluation_window": "invented-window-v1",
        "TPM_GZMA": gzma,
        "TPM_PRF1": prf1,
    }


def test_same_index_episode_is_used_and_exclusions_stay_explicit():
    rows = [
        record("invented-01", "CR", 4, 9),
        record("invented-02", "SD", 4, 4),
        record("invented-03", "PD", 1, 4),
        record(
            "invented-04", "PR", 4, 9,
            expression_episode_id="episode-0",
        ),
        record("invented-05", "NE", 4, 9),
        record("invented-06", "PR", None, 9),
        record("invented-07", "R", 4, 9),
    ]
    rows.extend([
        record(
            "invented-01", "PD", 100, 100,
            specimen_key="invented-01-non-index",
            index_episode_id="episode-1",
            expression_episode_id="episode-0",
            is_index_specimen=False,
        ),
    ])

    result = summarize_records(rows)
    study = result["studies"]["invented-study-a"]

    assert study["patient_n"] == 7
    assert study["eligible_n"] == 3
    assert study["category_counts"] == {"O": 1, "SD": 1, "PD": 1}
    assert study["exclusions"] == {
        "INDEX_EPISODE_MISMATCH": 1,
        "UNKNOWN_OR_NE_CATEGORY": 2,
        "MISSING_CYT_GENE": 1,
    }
    assert study["non_index_specimen_rows"] == 1
    assert study["source_criteria"] == "invented-source-criteria-v1"
    assert study["evaluation_window"] == "invented-window-v1"
    assert study["score_formula"] == "sqrt(TPM_GZMA * TPM_PRF1)"
    assert study["score_mapping_version"] == "CYT_SQRT_TPM_GZMA_TIMES_PRF1_V1"


def test_duplicate_index_specimens_are_excluded_instead_of_choosing_one():
    rows = [
        record("invented-01", "CR", 4, 9),
        record(
            "invented-01", "PR", 100, 100,
            specimen_key="invented-01-second-index",
        ),
    ]

    result = summarize_records(rows)

    assert result["studies"]["invented-study-a"]["eligible_n"] == 0
    assert result["studies"]["invented-study-a"]["exclusions"] == {
        "INDEX_SPECIMEN_NOT_UNIQUE": 1
    }


def test_duplicate_specimen_rows_are_explicitly_excluded():
    row = record("invented-01", "CR", 4, 9)
    duplicate = dict(row, is_index_specimen=False)

    result = summarize_records([row, duplicate])

    assert result["studies"]["invented-study-a"]["eligible_n"] == 0
    assert result["studies"]["invented-study-a"]["exclusions"] == {
        "DUPLICATE_SPECIMEN_ROW": 1
    }


def test_cross_patient_specimen_reuse_with_same_episode_is_rejected():
    rows = [
        record("invented-01", "CR", 4, 9, specimen_key="invented-shared-specimen"),
        record("invented-02", "SD", 4, 4, specimen_key="invented-shared-specimen"),
    ]

    with pytest.raises(ValueError, match="specimen.*patient/episode binding"):
        summarize_records(rows)


def test_specimen_episode_binding_conflict_is_rejected_before_patient_grouping():
    rows = [
        record("invented-01", "CR", 4, 9, specimen_key="invented-shared-specimen"),
        record(
            "invented-01", "CR", 4, 9,
            specimen_key="invented-shared-specimen",
            index_episode_id="episode-2",
            expression_episode_id="episode-2",
            outcome_episode_id="episode-2",
            is_index_specimen=False,
        ),
    ]

    with pytest.raises(ValueError, match="specimen.*patient/episode binding"):
        summarize_records(rows)


def test_permutation_and_category_relabelling_keep_score_identity_separate():
    rows = [
        record("invented-01", "CR", 1, 1),
        record("invented-02", "PR", 4, 4),
        record("invented-03", "SD", 9, 9),
        record("invented-04", "SD", 4, 4),
        record("invented-05", "PD", 1, 4),
        record("invented-06", "PD", 1, 1),
    ]

    first = summarize_records(rows)["studies"]["invented-study-a"]
    permuted = summarize_records(list(reversed(rows)))["studies"]["invented-study-a"]
    relabelled_rows = deepcopy(rows)
    relabelled_rows[0]["response_category"] = "SD"
    relabelled = summarize_records(relabelled_rows)["studies"]["invented-study-a"]

    assert first["score_hash_sha256"] == permuted["score_hash_sha256"]
    assert first["delta"] == permuted["delta"]
    assert relabelled["score_hash_sha256"] == first["score_hash_sha256"]
    assert relabelled["category_counts"] != first["category_counts"]


def test_no_sd_and_absent_o_or_pd_statuses_are_not_silently_promoted():
    no_sd = summarize_records([
        record("invented-01", "CR", 4, 4),
        record("invented-02", "PD", 1, 1),
    ])["studies"]["invented-study-a"]
    no_o = summarize_records([
        record("invented-01", "SD", 4, 4),
        record("invented-02", "PD", 1, 1),
    ])["studies"]["invented-study-a"]

    assert no_sd["status"] == "structurally_zero_no_sd"
    assert no_sd["informative"] is False
    assert no_sd["delta"] == 0.0
    assert no_o["status"] == "nonestimable_missing_o_or_pd"
    assert no_o["delta"] is None
