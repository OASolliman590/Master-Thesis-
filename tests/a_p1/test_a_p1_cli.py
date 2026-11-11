from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.a_meta.provenance import is_locked_study, known_cohort_ids
from tools.a_p1.__main__ import main


def test_cli_real_route_refuses_before_nonexistent_payload_without_release(tmp_path):
    known_id = next(value for value in known_cohort_ids() if not is_locked_study(value))
    manifest = {
        "manifest_version": 1,
        "producer": "invented-real-provenance-fixture",
        "data_classification": "real",
        "kind": "a_p1_input",
        "cohort_ids": [known_id],
        "selected_fields": [
            "study_id", "cancer", "patient_key", "specimen_key", "index_episode_id",
            "is_index_specimen", "expression_episode_id", "outcome_episode_id",
            "response_category", "source_criteria", "evaluation_window", "TPM_GZMA", "TPM_PRF1",
        ],
        "measurement_contract": {
            "representation_id": "invented-qualified-tpm-v1",
            "unit": "TPM",
            "transform": "unlogged_abundance",
            "gene_mapping": "unique",
            "qualification_status": "qualified",
        },
        "payload_sha256": "0" * 64,
    }
    provenance_path = tmp_path / "real-manifest.json"
    provenance_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PermissionError, match="allow-outcomes"):
        main([
            "analyze",
            "--input", str(tmp_path / "payload-does-not-exist.tsv"),
            "--provenance", str(provenance_path),
            "--out", str(tmp_path / "results"),
        ])


def test_cli_contract_packet_path_is_refused_before_any_file_is_opened(tmp_path):
    with pytest.raises(PermissionError, match="ingestion packets"):
        main([
            "analyze",
            "--input", str(tmp_path / "invented-input.tsv"),
            "--provenance", str(tmp_path / "invented-manifest.json"),
            "--synthesis-contract", str(tmp_path / "ingestion_packet.json"),
            "--out", str(tmp_path / "results"),
        ])


def test_cli_real_release_gate_precedes_synthesis_contract_read(tmp_path, monkeypatch):
    known_id = next(value for value in known_cohort_ids() if not is_locked_study(value))
    manifest_path = tmp_path / "invented-real-manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": 1,
        "producer": "invented-real-provenance-fixture",
        "data_classification": "real",
        "kind": "a_p1_input",
        "cohort_ids": [known_id],
        "selected_fields": [
            "study_id", "cancer", "patient_key", "specimen_key", "index_episode_id",
            "is_index_specimen", "expression_episode_id", "outcome_episode_id",
            "response_category", "source_criteria", "evaluation_window", "TPM_GZMA", "TPM_PRF1",
        ],
        "measurement_contract": {
            "representation_id": "invented-qualified-tpm-v1",
            "unit": "TPM",
            "transform": "unlogged_abundance",
            "gene_mapping": "unique",
            "qualification_status": "qualified",
        },
        "payload_sha256": "0" * 64,
    }), encoding="utf-8")
    contract_path = tmp_path / "invented-contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    original_read_text = Path.read_text

    def refuse_contract_read(path, *args, **kwargs):
        if path == contract_path:
            raise AssertionError("the synthesis contract was read before outcome preflight")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", refuse_contract_read)
    with pytest.raises(PermissionError, match="allow-outcomes"):
        main([
            "analyze",
            "--input", str(tmp_path / "invented-payload-does-not-exist.tsv"),
            "--provenance", str(manifest_path),
            "--synthesis-contract", str(contract_path),
            "--out", str(tmp_path / "results"),
        ])


@pytest.mark.requires_r
def test_two_study_synthetic_cli_demo_runs_pinned_r_and_reports_collection_intervals(tmp_path):
    output_dir = tmp_path / "invented-demo"

    exit_code = main(["demo", "--out", str(output_dir)])

    assert exit_code == 0
    result = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert result["data_classification"] == "synthetic"
    assert result["synthetic_scope"] == "invented software fixture; no biological claim"
    assert result["r_provenance"]["r_version"] == "4.6.1"
    assert result["r_provenance"]["bioconductor_version"] == "3.23"
    assert set(result["studies"]) == {"invented-study-a", "invented-study-b"}
    assert all(result["studies"][study]["bootstrap"]["status"] == "estimated"
               for study in result["studies"])
    assert set(result["synthesis"]["interval"]) == {"auc_orr", "auc_dcr", "delta"}
    assert result["synthesis"]["interval_status"] == "estimated_conditional_on_original_category_counts"
    assert result["synthesis"]["cross_study_pooled_auc"] is None
    assert result["panel_extension"]["status"] == "pending_a_p1_scoring_authorization"
