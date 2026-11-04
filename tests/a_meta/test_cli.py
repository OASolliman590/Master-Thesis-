from __future__ import annotations

import csv
import hashlib
import json
from types import SimpleNamespace

import pytest

from tools.a_meta.__main__ import (
    _cohort_row_identity_sha256,
    _panel_coverage_counts,
    _validate_feature_manifest,
    main,
)
from tools.a_meta.effects import EFFECT_COLUMNS
from tools.a_meta.provenance import write_synthetic_fixture_manifest


def test_real_cohort_effects_are_refused_without_allow_outcomes(tmp_path):
    with pytest.raises(SystemExit, match="explicit --allow-outcomes"):
        main(["effects", "--cohort", "liu2019", "--results", str(tmp_path)])

    assert not (tmp_path / "liu2019").exists()


def test_real_effect_table_synthesis_is_refused_without_allow_outcomes(tmp_path):
    effect_dir = tmp_path / "synthetic-test-input"
    effect_dir.mkdir()
    effects_path = effect_dir / "effects.tsv"
    with effects_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(EFFECT_COLUMNS)
        writer.writerow({
            "unit_family": "panel", "unit": "PANEL", "study": "liu2019",
            "cancer": "melanoma", "cancer_components": "melanoma",
            "drug_class_stratum": "ALL", "endpoint_family": "orr",
            "endpoint_definition_id": "ORR", "patient_set_id": "set-hash",
            "n_R": 4, "n_NR": 4, "g": 0.2, "se": 0.1, "status": "ok",
        })
    (effect_dir / "manifest.json").write_text(json.dumps({
        "data_classification": "real",
        "cohort": "liu2019",
        "outputs_sha256": {"effects.tsv": hashlib.sha256(effects_path.read_bytes()).hexdigest()},
    }), encoding="utf-8")

    with pytest.raises(SystemExit, match="explicit --allow-outcomes"):
        main([
            "synthesize",
            "--effects",
            str(effects_path),
            "--stratum",
            "per_cancer",
            "--results",
            str(tmp_path / "results"),
        ])

    assert not (tmp_path / "results").exists()


def test_synthetic_effect_table_requires_fixture_manifest_and_hash(tmp_path):
    effect_dir = tmp_path / "synthetic"
    effect_dir.mkdir()
    effects_path = effect_dir / "effects.tsv"
    with effects_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=EFFECT_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow({
            "unit_family": "panel", "unit": "PANEL", "study": "synthetic_study",
            "cancer": "melanoma", "cancer_components": "melanoma",
            "drug_class_stratum": "ALL", "endpoint_family": "source_label",
            "endpoint_definition_id": "SOURCE_LABEL_UNSPECIFIED", "patient_set_id": "set-hash",
            "n_R": 4, "n_NR": 4, "g": 0.2, "se": 0.1, "status": "ok",
        })
    write_synthetic_fixture_manifest(
        effect_dir / "manifest.json",
        kind="effect_table",
        payload_sha256="unused-for-file-input",
        cohort_ids=("synthetic_study",),
        output_path=effects_path,
    )

    assert main([
        "synthesize", "--effects", str(effects_path), "--stratum", "per_cancer",
        "--results", str(tmp_path / "results"),
    ]) == 0
    assert (tmp_path / "results/meta").is_dir()
    assert list((tmp_path / "results/meta").glob("*/synthesis.tsv"))


def test_synthetic_manifest_naming_real_cohort_is_refused_before_effect_read(tmp_path):
    effect_dir = tmp_path / "contradictory"
    effect_dir.mkdir()
    manifest_path = effect_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": 1,
        "producer": "tools.a_meta.synthetic_fixture",
        "data_classification": "synthetic",
        "kind": "effect_table",
        "cohort": "liu2019",
        "cohort_ids": ["liu2019"],
    }), encoding="utf-8")

    with pytest.raises(SystemExit, match="Synthetic provenance contradicts"):
        main([
            "synthesize", "--effects", str(effect_dir / "effects.tsv"),
            "--stratum", "per_cancer", "--results", str(tmp_path / "results"),
        ])


def test_panel_coverage_counts_parse_false_strings_as_false():
    complete, incomplete = _panel_coverage_counts([
        {"unit_family": "panel", "complete": "true"},
        {"unit_family": "panel", "complete": "false"},
    ])

    assert (complete, incomplete) == (1, 1)


def test_feature_manifest_rejects_stale_input_output_and_row_identity(tmp_path):
    cohort_dir = tmp_path / "cohort"
    feature_dir = cohort_dir / "features"
    feature_dir.mkdir(parents=True)
    expression_path = cohort_dir / "expression.tsv"
    clinical_path = cohort_dir / "clinical.tsv"
    expression_path.write_text("gene\tsample-a\nsymbol\t1\n", encoding="utf-8")
    clinical_path.write_text("patient_id\tsample_id\ttimepoint\npatient-a\tsample-a\tPRE\n", encoding="utf-8")
    feature_path = feature_dir / "genes.tsv"
    feature_path.write_text("patient_row\tGENE_A\n0\t1\n", encoding="utf-8")
    view = SimpleNamespace(
        expression_path=expression_path,
        clinical_rows=[{"patient_id": "patient-a", "sample_id": "sample-a", "timepoint": "PRE"}],
    )
    manifest_path = feature_dir / "manifest.json"
    manifest = {
        "cohort": "synthetic_cohort",
        "data_classification": "synthetic",
        "inputs_sha256": {
            "cohort_expression": hashlib.sha256(expression_path.read_bytes()).hexdigest(),
            "cohort_clinical": hashlib.sha256(clinical_path.read_bytes()).hexdigest(),
        },
        "outputs_sha256": {"genes.tsv": hashlib.sha256(feature_path.read_bytes()).hexdigest()},
        "row_identity_sha256": _cohort_row_identity_sha256(view),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    _validate_feature_manifest(view, feature_dir, "synthetic_cohort")

    clinical_path.write_text("patient_id\tsample_id\ttimepoint\npatient-b\tsample-b\tPRE\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="stale relative to the current cohort view"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")

    clinical_path.write_text("patient_id\tsample_id\ttimepoint\npatient-a\tsample-a\tPRE\n", encoding="utf-8")
    feature_path.write_text("patient_row\tGENE_A\n0\t2\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="Feature output hash mismatch"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")

    feature_path.write_text("patient_row\tGENE_A\n0\t1\n", encoding="utf-8")
    view.clinical_rows[0]["patient_id"] = "patient-b"
    with pytest.raises(SystemExit, match="row identities"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")
