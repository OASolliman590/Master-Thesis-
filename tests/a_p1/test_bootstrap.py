from __future__ import annotations

import csv
import math
from collections import Counter

import pytest

from tools.a_p1 import analyze_records, create_synthetic_manifest
from tools.a_meta.random_streams import derive_task_seed


MEASUREMENT = {
    "representation_id": "invented-qualified-tpm-v1",
    "unit": "TPM",
    "transform": "unlogged_abundance",
    "gene_mapping": "unique",
    "qualification_status": "qualified",
}


def rows():
    values = [
        ("invented-01", "CR", 9, 9),
        ("invented-02", "PR", 4, 4),
        ("invented-03", "OOPS", 9, 9),
        ("invented-04", "SD", 4, 4),
        ("invented-05", "SD", 1, 1),
        ("invented-06", "SD", 9, 9),
        ("invented-07", "PD", 1, 1),
        ("invented-08", "PD", 4, 4),
        ("invented-09", "PD", 1, 4),
    ]
    return [
        {
            "study_id": "invented-study-a",
            "cancer": "invented-cancer-a",
            "patient_key": patient,
            "specimen_key": f"{patient}-specimen",
            "index_episode_id": "episode-1",
            "is_index_specimen": True,
            "expression_episode_id": "episode-1",
            "outcome_episode_id": "episode-1",
            "response_category": response,
            "source_criteria": "invented-criteria-v1",
            "evaluation_window": "invented-window-v1",
            "TPM_GZMA": gzma,
            "TPM_PRF1": prf1,
        }
        for patient, response, gzma, prf1 in values
    ]


def tsv_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def type7_quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def manual_auc(scores, categories, positive, negative):
    cases = [score for score, category in zip(scores, categories) if category in positive]
    controls = [score for score, category in zip(scores, categories) if category in negative]
    return sum(
        1.0 if case > control else 0.5 if case == control else 0.0
        for case in cases for control in controls
    ) / (len(cases) * len(controls))


@pytest.mark.requires_r
def test_real_r_bootstrap_is_paired_stratified_seeded_and_second_check_only(tmp_path):
    input_rows = rows()
    first = analyze_records(
        input_rows,
        create_synthetic_manifest(input_rows, MEASUREMENT),
        tmp_path / "first",
    )
    reordered = list(reversed(input_rows))
    second = analyze_records(
        reordered,
        create_synthetic_manifest(reordered, MEASUREMENT),
        tmp_path / "second",
    )

    study = first["studies"]["invented-study-a"]
    bootstrap = study["bootstrap"]
    assert bootstrap["repetitions"] == 2000
    assert bootstrap["stream"] == "a_p1_bootstrap"
    assert bootstrap["seed"] == 20261108
    assert bootstrap["second_check_seed"] == derive_task_seed("second_check", "a_p1_bootstrap")
    assert bootstrap["selected_interval_stream"] == "a_p1_bootstrap"
    assert bootstrap["second_check_replaces_main"] is False
    assert bootstrap["second_check_decision"] == "reported_only"
    assert len(bootstrap["assignment_receipt_sha256"]) == 64
    assert len(bootstrap["assignment_file_sha256"]) == 64
    assert bootstrap["assignment_artifact_sha256"] == first["r_provenance"]["output_sha256"][
        "bootstrap_assignments.tsv"
    ]
    assert first["studies"]["invented-study-a"]["bootstrap"]["assignment_receipt_sha256"] == (
        second["studies"]["invented-study-a"]["bootstrap"]["assignment_receipt_sha256"]
    )
    assert first["r_provenance"]["r_version"] == "4.6.1"
    assert first["r_provenance"]["bioconductor_version"] == "3.23"

    output = tmp_path / "first" / "r"
    assignments = tsv_rows(output / "bootstrap_assignments.tsv")
    assert len(assignments) == 2 * 2000 * 8
    assert {row["study"] for row in assignments} == {"invented-study-a"}
    assert {row["stream"] for row in assignments} == {"a_p1_bootstrap", "second_check"}
    assignment_counts = Counter(
        (int(row["replicate"]), row["stream"], row["stratum"]) for row in assignments
    )
    assert len(assignment_counts) == 2000 * 2 * 3
    sorted_categories = ["O", "O", "SD", "SD", "SD", "PD", "PD", "PD"]
    assert all(
        sorted_categories[int(row["row_index"]) - 1] == row["stratum"]
        for row in assignments
    )
    for replicate in range(1, 2001):
        for stream_name in ("a_p1_bootstrap", "second_check"):
            assert {
                category: assignment_counts[(replicate, stream_name, category)]
                for category in ("O", "SD", "PD")
            } == {"O": 2, "SD": 3, "PD": 3}

    replicates = tsv_rows(output / "bootstrap_replicates.tsv")
    assert len(replicates) == 2 * 2000
    for row in replicates:
        assert float(row["auc_dcr"]) - float(row["auc_orr"]) == pytest.approx(
            float(row["delta"]), abs=1e-12
        )
    accepted = sorted(
        (row for row in rows() if row["response_category"] in {"CR", "PR", "SD", "PD"}),
        key=lambda row: row["patient_key"],
    )
    score_by_row = [math.sqrt(row["TPM_GZMA"] * row["TPM_PRF1"]) for row in accepted]
    category_by_row = [
        "O" if row["response_category"] in {"CR", "PR"} else row["response_category"]
        for row in accepted
    ]
    replicate_lookup = {
        (row["stream"], int(row["replicate"])): row for row in replicates
    }
    assignment_lookup = {}
    for row in assignments:
        assignment_lookup.setdefault((row["stream"], int(row["replicate"])), []).append(
            int(row["row_index"]) - 1
        )
    for stream_name in ("a_p1_bootstrap", "second_check"):
        for replicate in range(1, 6):
            selected = assignment_lookup[(stream_name, replicate)]
            scores = [score_by_row[index] for index in selected]
            categories = [category_by_row[index] for index in selected]
            observed = replicate_lookup[(stream_name, replicate)]
            assert float(observed["auc_orr"]) == pytest.approx(
                manual_auc(scores, categories, {"O"}, {"SD", "PD"})
            )
            assert float(observed["auc_dcr"]) == pytest.approx(
                manual_auc(scores, categories, {"O", "SD"}, {"PD"})
            )
    intervals = tsv_rows(output / "intervals.tsv")
    assert len(intervals) == 6
    main = next(
        row for row in intervals
        if row["stream"] == "a_p1_bootstrap" and row["metric"] == "delta"
    )
    check = next(
        row for row in intervals
        if row["stream"] == "second_check" and row["metric"] == "delta"
    )
    assert main["role"] == "primary"
    assert check["role"] == "reported_only"
    assert study["bootstrap"]["main_interval"]["delta"] == [
        float(main["lower"]), float(main["upper"])
    ]
    lower_difference = abs(float(main["lower"]) - float(check["lower"]))
    upper_difference = abs(float(main["upper"]) - float(check["upper"]))
    assert study["bootstrap"]["second_check_delta_lower_difference"] == pytest.approx(
        lower_difference
    )
    assert study["bootstrap"]["second_check_delta_upper_difference"] == pytest.approx(
        upper_difference
    )
    assert study["bootstrap"]["second_check_flag_over_0_01"] is (
        lower_difference > 0.01 or upper_difference > 0.01
    )
    assert study["bootstrap"]["selected_interval_stream"] == "a_p1_bootstrap"
    assert study["bootstrap"]["second_check_replaces_main"] is False
    assert "invented-01" not in (tmp_path / "first" / "summary.json").read_text(encoding="utf-8")


@pytest.mark.requires_r
def test_multi_study_bootstrap_uses_one_seeded_task_and_declared_weights(tmp_path):
    input_rows = rows()
    second_study = [
        {
            **row,
            "study_id": "invented-study-b",
            "cancer": "invented-cancer-b",
            "patient_key": f"second-{row['patient_key']}",
            "specimen_key": f"second-{row['specimen_key']}",
        }
        for row in rows()
    ]
    combined = input_rows + second_study
    weights = {
        "collection_id": "invented-joint-bootstrap-collection",
        "decision_status": "INVENTED_FIXTURE",
        "studies": [
            {"study_id": "invented-study-a", "cancer": "invented-cancer-a",
             "cancer_weight": 0.6, "study_weight": 1.0},
            {"study_id": "invented-study-b", "cancer": "invented-cancer-b",
             "cancer_weight": 0.4, "study_weight": 1.0},
        ],
    }

    result = analyze_records(
        combined,
        create_synthetic_manifest(combined, MEASUREMENT),
        tmp_path / "multi-study",
        synthesis_contract=weights,
    )

    assert result["r_provenance"]["r_version"] == "4.6.1"
    assert result["r_provenance"]["bioconductor_version"] == "3.23"
    assert result["synthesis"]["status"] == "estimated_synthetic_fixture"
    assert result["synthesis"]["interval_status"] == "estimated_conditional_on_original_category_counts"
    assert result["synthesis"]["cross_study_pooled_auc"] is None
    assert result["synthesis"]["interval"]["delta"]
    assert result["synthesis"]["bootstrap"]["seed"] == 20261108
    assert result["synthesis"]["bootstrap"]["second_check_replaces_main"] is False
    joint_receipts = {}
    for study in ("invented-study-a", "invented-study-b"):
        bootstrap = result["studies"][study]["bootstrap"]
        assert bootstrap["status"] == "estimated"
        assert bootstrap["seed"] == 20261108
        assert bootstrap["conditioning"] == "conditional_on_original_study_category_counts_O_SD_PD"
        joint_receipts[study] = bootstrap["assignment_receipt_sha256"]
    assert len(set(joint_receipts.values())) == 1
    assignments = tsv_rows(tmp_path / "multi-study" / "r" / "bootstrap_assignments.tsv")
    assert {row["study"] for row in assignments} == {"invented-study-a", "invented-study-b"}
    assert {row["stratum"] for row in assignments} == {"O", "SD", "PD"}
    assert {row["stream"] for row in assignments} == {"a_p1_bootstrap", "second_check"}
    assignment_counts = Counter(
        (int(row["replicate"]), row["stream"], row["study"], row["stratum"])
        for row in assignments
    )
    for replicate in range(1, 2001):
        for stream_name in ("a_p1_bootstrap", "second_check"):
            for study_id in ("invented-study-a", "invented-study-b"):
                assert {
                    stratum: assignment_counts[(replicate, stream_name, study_id, stratum)]
                    for stratum in ("O", "SD", "PD")
                } == {
                    "O": 2, "SD": 3, "PD": 3
                }
    replicates = tsv_rows(tmp_path / "multi-study" / "r" / "bootstrap_replicates.tsv")
    replicate_lookup = {
        (row["scope"], row["score_method"], row["study_id"], row["stream"], int(row["replicate"])): row
        for row in replicates
    }
    collection_replicates = [
        replicate_lookup[("collection", "CYT", "invented-joint-bootstrap-collection",
                          "a_p1_bootstrap", replicate)]
        for replicate in range(1, 2001)
    ]
    for replicate, collection_row in enumerate(collection_replicates, start=1):
        for metric in ("auc_orr", "auc_dcr", "delta"):
            expected = (
                0.6 * float(replicate_lookup[("study", "CYT", "invented-study-a",
                                               "a_p1_bootstrap", replicate)][metric])
                + 0.4 * float(replicate_lookup[("study", "CYT", "invented-study-b",
                                                "a_p1_bootstrap", replicate)][metric])
            )
            assert float(collection_row[metric]) == pytest.approx(expected, abs=1e-12)
    delta_values = [float(row["delta"]) for row in collection_replicates]
    collection_interval = result["synthesis"]["interval"]["delta"]
    assert collection_interval == pytest.approx([
        type7_quantile(delta_values, 0.025), type7_quantile(delta_values, 0.975)
    ])
    assert "invented-patient" not in (tmp_path / "multi-study" / "summary.json").read_text(
        encoding="utf-8"
    )


@pytest.mark.requires_r
def test_missing_endpoint_classes_remain_nonestimable_and_no_sd_is_zero_sensitivity(tmp_path):
    fixtures = {
        "invented-missing-o": [("SD", 4.0), ("SD", 1.0), ("PD", 1.0), ("PD", 4.0)],
        "invented-missing-pd": [("CR", 9.0), ("PR", 4.0), ("SD", 4.0), ("SD", 1.0)],
        "invented-no-sd": [("CR", 9.0), ("PR", 4.0), ("PD", 1.0), ("PD", 4.0)],
    }
    input_rows = []
    for study, values in fixtures.items():
        for index, (category, abundance) in enumerate(values, start=1):
            input_rows.append({
                "study_id": study,
                "cancer": f"invented-{study}",
                "patient_key": f"invented-{study}-patient-{index:02d}",
                "specimen_key": f"invented-{study}-specimen-{index:02d}",
                "index_episode_id": "invented-index-episode",
                "is_index_specimen": True,
                "expression_episode_id": "invented-index-episode",
                "outcome_episode_id": "invented-index-episode",
                "response_category": category,
                "source_criteria": "invented-criteria-v1",
                "evaluation_window": "invented-window-v1",
                "TPM_GZMA": abundance,
                "TPM_PRF1": abundance,
            })

    result = analyze_records(
        input_rows,
        create_synthetic_manifest(input_rows, MEASUREMENT),
        tmp_path / "nonestimable-sets",
    )

    missing_o = result["studies"]["invented-missing-o"]
    missing_pd = result["studies"]["invented-missing-pd"]
    no_sd = result["studies"]["invented-no-sd"]
    assert missing_o["status"] == "nonestimable_missing_o_or_pd"
    assert missing_o["delta"] is None
    assert missing_o["bootstrap"]["status"] == "not_run_nonestimable_missing_o_or_pd"
    assert missing_pd["status"] == "nonestimable_missing_o_or_pd"
    assert missing_pd["delta"] is None
    assert missing_pd["bootstrap"]["status"] == "not_run_nonestimable_missing_o_or_pd"
    assert no_sd["status"] == "structurally_zero_no_sd"
    assert no_sd["informative"] is False
    assert no_sd["bootstrap"]["status"] == "structural_zero_sensitivity"
    assert no_sd["bootstrap"]["main_interval"]["delta"] == [0.0, 0.0]
    assert result["r_provenance"]["r_version"] == "4.6.1"
