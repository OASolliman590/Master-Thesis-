from __future__ import annotations

import csv
from collections import Counter
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tools.a_scoring.core import DEFAULT_PANELS, panel_definitions


ROOT = Path(__file__).resolve().parents[2]
FEATURES = (
    "P_ANTIGEN_PRESENTATION",
    "M2_CYTOTOXICITY",
    "M3_VIRAL_MIMICRY",
    "M4_EXCLUSION",
)


def _invented_inputs(
    root: Path, *, role="development", studies=3, include_adaptive=False,
    prefix="invented", small_studies=(), group_first_two=False,
    cyt_discordant=False, robust_features=False,
):
    rows = []
    cohorts = {}
    identity_records = []
    for family_index in range(studies + int(include_adaptive)):
        cohort = f"{prefix}_study_{family_index + 1}"
        adaptive_only = family_index >= studies
        family = 1 if group_first_two and family_index < 2 else family_index + 1
        cohorts[cohort] = {
            "study_family": f"{prefix}_family_{family}",
            "cancer": f"{prefix}_cancer_1" if family_index < 2 else f"{prefix}_cancer_{family_index}",
            "representation": "upper_quartile_log2" if adaptive_only else "TPM_log2p1",
            "feature_transform": "deposited log2 upper-quartile" if adaptive_only else "log2(TPM + 1)",
            "primary_eligible": not adaptive_only,
            "adaptive_eligible": True,
            "cyt_available": not adaptive_only,
        }
        for class_name, direction in (("NR", -1.0), ("R", 1.0)):
            class_size = 8 if family_index in small_studies else 12
            for within_class in range(class_size):
                wiggle = (within_class - 5.5) * 0.08
                offset = family_index * 0.11
                if robust_features:
                    varied_a = ((within_class * 5) % 13 - 6) * 0.035
                    varied_b = ((within_class * 7) % 17 - 8) * 0.025
                    varied_c = ((within_class * 3) % 11 - 5) * 0.03
                    feature_values = (
                        direction * 0.10 + wiggle + offset,
                        direction * 0.07 + varied_a + offset * 0.2,
                        -direction * 0.06 + varied_b - offset * 0.1,
                        direction * 0.04 + varied_c + offset * 0.05,
                    )
                else:
                    feature_values = (
                        direction * 0.14 + wiggle + offset,
                        direction * 0.10 - wiggle * 0.7 + offset * 0.2,
                        -direction * 0.08 + wiggle * 0.3 - offset * 0.1,
                        direction * 0.12 + wiggle * 0.5 + offset * 0.05,
                    )
                cyt_direction = -direction if cyt_discordant or family_index == 3 else direction
                gzma_tpm = 12.0 + cyt_direction * 1.5 + within_class * 0.07
                prf1_tpm = 15.0 + cyt_direction * 1.1 + within_class * 0.05
                rows.append(
                    {
                        "cohort": cohort,
                        "patient_id": f"{prefix}_patient_{family_index}_{class_name}_{within_class}",
                        "orr_class": class_name,
                        **dict(zip(FEATURES, feature_values)),
                        "CYT": "" if adaptive_only else str(math.sqrt(gzma_tpm * prf1_tpm)),
                    }
                )
                identity_records.append({
                    "cohort": cohort,
                    "patient_id": rows[-1]["patient_id"],
                    "canonical_patient_uid": f"{prefix}_unique_person_{family_index}_{class_name}_{within_class}",
                    "publication_family_id": cohorts[cohort]["study_family"],
                    "resolution_status": "SYNTHETIC_FIXTURE_UNIQUE",
                })

    root.mkdir(parents=True, exist_ok=True)
    payload = root / "invented_features.tsv"
    columns = ["cohort", "patient_id", "orr_class", *FEATURES, "CYT"]
    with payload.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    identity_path = root / "invented_identity_bindings.json"
    identity_value = {
        "schema": "a_p2_identity_bindings_v1",
        "data_classification": "SYNTHETIC_ONLY",
        "provenance": {
            "kind": "generated_fixture",
            "fixture_id": "a_p2_synthetic_software_test",
            "valid_as_real_identity_evidence": False,
        },
        "records": identity_records,
    }
    identity_path.write_text(
        json.dumps(identity_value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema": "a_p2_input_manifest_v1",
        "data_classification": "SYNTHETIC_ONLY",
        "feature_definition": "arithmetic mean over every member of each frozen panel after the cohort-declared source transform",
        "feature_membership_sha256": {
            feature: hashlib.sha256(("\n".join(panel_definitions(DEFAULT_PANELS)[feature]) + "\n").encode("utf-8")).hexdigest()
            for feature in FEATURES
        },
        "cyt_definition": "sqrt(TPM_GZMA * TPM_PRF1)",
        "role": role,
        "input_table": payload.name,
        "input_sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
        "identity_provenance": {
            "schema": "a_p2_identity_provenance_v1",
            "kind": "generated_fixture",
            "fixture_id": "a_p2_synthetic_software_test",
            "sidecar": identity_path.name,
            "sidecar_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
            "valid_as_real_identity_evidence": False,
        },
        "cohorts": cohorts,
        "provenance": {
            "kind": "generated_fixture",
            "fixture_id": "a_p2_synthetic_software_test",
            "authorization": "synthetic-test-authorization",
            "signatures_present": False,
            "valid_as_real_approval": False,
        },
    }
    manifest_path = root / "input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return manifest_path, payload, rows


def _run(*arguments, env=None):
    task_env = os.environ.copy()
    task_env.pop("THESIS_RUNTIME", None)
    if env:
        task_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "tools.a_p2", *map(str, arguments)],
        cwd=ROOT,
        env=task_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _equation_file(path: Path, *, tampered=False, training_family=None):
    value = {
        "schema": "a_p2_equation_v1",
        "status": "AVAILABLE_SYNTHETIC_SOFTWARE_ONLY",
        "data_classification": "SYNTHETIC_ONLY",
    }
    if training_family:
        value["primary_training_cohort_families"] = [training_family]
    value["equation_sha256"] = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if tampered:
        value["status"] = "tampered_after_hash"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _pairwise_auc(labels, scores):
    responders = [score for label, score in zip(labels, scores) if label == "R"]
    nonresponders = [score for label, score in zip(labels, scores) if label == "NR"]
    if not responders or not nonresponders:
        return math.nan
    wins = sum(
        1.0 if responder > nonresponder else 0.5 if responder == nonresponder else 0.0
        for responder in responders
        for nonresponder in nonresponders
    )
    return wins / (len(responders) * len(nonresponders))


def _type7(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


@pytest.mark.requires_r
def test_synthetic_freeze_writes_the_signed_ridge_equation(tmp_path):
    manifest, _, training_rows = _invented_inputs(
        tmp_path / "development", include_adaptive=True,
    )
    output = tmp_path / "frozen"

    result = _run(
        "freeze", "--manifest", manifest, "--out", output,
        env={"THESIS_RUNTIME": str(tmp_path / "must_not_be_loaded")},
    )

    assert result.returncode == 0, result.stderr
    input_manifest = json.loads(Path(manifest).read_text(encoding="utf-8"))
    equation = json.loads((output / "equation.json").read_text(encoding="utf-8"))
    assert equation["status"] == "AVAILABLE_SYNTHETIC_SOFTWARE_ONLY"
    assert equation["model"]["family"] == "binomial"
    assert equation["model"]["alpha"] == 0
    assert equation["model"]["lambda"] == pytest.approx(0.1)
    assert equation["model"]["standardize"] is False
    assert equation["model"]["intercept"] is True
    assert equation["model"]["solver"] == "glmnet 5.2"
    assert equation["model"]["responder_label"] == "R"
    assert equation["primary"]["training_counts"] == {"R": 36, "NR": 36}
    assert equation["primary"]["training_family_count"] == 3
    assert equation["cohort_adaptive"]["available"] is True
    assert equation["cohort_adaptive"]["training_family_count"] == 4
    assert equation["cohort_adaptive"]["kkt_max_residual"] <= 1e-6
    assert set(equation["training_feature_transforms"]["primary"]) == {
        "invented_study_1", "invented_study_2", "invented_study_3"
    }
    assert set(equation["code_provenance"]) == {
        "python_product", "python_cli", "r_entrypoint", "r_random_streams",
        "r_bridge", "panel_registry", "renv_lock", "numerical_freeze_register",
        "validation_contract", "measurement_decision",
    }
    assert equation["training_identity_provenance_sha256"] == json.loads(
        Path(manifest).read_text(encoding="utf-8")
    )["identity_provenance"]["sidecar_sha256"]
    assert set(equation["training_feature_transforms"]["cohort_adaptive"]) == {
        "invented_study_1", "invented_study_2", "invented_study_3", "invented_study_4"
    }
    assert {
        record["feature_transform"]
        for record in equation["training_feature_transforms"]["cohort_adaptive"].values()
    } == {"log2(TPM + 1)", "deposited log2 upper-quartile"}
    assert equation["primary"]["kkt_max_residual"] <= 1e-6
    assert equation["primary"]["jerr"] == 0
    assert set(equation["primary"]["features"]) == set(FEATURES)
    assert [len(equation["feature_definitions"][feature]["genes"]) for feature in FEATURES] == [8, 12, 13, 13]
    for feature in FEATURES:
        primary_rows = [row for row in training_rows if row["cohort"] != "invented_study_4"]
        values = [row[feature] for row in primary_rows]
        mean = sum(values) / len(values)
        sample_sd = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
        definition = equation["feature_definitions"][feature]
        assert len(definition["genes"]) in (8, 12, 13)
        assert len(definition["membership_sha256"]) == 64
        assert definition["membership_sha256"] == input_manifest["feature_membership_sha256"][feature]
        assert definition["transform"] == "arithmetic mean over the complete frozen membership after the cohort-declared source transform"
        assert equation["primary"]["scaling"][feature]["mean"] == pytest.approx(mean, abs=1e-12)
        assert equation["primary"]["scaling"][feature]["sd"] == pytest.approx(sample_sd, abs=1e-12)
        assert len(equation["primary"]["coefficient_sha256"]) == 64
        assert len(equation["primary"]["scaling_sha256"]) == 64
    assert len(equation["equation_sha256"]) == 64


@pytest.mark.requires_r
def test_synthetic_final_evaluation_scores_the_portable_equation_and_writes_paired_receipts(tmp_path):
    development_manifest, _, _ = _invented_inputs(tmp_path / "development")
    frozen = tmp_path / "frozen"
    freeze = _run("freeze", "--manifest", development_manifest, "--out", frozen)
    assert freeze.returncode == 0, freeze.stderr

    final_manifest, _, rows = _invented_inputs(
        tmp_path / "final", role="final_test", studies=1,
        prefix="invented_external", cyt_discordant=True,
    )
    output = tmp_path / "final_output"
    result = _run(
        "final-evaluate", "--manifest", final_manifest,
        "--equation", frozen / "equation.json", "--out", output,
    )

    assert result.returncode == 0, result.stderr
    equation = json.loads((frozen / "equation.json").read_text(encoding="utf-8"))
    expected_rows = sorted(rows, key=lambda row: (row["cohort"], row["patient_id"]))
    with (output / "predictions.tsv").open(newline="", encoding="utf-8") as stream:
        predictions = list(csv.DictReader(stream, delimiter="\t"))
    primary_predictions = [row for row in predictions if row["analysis"] == "PRIMARY_TPM"]
    adaptive_predictions = [row for row in predictions if row["analysis"] == "COHORT_ADAPTIVE_SENSITIVITY"]
    assert len(primary_predictions) == 24
    assert len(adaptive_predictions) == 24
    for expected, observed in zip(expected_rows, primary_predictions):
        xz = [
            (expected[feature] - equation["primary"]["scaling"][feature]["mean"])
            / equation["primary"]["scaling"][feature]["sd"]
            for feature in FEATURES
        ]
        eta = equation["primary"]["intercept"] + sum(
            equation["primary"]["coefficients"][feature] * value
            for feature, value in zip(FEATURES, xz)
        )
        direct = 1 / (1 + math.exp(-eta))
        assert float(observed["learner_score"]) == pytest.approx(direct, abs=1e-12)
        assert float(observed["cyt_score"]) == pytest.approx(float(expected["CYT"]))

    with (output / "final_metrics.tsv").open(newline="", encoding="utf-8") as stream:
        metrics = list(csv.DictReader(stream, delimiter="\t"))
    primary = next(row for row in metrics if row["analysis"] == "PRIMARY_TPM")
    assert primary["status"] == "AVAILABLE"
    assert primary["responders"] == "12"
    assert primary["nonresponders"] == "12"
    assert primary["comparator_membership_caveat"] == (
        "M2 includes GZMA and PRF1 and therefore partly overlaps the CYT comparator."
    )
    with (output / "adaptive_external_scaling.tsv").open(newline="", encoding="utf-8") as stream:
        adaptive_scaling = list(csv.DictReader(stream, delimiter="\t"))
    assert len(adaptive_scaling) == len(FEATURES)
    assert {row["scope"] for row in adaptive_scaling} == {"EXTERNAL_COHORT_OUTCOME_BLINDED"}
    assert {row["status"] for row in adaptive_scaling} == {"AVAILABLE"}
    for feature in FEATURES:
        values = [float(row[feature]) for row in expected_rows]
        mean = sum(values) / len(values)
        sample_sd = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
        scaling_row = next(row for row in adaptive_scaling if row["feature"] == feature)
        assert float(scaling_row["mean"]) == pytest.approx(mean, abs=1e-12)
        assert float(scaling_row["sd"]) == pytest.approx(sample_sd, abs=1e-12)
    with (output / "bootstrap.tsv").open(newline="", encoding="utf-8") as stream:
        bootstrap_rows = list(csv.DictReader(stream, delimiter="\t"))
    assert len(bootstrap_rows) == 2000
    assert all(
        float(row["delta_auc"]) == pytest.approx(float(row["learner_auc"]) - float(row["cyt_auc"]))
        for row in bootstrap_rows
    )
    bootstrap_receipt = json.loads((output / "bootstrap_receipt.json").read_text(encoding="utf-8"))
    second_receipt = json.loads((output / "second_check_receipt.json").read_text(encoding="utf-8"))
    assert bootstrap_receipt["stream"] == "a_p2_bootstrap"
    assert bootstrap_receipt["seed"] == 20261102
    assert len(bootstrap_receipt["receipt_sha256"]) == 64
    assert second_receipt["stream"] == "second_check"
    assert second_receipt["reported_only"] is True
    with (output / "second_check.tsv").open(newline="", encoding="utf-8") as stream:
        second_check = next(csv.DictReader(stream, delimiter="\t"))
    assert second_check["replaces_main_result"] == "FALSE"
    assert second_check["discrepancy_threshold"] == "0.01"
    expected_flag = (
        float(second_check["lower_endpoint_difference"]) > 0.01
        or float(second_check["upper_endpoint_difference"]) > 0.01
    )
    assert (second_check["discrepancy_flag"] == "TRUE") is expected_flag
    assert second_check["replaces_main_result"] == "FALSE"
    assert second_check["comparator_membership_caveat"] == primary["comparator_membership_caveat"]
    with (output / "bootstrap_assignments.tsv").open(newline="", encoding="utf-8") as stream:
        assignments = list(csv.DictReader(stream, delimiter="\t"))
    assert len(assignments) == 2_000 * 24
    assert bootstrap_receipt["assignments_file"] == "bootstrap_assignments.tsv"
    assert second_receipt["assignments_file"] == "second_check_assignments.tsv"
    assert bootstrap_receipt["assignments_sha256"] == hashlib.sha256(
        (output / "bootstrap_assignments.tsv").read_bytes()
    ).hexdigest()
    assert second_receipt["assignments_sha256"] == hashlib.sha256(
        (output / "second_check_assignments.tsv").read_bytes()
    ).hexdigest()
    assert (output / ".work" / "bootstrap_receipt.json").is_file()
    assert (output / ".work" / "second_check_receipt.json").is_file()
    assert set(row["stratum"] for row in assignments) == {"R", "NR"}
    counts = Counter((row["replicate"], row["stratum"]) for row in assignments)
    assert all(counts[(str(replicate), "R")] == 12 for replicate in range(1, 2001))
    assert all(counts[(str(replicate), "NR")] == 12 for replicate in range(1, 2001))

    prediction_by_index = {
        int(row["row_index"]): row
        for row in primary_predictions
    }
    labels_by_index = {
        index: row["orr_class"]
        for index, row in prediction_by_index.items()
    }

    def independently_reconstruct(assignments_path):
        with assignments_path.open(newline="", encoding="utf-8") as stream:
            sampled_rows = list(csv.DictReader(stream, delimiter="\t"))
        grouped = {}
        for sample in sampled_rows:
            grouped.setdefault(int(sample["replicate"]), []).append(sample)
        assert set(grouped) == set(range(1, 2001))
        values = {}
        for replicate, sample_rows in grouped.items():
            assert len(sample_rows) == 24
            assert Counter(sample["stratum"] for sample in sample_rows) == {"R": 12, "NR": 12}
            selected = [int(sample["row_index"]) for sample in sorted(sample_rows, key=lambda item: int(item["draw"]))]
            labels = [labels_by_index[index] for index in selected]
            learner_scores = [float(prediction_by_index[index]["learner_score"]) for index in selected]
            cyt_scores = [float(prediction_by_index[index]["cyt_score"]) for index in selected]
            learner_auc = _pairwise_auc(labels, learner_scores)
            cyt_auc = _pairwise_auc(labels, cyt_scores)
            values[replicate] = (learner_auc, cyt_auc, learner_auc - cyt_auc)
        return sampled_rows, values

    _, reconstructed_main = independently_reconstruct(output / "bootstrap_assignments.tsv")
    main_draws = {index: row for index, row in enumerate(bootstrap_rows, start=1)}
    for replicate, (learner_auc, cyt_auc, delta_auc) in reconstructed_main.items():
        row = main_draws[replicate]
        assert float(row["learner_auc"]) == pytest.approx(learner_auc, abs=1e-12)
        assert float(row["cyt_auc"]) == pytest.approx(cyt_auc, abs=1e-12)
        assert float(row["delta_auc"]) == pytest.approx(delta_auc, abs=1e-12)
    main_interval = (
        _type7([value[2] for value in reconstructed_main.values()], 0.025),
        _type7([value[2] for value in reconstructed_main.values()], 0.975),
    )
    with (output / "bootstrap_summary.tsv").open(newline="", encoding="utf-8") as stream:
        main_summary = next(csv.DictReader(stream, delimiter="\t"))
    assert float(main_summary["lower_95"]) == pytest.approx(main_interval[0], abs=1e-12)
    assert float(main_summary["upper_95"]) == pytest.approx(main_interval[1], abs=1e-12)

    second_samples, reconstructed_check = independently_reconstruct(
        output / "second_check_assignments.tsv"
    )
    assert len(second_samples) == 2_000 * 24
    check_interval = (
        _type7([value[2] for value in reconstructed_check.values()], 0.025),
        _type7([value[2] for value in reconstructed_check.values()], 0.975),
    )
    assert float(second_check["lower_95"]) == pytest.approx(check_interval[0], abs=1e-12)
    assert float(second_check["upper_95"]) == pytest.approx(check_interval[1], abs=1e-12)
    lower_difference = abs(main_interval[0] - check_interval[0])
    upper_difference = abs(main_interval[1] - check_interval[1])
    assert float(second_check["lower_endpoint_difference"]) == pytest.approx(lower_difference, abs=1e-12)
    assert float(second_check["upper_endpoint_difference"]) == pytest.approx(upper_difference, abs=1e-12)
    assert (second_check["discrepancy_flag"] == "TRUE") is (
        lower_difference > 0.01 or upper_difference > 0.01
    )
    assert {row["stream"] for row in [bootstrap_receipt, second_receipt]} == {
        "a_p2_bootstrap", "second_check"
    }

    small_manifest, _, _ = _invented_inputs(
        tmp_path / "small_final", role="final_test", studies=1,
        prefix="invented_small_final", small_studies=(0,),
    )
    small_output = tmp_path / "small_final_output"
    small_result = _run(
        "final-evaluate", "--manifest", small_manifest,
        "--equation", frozen / "equation.json", "--out", small_output,
    )
    assert small_result.returncode == 0, small_result.stderr
    with (small_output / "final_metrics.tsv").open(newline="", encoding="utf-8") as stream:
        small_primary = next(row for row in csv.DictReader(stream, delimiter="\t") if row["analysis"] == "PRIMARY_TPM")
    assert small_primary["status"] == "UNAVAILABLE_FINAL_CLASS_FLOOR_DESCRIPTIVE_ONLY"
    assert small_primary["responders"] == "8"
    assert small_primary["nonresponders"] == "8"
    assert json.loads((small_output / "bootstrap_receipt.json").read_text())["random_draws"] is False

    no_cyt_manifest, _, _ = _invented_inputs(
        tmp_path / "no_cyt_final", role="final_test", studies=0,
        include_adaptive=True, prefix="invented_no_cyt_final",
    )
    no_cyt_output = tmp_path / "no_cyt_final_output"
    no_cyt_result = _run(
        "final-evaluate", "--manifest", no_cyt_manifest,
        "--equation", frozen / "equation.json", "--out", no_cyt_output,
    )
    assert no_cyt_result.returncode == 0, no_cyt_result.stderr
    with (no_cyt_output / "final_metrics.tsv").open(newline="", encoding="utf-8") as stream:
        no_cyt_metrics = list(csv.DictReader(stream, delimiter="\t"))
    adaptive_only = next(row for row in no_cyt_metrics if row["analysis"] == "COHORT_ADAPTIVE_SENSITIVITY_DESCRIPTIVE")
    assert adaptive_only["learner_auc"] != "NA"
    assert adaptive_only["cyt_auc"] == "NA"
    assert adaptive_only["reason"] == "CYT_UNAVAILABLE_BY_MEASUREMENT_CONTRACT"
    with (no_cyt_output / "predictions.tsv").open(newline="", encoding="utf-8") as stream:
        no_cyt_predictions = list(csv.DictReader(stream, delimiter="\t"))
    adaptive_predictions = [row for row in no_cyt_predictions if row["analysis"] == "COHORT_ADAPTIVE_SENSITIVITY"]
    assert len(adaptive_predictions) == 24
    assert all(row["cyt_score"] == "NA" for row in adaptive_predictions)


@pytest.mark.requires_r
def test_development_keeps_families_weights_small_studies_and_sensitivity_outputs_separate(tmp_path):
    manifest, _, _ = _invented_inputs(
        tmp_path / "development", studies=4, include_adaptive=True,
        small_studies=(3,), group_first_two=True,
    )
    output = tmp_path / "development_output"
    result = _run("development", "--manifest", manifest, "--out", output)
    assert result.returncode == 0, result.stderr

    with (output / "family_folds.tsv").open(newline="", encoding="utf-8") as stream:
        folds = list(csv.DictReader(stream, delimiter="\t"))
    grouped = next(
        row for row in folds
        if row["analysis"] == "PRIMARY_TPM" and row["held_out_family"] == "invented_family_1"
    )
    assert set(grouped["held_out_studies"].split(",")) == {
        "invented_study_1", "invented_study_2"
    }
    primary_folds = [row for row in folds if row["analysis"] == "PRIMARY_TPM"]
    assert all(row["status"] == "AVAILABLE" for row in primary_folds)
    assert all(int(row["responders"]) >= 20 and int(row["nonresponders"]) >= 20 for row in primary_folds)

    with (output / "primary_leave_family_out.tsv").open(newline="", encoding="utf-8") as stream:
        primary = list(csv.DictReader(stream, delimiter="\t"))
    assert "invented_study_5" not in {row["study"] for row in primary}
    assert {row["validation_label"] for row in primary} == {"INTERNAL_EXTERNAL"}
    for row in primary:
        if row["cancer"] == "invented_cancer_1":
            assert float(row["equal_study_weight"]) == pytest.approx(0.25)
            assert float(row["equal_cancer_weight"]) == pytest.approx(1 / 6)
        else:
            assert float(row["equal_study_weight"]) == pytest.approx(0.25)
            assert float(row["equal_cancer_weight"]) == pytest.approx(1 / 3)
    assert any(row["transfer_label"] == "JOINT_STUDY_AND_CANCER_TRANSFER" for row in primary)
    assert all(row["comparison_status"] == "AVAILABLE_PAIRED" for row in primary)
    equal_study = sum(float(row["delta_auc"]) for row in primary) / len(primary)
    cancer_means = {
        cancer: sum(float(row["delta_auc"]) for row in primary if row["cancer"] == cancer)
        / sum(row["cancer"] == cancer for row in primary)
        for cancer in {row["cancer"] for row in primary}
    }
    with (output / "primary_aggregates.tsv").open(newline="", encoding="utf-8") as stream:
        aggregate_rows = list(csv.DictReader(stream, delimiter="\t"))
    aggregates = {(row["metric"], row["weighting"]): row for row in aggregate_rows}
    assert aggregates[("delta_auc", "equal_study")]["status"] == "AVAILABLE"
    assert float(aggregates[("delta_auc", "equal_study")]["value"]) == pytest.approx(equal_study)
    assert aggregates[("delta_auc", "equal_cancer")]["status"] == "AVAILABLE"
    assert float(aggregates[("delta_auc", "equal_cancer")]["value"]) == pytest.approx(sum(cancer_means.values()) / len(cancer_means))
    assert float(aggregates[("delta_auc", "equal_study")]["value"]) != pytest.approx(
        float(aggregates[("delta_auc", "equal_cancer")]["value"])
    )
    assert aggregates[("learner_auc", "equal_study")]["status"] == "AVAILABLE"
    assert aggregates[("cyt_auc", "equal_cancer")]["status"] == "AVAILABLE"

    with (output / "cohort_adaptive_aggregates.tsv").open(newline="", encoding="utf-8") as stream:
        adaptive_aggregates = {
            (row["metric"], row["weighting"]): row
            for row in csv.DictReader(stream, delimiter="\t")
        }
    assert adaptive_aggregates[("learner_auc", "equal_cancer")]["status"] == "AVAILABLE"
    assert adaptive_aggregates[("delta_auc", "equal_cancer")]["status"] == "UNAVAILABLE_REQUIRED_STUDY_PAIRED_COMPARISON"

    with (output / "cohort_adaptive_leave_family_out.tsv").open(newline="", encoding="utf-8") as stream:
        adaptive = list(csv.DictReader(stream, delimiter="\t"))
    braun = next(row for row in adaptive if row["study"] == "invented_study_5")
    assert braun["analysis"] == "COHORT_ADAPTIVE_SENSITIVITY"
    assert braun["learner_status"] == "AVAILABLE"
    assert braun["cyt_status"] == "CYT_UNAVAILABLE_BY_MEASUREMENT_CONTRACT"
    assert braun["comparison_status"] == "LEARNER_ONLY_CYT_UNAVAILABLE"

    with (output / "primary_split_assignments.tsv").open(newline="", encoding="utf-8") as stream:
        primary_assignments = list(csv.DictReader(stream, delimiter="\t"))
    small_rows = [row for row in primary_assignments if row["study"] == "invented_study_4"]
    assert len(small_rows) == 20 * 16
    assert {row["partition"] for row in small_rows} == {"train"}
    assert len({row["replicate"] for row in small_rows}) == 20
    split_counts = Counter(
        (row["study"], row["replicate"], row["stratum"], row["partition"])
        for row in primary_assignments
    )
    for study in ("invented_study_1", "invented_study_2", "invented_study_3"):
        for repeat in range(1, 21):
            for stratum in ("R", "NR"):
                assert split_counts[(study, str(repeat), stratum, "train")] == 8
                assert split_counts[(study, str(repeat), stratum, "test")] == 4
    assert json.loads((output / "primary_split_receipt.json").read_text())["stream"] == "a_p2_splits"
    primary_receipt = json.loads((output / "primary_split_receipt.json").read_text())
    assert len(primary_receipt["receipt_sha256"]) == 64
    assert primary_receipt["assignments_file"] == "primary_split_assignments.tsv"
    assert primary_receipt["assignments_sha256"] == hashlib.sha256(
        (output / "primary_split_assignments.tsv").read_bytes()
    ).hexdigest()
    with (output / "primary_split_sensitivity.tsv").open(newline="", encoding="utf-8") as stream:
        split_rows = list(csv.DictReader(stream, delimiter="\t"))
    assert {row["validation_label"] for row in split_rows} == {
        "VALIDATION_SETTING_CONTRAST_NOT_OPTIMISM"
    }
    primary_repeat_aggregates = [row for row in split_rows if row["result_type"] == "repeat_aggregate"]
    assert len(primary_repeat_aggregates) == 40
    assert all(row["learner_status"] == "AVAILABLE" for row in primary_repeat_aggregates)
    assert all(row["cyt_status"] == "AVAILABLE" for row in primary_repeat_aggregates)
    assert all(float(row["delta_auc"]) == pytest.approx(float(row["learner_auc"]) - float(row["cyt_auc"])) for row in primary_repeat_aggregates)
    repeat_summaries = [row for row in split_rows if row["result_type"] == "repeat_summary"]
    assert {(row["metric"], row["weighting"]) for row in repeat_summaries} == {
        (metric, weighting)
        for metric in ("learner_auc", "cyt_auc", "delta_auc")
        for weighting in ("equal_study", "equal_cancer")
    }
    assert all(row["status"] == "AVAILABLE" for row in repeat_summaries)

    with (output / "cohort_adaptive_split_sensitivity.tsv").open(newline="", encoding="utf-8") as stream:
        adaptive_split_rows = list(csv.DictReader(stream, delimiter="\t"))
    assert {row["analysis"] for row in adaptive_split_rows} == {"COHORT_ADAPTIVE_SENSITIVITY"}
    adaptive_repeat_aggregates = [row for row in adaptive_split_rows if row["result_type"] == "repeat_aggregate"]
    braun_aggregates = [row for row in adaptive_repeat_aggregates if row["cyt_status"] != "AVAILABLE"]
    assert braun_aggregates
    assert all(row["learner_status"] == "AVAILABLE" for row in braun_aggregates)
    assert json.loads((output / "cohort_adaptive_split_receipt.json").read_text())["stream"] == "a_p2_splits"


@pytest.mark.requires_r
def test_held_out_labels_cannot_change_training_scaling_or_coefficients(tmp_path):
    from tools.r_bridge import run_r

    manifest_path, payload, _ = _invented_inputs(tmp_path / "original", robust_features=True)
    changed_root = tmp_path / "changed"
    changed_manifest, changed_payload, _ = _invented_inputs(changed_root, robust_features=True)
    with payload.open(newline="", encoding="utf-8") as stream:
        original_rows = list(csv.DictReader(stream, delimiter="\t"))
    changed_rows = []
    for row in original_rows:
        if row["cohort"] == "invented_study_1":
            row["orr_class"] = "NR" if row["orr_class"] == "R" else "R"
        changed_rows.append(row)
    columns = ["cohort", "patient_id", "orr_class", *FEATURES, "CYT"]
    with changed_payload.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(changed_rows)
    changed_value = json.loads(changed_manifest.read_text(encoding="utf-8"))
    changed_value["input_sha256"] = hashlib.sha256(changed_payload.read_bytes()).hexdigest()
    changed_manifest.write_text(json.dumps(changed_value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    def held_fold(name, manifest_path, payload):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        output = tmp_path / name
        work = output / ".work"
        work.mkdir(parents=True)
        result = run_r(
            ROOT / "r/R/a_p2.R", {"features": payload},
            {
                "operation": "test-leakage-family-contract",
                "data_classification": "SYNTHETIC_ONLY",
                "cohorts": manifest["cohorts"],
                "feature_names": list(FEATURES),
                "response_column": "orr_class",
                "input_sha256": manifest["input_sha256"],
                "test_only_family": "invented_family_1",
                "work_dir": str(work),
                "expected_outputs": ["leakage_model.tsv"],
            },
            output / "r_bridge",
        )
        with result.outputs["leakage_model.tsv"].open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream, delimiter="\t"))

    original_model = held_fold("original_output", manifest_path, payload)
    changed_model = held_fold("changed_output", changed_manifest, changed_payload)
    original_primary = [row for row in original_model if row["analysis"] == "PRIMARY_TPM"]
    changed_primary = [row for row in changed_model if row["analysis"] == "PRIMARY_TPM"]
    assert len(original_primary) == len(changed_primary) == 4
    for left, right in zip(original_primary, changed_primary):
        assert (left["feature"], left["mean"], left["sd"], left["coefficient"], left["intercept"]) == (
            right["feature"], right["mean"], right["sd"], right["coefficient"], right["intercept"]
        )
    original_adaptive = [row for row in original_model if row["analysis"] == "COHORT_ADAPTIVE_SENSITIVITY"]
    changed_adaptive = [row for row in changed_model if row["analysis"] == "COHORT_ADAPTIVE_SENSITIVITY"]
    original_training = [row for row in original_adaptive if not row["study_scope"].startswith("HELD_OUT_")]
    changed_training = [row for row in changed_adaptive if not row["study_scope"].startswith("HELD_OUT_")]
    assert len(original_training) == len(changed_training) == 8
    assert [
        (row["study_scope"], row["feature"], row["mean"], row["sd"], row["coefficient"], row["intercept"])
        for row in original_training
    ] == [
        (row["study_scope"], row["feature"], row["mean"], row["sd"], row["coefficient"], row["intercept"])
        for row in changed_training
    ]
    original_external = [row for row in original_adaptive if row["study_scope"].startswith("HELD_OUT_")]
    changed_external = [row for row in changed_adaptive if row["study_scope"].startswith("HELD_OUT_")]
    assert len(original_external) == len(changed_external) == 4
    assert [
        (row["feature"], row["mean"], row["sd"], row["status"])
        for row in original_external
    ] == [
        (row["feature"], row["mean"], row["sd"], row["status"])
        for row in changed_external
    ]


def test_real_final_gate_rejects_unreleased_or_tampered_inputs_before_payload_access(tmp_path):
    manifest_path, payload, _ = _invented_inputs(
        tmp_path / "real_final", role="final_test", studies=1, prefix="synthetic_test_authorization"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["data_classification"] = "PRIVATE_PATIENT_LEVEL"
    manifest["input_table"] = "not_created_until_authorized.tsv"
    manifest["provenance"] = {
        "kind": "source_derived",
        "source_object_sha256": ["a" * 64],
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    fake_release = tmp_path / "invented_user_release.json"
    fake_release.write_text(json.dumps({
        "record_type": "a_p2_user_release_v2",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "record_status": "TEST_ONLY_NOT_A_REAL_DECISION",
        "decision": {"identity": "fixture_only", "path": "docs/decisions/fixture_only.md", "sha256": "0" * 64},
        "real_authorization": False,
    }), encoding="utf-8")
    equation = _equation_file(tmp_path / "equation.json")
    output = tmp_path / "must_not_be_created"

    result = _run(
        "final-evaluate", "--manifest", manifest_path, "--equation", equation,
        "--release-record", fake_release, "--out", output,
    )

    assert result.returncode == 2
    assert "--allow-outcomes" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not output.exists()
    assert payload.is_file()


@pytest.mark.parametrize("operation", ["development", "freeze"])
def test_real_development_and_freeze_require_release_before_payload_access(tmp_path, operation):
    manifest_path, _, _ = _invented_inputs(tmp_path / operation)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["data_classification"] = "PRIVATE_PATIENT_LEVEL"
    manifest["input_table"] = "not_created_until_authorized.tsv"
    manifest["provenance"] = {"kind": "source_derived", "source_object_sha256": ["b" * 64]}
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    output = tmp_path / f"{operation}_blocked"

    result = _run(operation, "--manifest", manifest_path, "--out", output)

    assert result.returncode == 2
    assert "--allow-outcomes" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not output.exists()


def test_synthetic_classification_without_generated_provenance_is_not_a_bypass(tmp_path):
    manifest_path, _, _ = _invented_inputs(tmp_path / "missing_provenance")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_table"] = "not_created.tsv"
    manifest.pop("provenance")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    output = tmp_path / "blocked"

    result = _run("development", "--manifest", manifest_path, "--out", output)

    assert result.returncode == 2
    assert "generated-fixture provenance" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("input_name", ["ingestion_packet.json", "INGESTION_PACKET.JSON"])
def test_ingestion_packet_paths_are_refused_before_payload_access(tmp_path, input_name):
    manifest_path, _, _ = _invented_inputs(tmp_path / input_name.replace(".", "_"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_table"] = input_name
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    output = tmp_path / "blocked"

    result = _run("development", "--manifest", manifest_path, "--out", output)

    assert result.returncode == 2
    assert "never reads ingestion_packet.json" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    ("feature_transform", "representation", "expected_error"),
    [
        ("unknown_transform", "TPM_log2p1", "not in the A-P2 measurement contract"),
        ("deposited log2 upper-quartile", "upper_quartile_log2", "Primary A-P2 cohorts must declare"),
    ],
)
def test_cohort_feature_transform_is_validated_before_payload_access(
    tmp_path, feature_transform, representation, expected_error,
):
    manifest_path, _, _ = _invented_inputs(tmp_path / "invalid_transform")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_table"] = "not_created.tsv"
    cohort = next(iter(manifest["cohorts"]))
    manifest["cohorts"][cohort]["feature_transform"] = feature_transform
    manifest["cohorts"][cohort]["representation"] = representation
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    output = tmp_path / "blocked"

    result = _run("development", "--manifest", manifest_path, "--out", output)

    assert result.returncode == 2
    assert expected_error in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not output.exists()


def test_imvigor210_cannot_be_opened_by_synthetic_fixture_provenance(tmp_path):
    neutral_root = tmp_path.parent.parent / "protected_fixture"
    manifest_path, _, _ = _invented_inputs(
        neutral_root / "inputs", role="final_test", studies=1, prefix="synthetic"
    )
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    cohort = next(iter(value["cohorts"]))
    value["cohorts"]["IMvigor210"] = value["cohorts"].pop(cohort)
    value["input_table"] = "not_created.tsv"
    manifest_path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    equation = _equation_file(neutral_root / "equation.json")

    result = _run("final-evaluate", "--manifest", manifest_path, "--equation", equation, "--out", neutral_root / "blocked")

    assert result.returncode == 2
    assert "IMvigor210" in result.stderr
    assert not (neutral_root / "blocked").exists()


def test_tampered_equation_is_rejected_before_final_payload_access(tmp_path):
    manifest_path, _, _ = _invented_inputs(
        tmp_path / "final", role="final_test", studies=1, prefix="invented_external"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_table"] = "not_created.tsv"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    equation = _equation_file(tmp_path / "equation.json", tampered=True)

    result = _run("final-evaluate", "--manifest", manifest_path, "--equation", equation, "--out", tmp_path / "blocked")

    assert result.returncode == 2
    assert "Frozen equation hash does not match" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not (tmp_path / "blocked").exists()


def test_tampered_final_payload_is_rejected_before_r_evaluation(tmp_path):
    manifest_path, payload, _ = _invented_inputs(
        tmp_path / "tampered_final", role="final_test", studies=1,
        prefix="invented_external",
    )
    payload.write_bytes(payload.read_bytes() + b"tampered\n")
    equation = _equation_file(tmp_path / "equation.json")
    output = tmp_path / "blocked"

    result = _run(
        "final-evaluate", "--manifest", manifest_path, "--equation", equation,
        "--out", output,
    )

    assert result.returncode == 2
    assert "input table hash does not match its manifest" in result.stderr
    assert not output.exists()


def test_final_family_overlap_is_rejected_before_payload_access(tmp_path):
    manifest_path, _, _ = _invented_inputs(
        tmp_path / "final", role="final_test", studies=1, prefix="invented_external"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_table"] = "not_created.tsv"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    equation = _equation_file(
        tmp_path / "equation.json", training_family="invented_external_family_1"
    )

    result = _run("final-evaluate", "--manifest", manifest_path, "--equation", equation, "--out", tmp_path / "blocked")

    assert result.returncode == 2
    assert "overlaps the frozen development equation" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not (tmp_path / "blocked").exists()


def test_final_evaluation_refuses_more_than_one_final_family_before_payload_access(tmp_path):
    manifest_path, _, _ = _invented_inputs(
        tmp_path / "multiple_final_families", role="final_test", studies=2,
        prefix="invented_external",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_table"] = "not_created.tsv"
    cohorts = list(manifest["cohorts"])
    manifest["cohorts"][cohorts[1]]["study_family"] = "second_external_family"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    equation = _equation_file(tmp_path / "equation.json")

    result = _run(
        "final-evaluate", "--manifest", manifest_path, "--equation", equation,
        "--out", tmp_path / "blocked",
    )

    assert result.returncode == 2
    assert "exactly one complete study family" in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not (tmp_path / "blocked").exists()


@pytest.mark.requires_r
def test_constant_and_missing_features_produce_explicit_unavailable_freezes(tmp_path):
    cases = (
        ("constant", "P_ANTIGEN_PRESENTATION", "1.0", "UNAVAILABLE_ZERO_OR_NONFINITE_TRAINING_SD"),
        ("missing", "M4_EXCLUSION", "", "UNAVAILABLE_MISSING_OR_NONFINITE_FEATURE"),
    )
    for name, feature, replacement, expected_status in cases:
        manifest_path, payload, _ = _invented_inputs(tmp_path / name)
        with payload.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        for row in rows:
            if name == "constant":
                row[feature] = replacement
            else:
                row[feature] = replacement
                break
        columns = ["cohort", "patient_id", "orr_class", *FEATURES, "CYT"]
        with payload.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["input_sha256"] = hashlib.sha256(payload.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        output = tmp_path / f"{name}_freeze"

        result = _run("freeze", "--manifest", manifest_path, "--out", output)

        assert result.returncode == 0, result.stderr
        equation = json.loads((output / "equation.json").read_text(encoding="utf-8"))
        assert equation["status"] == expected_status
        with (output / "fit_diagnostics.tsv").open(newline="", encoding="utf-8") as stream:
            diagnostics = list(csv.DictReader(stream, delimiter="\t"))
        assert next(row for row in diagnostics if row["analysis"] == "PRIMARY_TPM")["status"] == expected_status


@pytest.mark.requires_r
def test_training_class_and_family_floors_are_explicitly_unavailable(tmp_path):
    class_manifest, _, _ = _invented_inputs(
        tmp_path / "class_floor", studies=3, small_studies=(0, 1, 2),
    )
    class_output = tmp_path / "class_floor_output"
    class_result = _run("development", "--manifest", class_manifest, "--out", class_output)
    assert class_result.returncode == 0, class_result.stderr
    with (class_output / "family_folds.tsv").open(newline="", encoding="utf-8") as stream:
        class_folds = list(csv.DictReader(stream, delimiter="\t"))
    assert {row["status"] for row in class_folds if row["analysis"] == "PRIMARY_TPM"} == {
        "UNAVAILABLE_TRAINING_CLASS_FLOOR"
    }
    with (class_output / "primary_aggregates.tsv").open(newline="", encoding="utf-8") as stream:
        class_aggregates = list(csv.DictReader(stream, delimiter="\t"))
    assert all(row["status"] == "UNAVAILABLE_REQUIRED_STUDY_LEARNER" for row in class_aggregates if row["metric"] == "learner_auc")

    family_manifest, _, _ = _invented_inputs(
        tmp_path / "family_floor", studies=2,
    )
    family_development_output = tmp_path / "family_floor_development_output"
    family_development_result = _run(
        "development", "--manifest", family_manifest, "--out", family_development_output,
    )
    assert family_development_result.returncode == 0, family_development_result.stderr
    family_receipt = json.loads((family_development_output / "primary_split_receipt.json").read_text())
    assert family_receipt["status"] == "UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES"
    assert family_receipt["random_draws"] is False
    with (family_development_output / "primary_split_sensitivity.tsv").open(newline="", encoding="utf-8") as stream:
        family_splits = list(csv.DictReader(stream, delimiter="\t"))
    assert {row["status"] for row in family_splits} == {"UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES"}

    family_output = tmp_path / "family_floor_output"
    family_result = _run("freeze", "--manifest", family_manifest, "--out", family_output)
    assert family_result.returncode == 0, family_result.stderr
    equation = json.loads((family_output / "equation.json").read_text(encoding="utf-8"))
    assert equation["status"] == "UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES"


def test_cli_advertises_a_default_false_outcome_gate_without_using_it():
    for command in ("development", "freeze", "final-evaluate"):
        result = _run(command, "--help")
        assert result.returncode == 0, result.stderr
        assert "--allow-outcomes" in result.stdout


@pytest.mark.parametrize("operation", ["development", "freeze", "final-evaluate"])
def test_real_outcome_gate_precedes_authorization_equation_and_payload_reads(tmp_path, monkeypatch, operation):
    manifest_path, _, _ = _invented_inputs(
        tmp_path / operation, role="final_test" if operation == "final-evaluate" else "development",
        studies=1 if operation == "final-evaluate" else 3,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["data_classification"] = "PRIVATE_PATIENT_LEVEL"
    manifest["input_table"] = "not_created_until_user_release.tsv"
    manifest["provenance"] = {"kind": "source_derived", "source_object_sha256": ["a" * 64]}
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")

    def must_not_hash(path):
        pytest.fail("the real outcome gate must run before any patient-level file is read")

    monkeypatch.setattr("tools.a_p2.product._sha256_file", must_not_hash)
    if operation == "final-evaluate":
        with pytest.raises(PermissionError, match="--allow-outcomes"):
            from tools.a_p2.product import run_final_evaluation
            run_final_evaluation(
                manifest_path, tmp_path / "equation_that_must_not_be_opened.json",
                tmp_path / "blocked",
            )
    else:
        from tools.a_p2.product import run_development, run_freeze
        runner = run_development if operation == "development" else run_freeze
        with pytest.raises(PermissionError, match="--allow-outcomes"):
            runner(manifest_path, tmp_path / "blocked")


@pytest.mark.parametrize(
    ("identity_field", "identity_value", "reason"),
    [
        ("cohort", "liu2019", "known A-P2 source identity"),
        ("study_family", "alias_to_imvigor210_family", "protected source identity"),
    ],
)
def test_synthetic_provenance_cannot_claim_real_or_protected_identities_before_payload_access(
    tmp_path, identity_field, identity_value, reason,
):
    manifest_path, _, _ = _invented_inputs(tmp_path / "identity_collision")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cohort = next(iter(manifest["cohorts"]))
    manifest["input_table"] = "missing_payload.tsv"
    if identity_field == "cohort":
        metadata = manifest["cohorts"].pop(cohort)
        manifest["cohorts"][identity_value] = metadata
    else:
        manifest["cohorts"][cohort][identity_field] = identity_value
    _write_manifest(manifest_path, manifest)

    result = _run("development", "--manifest", manifest_path, "--out", tmp_path / "blocked")

    assert result.returncode == 2
    assert reason in result.stderr
    assert "input table is unavailable" not in result.stderr
    assert not (tmp_path / "blocked").exists()


def test_external_path_guard_preserves_symlink_alias_evidence_and_blocks_packets(tmp_path):
    from tools.a_p2.product import _guard_external_path

    target = tmp_path / "invented_sentinel.json"
    target.write_text("not a packet and not patient data", encoding="utf-8")
    alias_parent = tmp_path / "benign_alias"
    alias_parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(PermissionError, match="symlink ancestry"):
        _guard_external_path(alias_parent / target.name, "manifest")

    packet_path = tmp_path / "InGeStIoN_PaCkEt.JsOn"
    with pytest.raises(PermissionError, match="ingestion_packet.json"):
        _guard_external_path(packet_path, "input")

    protected_alias = tmp_path / "IMVIGOR210" / "invented_sentinel.tsv"
    with pytest.raises(PermissionError, match="protected path"):
        _guard_external_path(protected_alias, "equation")


def test_protected_input_and_identity_paths_are_allowed_only_for_real_final_role(tmp_path):
    from tools.a_p2.product import _identity_path, _input_path

    protected_root = tmp_path / "IMVIGOR210"
    protected_root.mkdir()
    manifest_path = tmp_path / "invented_manifest.json"
    synthetic = {
        "data_classification": "SYNTHETIC_ONLY",
        "role": "final_test",
        "input_table": str(protected_root / "invented.tsv"),
        "identity_provenance": {"sidecar": str(protected_root / "invented_identity.json")},
    }
    with pytest.raises(PermissionError, match="protected path"):
        _input_path(manifest_path, synthetic)
    with pytest.raises(PermissionError, match="protected path"):
        _identity_path(manifest_path, synthetic)

    real_development = {
        **synthetic,
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "role": "development",
    }
    with pytest.raises(PermissionError, match="protected path"):
        _input_path(manifest_path, real_development)
    with pytest.raises(PermissionError, match="protected path"):
        _identity_path(manifest_path, real_development)

    real_final = {**real_development, "role": "final_test"}
    assert _input_path(manifest_path, real_final) == protected_root / "invented.tsv"
    assert _identity_path(manifest_path, real_final) == protected_root / "invented_identity.json"


def test_manifest_equation_release_payload_and_identity_paths_are_guarded_before_reads(tmp_path, monkeypatch):
    from tools.a_p2 import product

    target_dir = tmp_path / "invented_external_targets"
    target_dir.mkdir()
    names = ("manifest.json", "equation.json", "release.json", "payload.tsv", "identity.json")
    targets = {name: target_dir / name for name in names}
    for name, target in targets.items():
        target.write_text("invented sentinel", encoding="utf-8")
    alias_dir = tmp_path / "invented_benign_alias"
    alias_dir.symlink_to(target_dir, target_is_directory=True)

    original_read_bytes = Path.read_bytes

    def read_spy(path):
        if path.parent == target_dir:
            pytest.fail("path guard followed a symlink alias and read a sentinel")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_spy)
    aliased_manifest = alias_dir / "manifest.json"
    with pytest.raises(PermissionError, match="symlink ancestry"):
        product._preflight_manifest(aliased_manifest, "development", False)
    with pytest.raises(PermissionError, match="symlink ancestry"):
        product._verify_equation(alias_dir / "equation.json")
    with pytest.raises(PermissionError, match="symlink ancestry"):
        product._authorize_real({}, b"invented", "development", alias_dir / "release.json", None)

    manifest = {
        "input_table": str(alias_dir / "payload.tsv"),
        "identity_provenance": {
            "sidecar": str(alias_dir / "identity.json"),
            "sidecar_sha256": "a" * 64,
        },
    }
    with pytest.raises(PermissionError, match="symlink ancestry"):
        product._input_path(targets["manifest.json"], manifest)
    with pytest.raises(PermissionError, match="symlink ancestry"):
        product._identity_path(targets["manifest.json"], manifest)


@pytest.mark.requires_r
def test_solver_jerr_failure_stops_before_a_later_family_fit(tmp_path):
    from tools.r_bridge import run_r

    manifest_path, payload, _ = _invented_inputs(tmp_path / "solver_fault")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = tmp_path / "solver_fault_output"
    work = output / ".work"
    work.mkdir(parents=True)
    result = run_r(
        ROOT / "r/R/a_p2.R",
        {"features": payload},
        {
            "operation": "test-solver-failure-contract",
            "data_classification": "SYNTHETIC_ONLY",
            "cohorts": manifest["cohorts"],
            "feature_names": list(FEATURES),
            "response_column": "orr_class",
            "expected_outputs": ["solver_fault_injection.tsv"],
            "input_sha256": manifest["input_sha256"],
            "work_dir": str(work),
        },
        output / "r_bridge",
    )
    with result.outputs["solver_fault_injection.tsv"].open(newline="", encoding="utf-8") as stream:
        fault = next(csv.DictReader(stream, delimiter="\t"))
    assert fault["status"] == "EXPECTED_STOP"
    assert fault["jerr"] == "17"
    assert fault["fit_attempts"] == "1"
    assert fault["later_fit_executed"] == "FALSE"
    diagnostic = json.loads((work / "solver_failure.json").read_text(encoding="utf-8"))
    assert diagnostic["jerr"] == 17
    assert diagnostic["fit_attempts"] == 1


@pytest.mark.requires_r
def test_freeze_checks_every_leave_family_training_class_floor_and_final_guard(tmp_path):
    development_manifest, _, _ = _invented_inputs(
        tmp_path / "thin_families", studies=3, small_studies=(0, 1, 2),
    )
    frozen = tmp_path / "thin_frozen"
    result = _run("freeze", "--manifest", development_manifest, "--out", frozen)
    assert result.returncode == 0, result.stderr
    equation = json.loads((frozen / "equation.json").read_text(encoding="utf-8"))
    assert equation["status"] == "UNAVAILABLE_LEAVE_FAMILY_OUT_TRAINING_CLASS_FLOOR"
    diagnostics = list(csv.DictReader((frozen / "fit_diagnostics.tsv").open(newline="", encoding="utf-8"), delimiter="\t"))
    assert next(row for row in diagnostics if row["analysis"] == "PRIMARY_TPM")["status"] == equation["status"]

    final_manifest, _, _ = _invented_inputs(
        tmp_path / "thin_final", role="final_test", studies=1,
        prefix="invented_external",
    )
    final = json.loads(final_manifest.read_text(encoding="utf-8"))
    final["input_table"] = "must_not_read.tsv"
    _write_manifest(final_manifest, final)
    blocked = _run(
        "final-evaluate", "--manifest", final_manifest,
        "--equation", frozen / "equation.json", "--out", tmp_path / "blocked_final",
    )
    assert blocked.returncode == 2
    assert "available synthetic equation" in blocked.stderr
    assert "input table is unavailable" not in blocked.stderr
    assert not (tmp_path / "blocked_final").exists()


@pytest.mark.parametrize("failure", ["duplicate", "unresolved"])
def test_identity_sidecar_blocks_duplicate_or_unresolved_people_before_fitting(tmp_path, failure):
    manifest_path, _, _ = _invented_inputs(
        tmp_path / failure, studies=3, group_first_two=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sidecar_path = manifest_path.parent / manifest["identity_provenance"]["sidecar"]
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if failure == "duplicate":
        first_uid = sidecar["records"][0]["canonical_patient_uid"]
        first_cohort = sidecar["records"][0]["cohort"]
        cross_alias = next(
            record for record in sidecar["records"] if record["cohort"] != first_cohort
        )
        cross_alias["canonical_patient_uid"] = first_uid
    else:
        sidecar["records"][0]["resolution_status"] = "UNRESOLVED"
    _write_manifest(sidecar_path, sidecar)
    manifest["identity_provenance"]["sidecar_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    _write_manifest(manifest_path, manifest)

    output = tmp_path / f"{failure}_blocked"
    result = _run("development", "--manifest", manifest_path, "--out", output)

    assert result.returncode == 2
    assert ("repeats across input rows" if failure == "duplicate" else "unresolved identity") in result.stderr
    assert not output.exists()


def test_synthetic_identity_sidecar_rejects_known_source_aliases(tmp_path):
    manifest_path, payload, _ = _invented_inputs(tmp_path / "identity_alias")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sidecar_path = manifest_path.parent / manifest["identity_provenance"]["sidecar"]
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["records"][0]["canonical_patient_uid"] = "invented_alias_hugo_gse78220_patient"
    _write_manifest(sidecar_path, sidecar)
    manifest["identity_provenance"]["sidecar_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    _write_manifest(manifest_path, manifest)

    from tools.a_p2.product import _read_authorized_input_material, _identity_path, _input_path

    with pytest.raises(PermissionError, match="known or protected identity alias"):
        _read_authorized_input_material(
            _input_path(manifest_path, manifest),
            _identity_path(manifest_path, manifest),
            manifest,
            allow_protected=False,
        )


def test_release_binding_comparison_uses_decision_and_exact_input_equation_hashes():
    from tools.a_p2.product import _release_binding_errors, _release_record_is_approved

    expected = {
        "operation": "final-evaluate",
        "input_role": "final_test",
        "input_manifest_sha256": "a" * 64,
        "input_sha256": "b" * 64,
        "identity_sidecar_sha256": "c" * 64,
        "cohorts": ["fixture_final_cohort"],
        "outcome_fields": ["orr_class"],
        "test_role": "UNTOUCHED_FINAL_TEST",
        "frozen_equation_sha256": "d" * 64,
    }
    fixture = {
        "record_type": "a_p2_user_release_v2",
        "record_status": "TEST_ONLY_NOT_A_REAL_DECISION",
        "real_authorization": False,
        "decision": {
            "identity": "fixture_decision_only",
            "path": "docs/decisions/fixture_only.md",
            "sha256": "e" * 64,
        },
        **expected,
    }
    assert _release_binding_errors(fixture, expected) == []
    assert not _release_record_is_approved(fixture)
    assert fixture["real_authorization"] is False
    tampered = {**fixture, "frozen_equation_sha256": "f" * 64}
    assert _release_binding_errors(tampered, expected) == ["frozen_equation_sha256"]


def test_synthetic_final_equation_and_payload_are_private_exact_snapshots(tmp_path, monkeypatch):
    from tools.a_p2 import product

    manifest_path, payload, _ = _invented_inputs(
        tmp_path / "snapshot_final", role="final_test", studies=1,
        prefix="invented_external",
    )
    equation_path = _equation_file(tmp_path / "portable_equation.json")
    expected_payload = payload.read_bytes()
    expected_equation = equation_path.read_bytes()

    def replacing_bridge(operation, input_path, manifest, out_dir, equation_path=None, **kwargs):
        payload.write_bytes(b"replacement payload bytes after authorization")
        replacing_bridge.source_equation.write_bytes(b"replacement equation bytes after verification")
        assert input_path != payload
        assert equation_path != replacing_bridge.source_equation
        assert input_path.read_bytes() == expected_payload
        assert equation_path.read_bytes() == expected_equation
        assert input_path.parent.name == ".work"
        assert equation_path.parent == input_path.parent
        fake_output = tmp_path / "fake_bridge_outputs"
        fake_output.mkdir()
        outputs = {}
        for name in product._expected_outputs(operation):
            output = fake_output / name
            output.write_text("synthetic output\n", encoding="utf-8")
            outputs[name] = output
        return {"script_sha256": "1" * 64}, outputs

    replacing_bridge.source_equation = equation_path
    monkeypatch.setattr(product, "_bridge", replacing_bridge)
    output = tmp_path / "snapshot_output"
    product.run_final_evaluation(manifest_path, equation_path, output)

    retained_input = output / ".work" / "verified_input.tsv"
    retained_equation = output / ".work" / "verified_equation.json"
    assert retained_input.read_bytes() == expected_payload
    assert retained_equation.read_bytes() == expected_equation
    assert payload.read_bytes() != retained_input.read_bytes()
    assert equation_path.read_bytes() != retained_equation.read_bytes()


def test_product_and_equation_record_complete_code_and_lock_hash_provenance(tmp_path):
    manifest_path, _, _ = _invented_inputs(tmp_path / "provenance")
    output = tmp_path / "provenance_output"
    result = _run("freeze", "--manifest", manifest_path, "--out", output)
    assert result.returncode == 0, result.stderr
    product_manifest = json.loads((output / "product_manifest.json").read_text(encoding="utf-8"))
    equation = json.loads((output / "equation.json").read_text(encoding="utf-8"))
    expected_roles = {
        "python_product", "python_cli", "r_entrypoint", "r_random_streams",
        "r_bridge", "panel_registry", "renv_lock", "numerical_freeze_register",
        "validation_contract", "measurement_decision",
    }
    for provenance in (product_manifest["code_provenance"], equation["code_provenance"]):
        assert set(provenance) == expected_roles
        assert all(len(value) == 64 for value in provenance.values())
        assert all("/" not in value and "\\" not in value for value in provenance.values())


def test_every_comparator_result_states_partial_m2_cyt_overlap(tmp_path):
    manifest, _, _ = _invented_inputs(
        tmp_path / "comparison_outputs", studies=3,
    )
    output = tmp_path / "comparison_output"
    result = _run("development", "--manifest", manifest, "--out", output)
    assert result.returncode == 0, result.stderr
    caveat = "M2 includes GZMA and PRF1 and therefore partly overlaps the CYT comparator."
    for name in (
        "primary_leave_family_out.tsv", "primary_aggregates.tsv",
        "primary_split_sensitivity.tsv", "cohort_adaptive_leave_family_out.tsv",
        "cohort_adaptive_aggregates.tsv", "cohort_adaptive_split_sensitivity.tsv",
    ):
        with (output / name).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        assert rows
        assert all(row["comparator_membership_caveat"] == caveat for row in rows)


def test_a_p2_path_retains_successful_and_failed_private_bridge_stages(tmp_path, monkeypatch):
    from tools.a_p2 import product
    from tools.r_bridge import FakeR, RScriptError

    successful_manifest, _, _ = _invented_inputs(tmp_path / "successful_input")
    successful_output = tmp_path / "successful_product"
    successful_canned = {
        "a_p2.R": {
            name: "invented bridge output\n"
            for name in product._expected_outputs("development")
        }
    }
    real_run_r = product.run_r

    def injected_run(canned):
        def call(script, inputs, config, out_dir, *, retention_dir=None):
            return real_run_r(
                script, inputs, config, out_dir, runner=FakeR(canned),
                retention_dir=retention_dir,
            )
        return call

    monkeypatch.setattr(product, "run_r", injected_run(successful_canned))
    product.run_development(successful_manifest, successful_output)

    successful_private_root = successful_output / ".work" / "r_bridge_stages"
    successful_stages = list(successful_private_root.glob(".r_bridge.stage-*"))
    assert len(successful_stages) == 1
    assert (successful_stages[0] / "config.json").is_file()
    assert (successful_stages[0] / "outputs" / "bridge-runtime.json").is_file()
    published_manifest_path = successful_output / "product_manifest.json"
    published_manifest_text = published_manifest_path.read_text(encoding="utf-8")
    published_manifest = json.loads(published_manifest_text)
    assert str(successful_private_root) not in published_manifest_text
    assert not any("stage" in name or ".work" in name for name in published_manifest["output_sha256"])

    failed_manifest, _, _ = _invented_inputs(tmp_path / "failed_input")
    failed_output = tmp_path / "failed_product"
    monkeypatch.setattr(product, "run_r", injected_run({}))
    with pytest.raises(RScriptError):
        product.run_development(failed_manifest, failed_output)

    failed_private_root = failed_output / ".work" / "r_bridge_stages"
    failed_stages = list(failed_private_root.glob(".r_bridge.stage-*"))
    assert len(failed_stages) == 1
    assert (failed_stages[0] / "config.json").is_file()
    assert not (failed_output / "product_manifest.json").exists()
    assert not (failed_output / "r_bridge").exists()
