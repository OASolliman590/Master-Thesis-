from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.a1.__main__ import main
from tools.a1.pairing import CANONICAL_COLUMNS, write_synthetic_pair_manifest


def _row(study, patient, specimen, category, day=""):
    return {
        "study_id": study,
        "patient_id": patient,
        "specimen_id": specimen,
        "assay_id": f"assay-{specimen}",
        "timepoint_category": category,
        "collection_day": day,
        "day_precision": "exact" if day else "unknown",
        "index_episode": "episode-fixture",
        "exposure": "fixture-ici-only",
        "baseline_source": "source-primary",
        "prior_treatment": "none",
        "disease_state": "no_progression",
        "regimen_state": "stable",
        "compartment": "fixture-tumour",
        "platform": "rnaseq",
        "unit": "tpm",
        "assay_method": "fixture-whole-transcriptome",
        "assay_qualified": "yes",
        "lesion_id": "lesion-fixture",
        "source_locator": f"fixture://{specimen}",
        "source_confidence": "invented_high",
        "day_origin": "fixture-dose-origin" if day else "unknown",
        "annotation_id": "fixture-annotation-v1",
        "measurement_comparability_id": "fixture-tpm-v1",
        "endpoint_id": "fixture-endpoint",
        "admission_receipt": "invented-N12-receipt",
    }


def _policy_payload(study):
    return {
        "study_id": study,
        "status": "PROPOSED",
        "decision_ref": None,
        "baseline_window": "baseline",
        "windows": [
            {"window_id": "baseline", "role": "baseline", "categories": ["PRE"]},
            {
                "window_id": "on_window",
                "role": "followup",
                "categories": ["ON"],
                "day_interval": [8, 12],
                "day_origin": "fixture-dose-origin",
                "target_day": 10,
            },
        ],
        "baseline_hierarchy": ["source-primary"],
        "allowed_prior_treatment": ["none"],
        "allowed_disease_states": ["no_progression"],
        "allowed_regimen_states": ["stable"],
        "prefer_same_lesion": True,
        "allow_different_lesion": False,
        "endpoint_id": "fixture-endpoint",
        "admission_receipt": "invented-N12-receipt",
        "source_family_id": None,
        "overlap_receipt_id": None,
        "overlap_status": None,
    }


def test_invented_cli_demo_writes_outcome_free_manifest(tmp_path, capsys):
    output = tmp_path / "demo"
    assert main(["demo", "--out", str(output)]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report == {
        "data_classification": "synthetic",
        "endpoint_evaluable_counts": None,
        "missing_followups": 1,
        "patients_in": 3,
        "policy_status": "FIXTURE_ONLY_PROPOSAL",
        "selected_pairs": 2,
    }
    manifest = json.loads((output / "pairing" / "pair_manifest.json").read_text())
    assert manifest["data_classification"] == "synthetic"
    assert manifest["endpoint_evaluable_counts"] is None
    assert manifest["endpoint_status"] == "UNAVAILABLE_OUTCOME_LOCKED"
    with (output / "pairing" / "pair_candidates.tsv").open(newline="") as stream:
        header = next(csv.reader(stream, delimiter="\t"))
    assert "response" not in header
    assert "survival" not in header


def test_invented_analysis_demo_runs_primary_and_ancova_through_real_r(tmp_path, capsys):
    output = tmp_path / "analysis-demo"
    assert main(["demo-analysis", "--out", str(output)]) == 0
    report = json.loads(capsys.readouterr().out)
    estimates = {row["model"]: row for row in report["effects"]}

    assert report["data_classification"] == "synthetic"
    assert report["policy_status"] == "FIXTURE_ONLY_PROPOSAL"
    assert estimates["delta_primary"]["status"] == "ESTIMABLE"
    assert float(estimates["delta_primary"]["estimate"]) == pytest.approx(-2.0, abs=1e-8)
    assert float(estimates["ancova_sensitivity"]["estimate"]) == pytest.approx(3.0, abs=1e-8)
    manifest = json.loads((output / report["provenance_manifest"]).read_text())
    assert manifest["data_classification"] == "synthetic"
    assert (output / "analysis" / "a_long_effects.tsv").is_file()


def test_future_n13_release_commands_expose_opt_in_but_pair_does_not(capsys):
    for command in (
        "pair-to-analysis", "two-timepoint", "ancova", "repeated",
        "randomized-arm", "synthesize",
    ):
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0
        assert "--allow-outcomes" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc:
        main(["pair", "--help"])
    assert exc.value.code == 0
    assert "--allow-outcomes" not in capsys.readouterr().out


def test_n13_cli_missing_opt_in_refuses_before_manifest_policy_or_source_access(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tools.a1.__main__.read_released_inputs",
        lambda *args, **kwargs: pytest.fail("released clinical input was accessed without opt-in"),
    )
    with pytest.raises(PermissionError, match="--allow-outcomes"):
        main([
            "two-timepoint",
            "--input-manifest", str(tmp_path / "invented-real-manifest.json"),
            "--release-record", str(tmp_path / "invented-real-record.json"),
            "--policy-json", str(tmp_path / "invented-policy.json"),
            "--out", str(tmp_path / "invented-output"),
            "--retention-dir", str(tmp_path / "invented-retention"),
        ])


def test_pair_command_reads_only_explicit_columns_and_requires_fixture_mode_for_proposals(tmp_path, capsys):
    study = "a-long-cli-fixture"
    input_path = tmp_path / "input.tsv"
    rows = [
        _row(study, "synthetic-patient-a", "synthetic-pre-a", "PRE"),
        _row(study, "synthetic-patient-a", "synthetic-on-a", "ON", "10"),
    ]
    with input_path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[*CANONICAL_COLUMNS, "Tumor_Shrinkage"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows([{**row, "Tumor_Shrinkage": "invented-only"} for row in rows])
    manifest_path = tmp_path / "input_manifest.json"
    write_synthetic_pair_manifest(input_path, manifest_path, study_id=study)
    columns_path = tmp_path / "columns.json"
    columns_path.write_text(json.dumps({name: name for name in CANONICAL_COLUMNS}))
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(_policy_payload(study)))
    output = tmp_path / "pairs"

    assert main([
        "pair",
        "--study-id", study,
        "--classification", "synthetic",
        "--input", str(input_path),
        "--columns-json", str(columns_path),
        "--policy-json", str(policy_path),
        "--acceptance-record-ref", "invented-only-fixture",
        "--acceptance-decision-id", "N12-fixture",
        "--fixture-only-policy",
        "--provenance-manifest", str(manifest_path),
        "--out", str(output),
    ]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["selected_pairs"] == 1
    manifest = json.loads((output / "pair_manifest.json").read_text())
    assert manifest["policy_status"] == "FIXTURE_ONLY_PROPOSAL"
    with (output / "pair_candidates.tsv").open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        candidate = next(reader)
    assert candidate["selected"] == "true"
    assert "Tumor_Shrinkage" not in candidate


def test_pair_cli_rejects_unsigned_real_window_policy_before_opening_source(tmp_path):
    study = "unresolved-real-study"
    columns_path = tmp_path / "real-columns.json"
    columns_path.write_text(json.dumps({name: name for name in CANONICAL_COLUMNS}))
    policy_path = tmp_path / "real-policy.json"
    policy_path.write_text(json.dumps(_policy_payload(study)))
    repo_root = Path(__file__).resolve().parents[2]
    output_path = repo_root / ".scratch" / f"w8-{tmp_path.name}-real-output"

    with pytest.raises(PermissionError, match="approved N12 record"):
        main([
            "pair",
            "--study-id", study,
            "--classification", "real",
            "--input", str(tmp_path / "must-not-be-opened.tsv"),
            "--columns-json", str(columns_path),
            "--policy-json", str(policy_path),
            "--acceptance-record-ref", "fixture-no-user-record",
            "--acceptance-decision-id", "N12",
            "--out", str(output_path),
        ])
