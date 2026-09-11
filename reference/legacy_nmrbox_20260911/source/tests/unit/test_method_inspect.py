from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_method_inspect
from src.pipeline.common.io import read_tsv, write_tsv


def test_method_inspect_emits_cohort_level_plan(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    out_dir = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "input_class",
            "timing_category",
            "response_label",
            "pair_id",
            "include_flag",
        ],
        rows=[
            {
                "cohort_id": "c_count",
                "sample_id": "c_count__s1",
                "input_class": "FASTQ",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "pair_id": "p1",
                "include_flag": "true",
            },
            {
                "cohort_id": "c_count",
                "sample_id": "c_count__s2",
                "input_class": "FASTQ",
                "timing_category": "on-treatment",
                "response_label": "responder",
                "pair_id": "p1",
                "include_flag": "true",
            },
            {
                "cohort_id": "c_count",
                "sample_id": "c_count__s3",
                "input_class": "FASTQ",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "pair_id": "p2",
                "include_flag": "true",
            },
            {
                "cohort_id": "c_count",
                "sample_id": "c_count__s4",
                "input_class": "FASTQ",
                "timing_category": "on-treatment",
                "response_label": "non_responder",
                "pair_id": "p2",
                "include_flag": "true",
            },
            {
                "cohort_id": "c_matrix",
                "sample_id": "c_matrix__s1",
                "input_class": "processed_matrix",
                "timing_category": "unknown",
                "response_label": "unknown",
                "pair_id": "",
                "include_flag": "true",
            },
        ],
    )

    args = Namespace(
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_method_inspect(args) == 0

    rows = {r["cohort_id"]: r for r in read_tsv(out_dir / "cohort_method_inspection.tsv")}
    count_row = rows["c_count"]
    matrix_row = rows["c_matrix"]

    assert count_row["recommended_analysis_method"] == "count_model_deseq2_or_edger"
    assert count_row["eligible_pre_response"] == "true"
    assert count_row["eligible_treatment_delta"] == "true"
    assert count_row["eligible_on_response"] == "true"
    assert count_row["recommended_primary_contrast"] == "PRE_RESPONSE"

    assert matrix_row["recommended_analysis_method"] == "limma_or_linear_model_scale_aware"
    assert matrix_row["eligible_pre_response"] == "false"
    assert matrix_row["recommended_primary_contrast"] == "NONE"
    assert "response_labels_incomplete" in matrix_row["curation_flags"]
    assert "timing_labels_incomplete" in matrix_row["curation_flags"]
