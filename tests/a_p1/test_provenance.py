from __future__ import annotations

import csv
import json

import pytest

from tools.a_meta.provenance import is_locked_study, known_cohort_ids
from tools.a_p1 import create_synthetic_manifest, load_input_tsv


FIELDS = (
    "study_id", "cancer", "patient_key", "specimen_key", "index_episode_id",
    "is_index_specimen", "expression_episode_id", "outcome_episode_id",
    "response_category", "source_criteria", "evaluation_window", "TPM_GZMA", "TPM_PRF1",
)
MEASUREMENT = {
    "representation_id": "invented-qualified-tpm-v1",
    "unit": "TPM",
    "transform": "unlogged_abundance",
    "gene_mapping": "unique",
    "qualification_status": "qualified",
}


def valid_row():
    return {
        "study_id": "invented-study-a",
        "cancer": "invented-cancer-a",
        "patient_key": "invented-patient-01",
        "specimen_key": "invented-specimen-01",
        "index_episode_id": "invented-episode-01",
        "is_index_specimen": True,
        "expression_episode_id": "invented-episode-01",
        "outcome_episode_id": "invented-episode-01",
        "response_category": "CR",
        "source_criteria": "invented-criteria-v1",
        "evaluation_window": "invented-window-v1",
        "TPM_GZMA": 4.0,
        "TPM_PRF1": 9.0,
    }


def write_tsv(path, row, extra=False):
    fields = list(FIELDS) + (["Tumor_Shrinkage"] if extra else [])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        output = dict(row)
        if extra:
            output["Tumor_Shrinkage"] = "invented-unselected-field"
        writer.writerow(output)


def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_tsv_loader_reads_only_exact_selected_fields_and_checks_payload_hash(tmp_path):
    input_path = tmp_path / "invented-input.tsv"
    manifest_path = tmp_path / "manifest.json"
    row = valid_row()
    write_tsv(input_path, row, extra=True)
    selected = [{field: str(row[field]) for field in FIELDS}]
    manifest = create_synthetic_manifest(selected, MEASUREMENT)
    write_manifest(manifest_path, manifest)

    loaded = load_input_tsv(input_path, manifest_path)

    assert list(loaded[0][0]) == list(FIELDS)
    assert "Tumor_Shrinkage" not in loaded[0][0]
    assert loaded[0][0]["TPM_GZMA"] == "4.0"


def test_synthetic_manifest_is_hash_bound_and_detects_selected_field_changes(tmp_path):
    input_path = tmp_path / "invented-input.tsv"
    manifest_path = tmp_path / "manifest.json"
    row = valid_row()
    write_tsv(input_path, row)
    selected = [{field: str(row[field]) for field in FIELDS}]
    write_manifest(manifest_path, create_synthetic_manifest(selected, MEASUREMENT))
    row["response_category"] = "PD"
    write_tsv(input_path, row)

    with pytest.raises(ValueError, match="hash"):
        load_input_tsv(input_path, manifest_path)


def test_real_route_refuses_before_opening_nonexistent_payload_without_release_flag(tmp_path):
    known_id = next(value for value in known_cohort_ids() if not is_locked_study(value))
    manifest_path = tmp_path / "real-manifest.json"
    write_manifest(manifest_path, {
        "manifest_version": 1,
        "producer": "invented-real-provenance-fixture",
        "data_classification": "real",
        "kind": "a_p1_input",
        "cohort_ids": [known_id],
        "selected_fields": list(FIELDS),
        "payload_sha256": "0" * 64,
    })

    with pytest.raises(PermissionError, match="allow-outcomes"):
        load_input_tsv(tmp_path / "payload-does-not-exist.tsv", manifest_path)


def test_known_real_identity_cannot_be_relabelled_as_synthetic(tmp_path):
    known_id = next(value for value in known_cohort_ids() if not is_locked_study(value))
    row = valid_row()
    row["study_id"] = known_id.upper()

    with pytest.raises(ValueError, match="(?i)known real cohort"):
        create_synthetic_manifest([row], MEASUREMENT)


def test_unlogged_uniquely_mapped_tpm_is_required_for_cyt():
    bad_contract = dict(MEASUREMENT, transform="log2_tpm")

    with pytest.raises(ValueError, match="unlogged TPM"):
        create_synthetic_manifest([valid_row()], bad_contract)


def test_protected_identity_is_refused_before_opening_input_payload(tmp_path):
    manifest_path = tmp_path / "protected-manifest.json"
    write_manifest(manifest_path, {
        "manifest_version": 1,
        "producer": "tools.a_p1.synthetic_fixture",
        "data_classification": "synthetic",
        "kind": "a_p1_input",
        "cohort_ids": ["invented-imvigor210-shadow"],
        "selected_fields": list(FIELDS),
        "measurement_contract": MEASUREMENT,
        "payload_sha256": "0" * 64,
    })

    with pytest.raises(PermissionError, match="Protected final-test"):
        load_input_tsv(tmp_path / "payload-does-not-exist.tsv", manifest_path)
