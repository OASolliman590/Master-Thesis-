from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_intake_build_geo_sample_manifest
from src.pipeline.common.io import read_tsv, write_tsv


def _write_input(path: Path) -> None:
    write_tsv(
        path,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_agent",
            "response_label_inferred",
            "timing_category_inferred",
            "source_type_selected",
            "preferred_input_route",
            "primary_expression_file",
            "analysis_ready_flag",
        ],
        rows=[
            {
                "cohort_id": "c_proc",
                "sample_id": "s1",
                "patient_id": "p1",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "processed_matrix",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "GSE1/matrix/GSE1_series_matrix.txt.gz",
                "analysis_ready_flag": "true",
            },
            {
                "cohort_id": "c_raw",
                "sample_id": "s2",
                "patient_id": "p2",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
                "response_label_inferred": "non_responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "raw_counts",
                "preferred_input_route": "raw_counts_or_fastq_path",
                "primary_expression_file": "GSE2/suppl/GSE2_raw_counts.tsv.gz",
                "analysis_ready_flag": "true",
            },
            {
                "cohort_id": "c_proc",
                "sample_id": "s3",
                "patient_id": "p3",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "unknown",
                "timing_category_inferred": "unknown",
                "source_type_selected": "processed_matrix",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "GSE1/matrix/GSE1_series_matrix.txt.gz",
                "analysis_ready_flag": "false",
            },
        ],
    )


def test_build_geo_sample_manifest_keeps_all_when_not_ready_only(tmp_path: Path) -> None:
    cohort_input = tmp_path / "cohort_input.tsv"
    out_manifest = tmp_path / "sample_manifest.tsv"
    ready_manifest = tmp_path / "sample_manifest_ready.tsv"
    summary_out = tmp_path / "summary.md"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    _write_input(cohort_input)

    args = Namespace(
        cohort_input_table=str(cohort_input),
        out=str(out_manifest),
        ready_out=str(ready_manifest),
        summary_out=str(summary_out),
        ready_only=False,
        processed_only=False,
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_sample_manifest(args) == 0

    all_rows = read_tsv(out_manifest)
    ready_rows = read_tsv(ready_manifest)
    assert len(all_rows) == 3
    assert len(ready_rows) == 2
    assert {r["input_class"] for r in ready_rows} == {"processed_matrix", "raw_counts"}


def test_build_geo_sample_manifest_processed_only_excludes_raw(tmp_path: Path) -> None:
    cohort_input = tmp_path / "cohort_input.tsv"
    out_manifest = tmp_path / "sample_manifest.tsv"
    ready_manifest = tmp_path / "sample_manifest_ready.tsv"
    summary_out = tmp_path / "summary.md"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    _write_input(cohort_input)

    args = Namespace(
        cohort_input_table=str(cohort_input),
        out=str(out_manifest),
        ready_out=str(ready_manifest),
        summary_out=str(summary_out),
        ready_only=True,
        processed_only=True,
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_sample_manifest(args) == 0

    written_rows = read_tsv(out_manifest)
    ready_rows = read_tsv(ready_manifest)
    assert len(written_rows) == 1
    assert len(ready_rows) == 1
    assert written_rows[0]["sample_id"] == "s1"
    assert written_rows[0]["input_class"] == "processed_matrix"


def test_build_geo_sample_manifest_enforces_stage01_assay_and_cohort_exclusion_gates(
    tmp_path: Path,
) -> None:
    cohort_input = tmp_path / "cohort_input.tsv"
    out_manifest = tmp_path / "sample_manifest.tsv"
    ready_manifest = tmp_path / "sample_manifest_ready.tsv"
    summary_out = tmp_path / "summary.md"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    write_tsv(
        cohort_input,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_agent",
            "response_label_inferred",
            "timing_category_inferred",
            "source_type_selected",
            "assay_type",
            "preferred_input_route",
            "primary_expression_file",
            "analysis_ready_flag",
        ],
        rows=[
            {
                "cohort_id": "cohort_ok",
                "sample_id": "s_ok",
                "patient_id": "p_ok",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "processed_matrix",
                "assay_type": "rlog_vst",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "x.tsv",
                "analysis_ready_flag": "true",
            },
            {
                "cohort_id": "gse126044_srp183455_nsclc_pd1",
                "sample_id": "s_dup",
                "patient_id": "p_dup",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "processed_matrix",
                "assay_type": "rlog_vst",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "x.tsv",
                "analysis_ready_flag": "true",
            },
            {
                "cohort_id": "gse165278_nsclc_pd1",
                "sample_id": "s_drop",
                "patient_id": "p_drop",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "processed_matrix",
                "assay_type": "rlog_vst",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "x.tsv",
                "analysis_ready_flag": "true",
            },
            {
                "cohort_id": "cohort_methyl",
                "sample_id": "s_meth",
                "patient_id": "p_meth",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "processed_matrix",
                "assay_type": "methylation_beta",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "x.tsv",
                "analysis_ready_flag": "true",
            },
            {
                "cohort_id": "cohort_unreadable",
                "sample_id": "s_bad",
                "patient_id": "p_bad",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
                "source_type_selected": "processed_matrix",
                "assay_type": "unreadable",
                "preferred_input_route": "processed_matrix",
                "primary_expression_file": "x.tsv",
                "analysis_ready_flag": "true",
            },
        ],
    )

    args = Namespace(
        cohort_input_table=str(cohort_input),
        out=str(out_manifest),
        ready_out=str(ready_manifest),
        summary_out=str(summary_out),
        ready_only=False,
        processed_only=False,
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_sample_manifest(args) == 0

    rows = {row["cohort_id"]: row for row in read_tsv(out_manifest)}
    assert rows["cohort_ok"]["include_flag"] == "true"

    assert rows["gse126044_srp183455_nsclc_pd1"]["include_flag"] == "false"
    assert rows["gse126044_srp183455_nsclc_pd1"]["exclude_reason"] == "duplicate_gse126044_deduped"

    assert rows["gse165278_nsclc_pd1"]["include_flag"] == "false"
    assert rows["gse165278_nsclc_pd1"]["exclude_reason"] == "excluded_no_responder_arm"

    assert rows["cohort_methyl"]["assay_type"] == "methylation_beta"
    assert rows["cohort_methyl"]["include_flag"] == "false"
    assert rows["cohort_methyl"]["exclude_reason"] == "excluded_assay_type_methylation_beta"

    assert rows["cohort_unreadable"]["assay_type"] == "unreadable"
    assert rows["cohort_unreadable"]["include_flag"] == "false"
    assert rows["cohort_unreadable"]["exclude_reason"] == "excluded_assay_type_unreadable"

    summary_text = summary_out.read_text(encoding="utf-8")
    assert "- n_unique_pre_treatment_cohorts_ready: 1" in summary_text
    assert "- expected_unique_pre_treatment_cohorts: 21" in summary_text
    assert "- pre_treatment_cohort_denominator_check: mismatch" in summary_text


def test_build_geo_sample_manifest_strict_pre_treatment_denominator_guard(tmp_path: Path) -> None:
    cohort_input = tmp_path / "cohort_input.tsv"
    out_manifest = tmp_path / "sample_manifest.tsv"
    ready_manifest = tmp_path / "sample_manifest_ready.tsv"
    summary_out = tmp_path / "summary.md"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    _write_input(cohort_input)

    args = Namespace(
        cohort_input_table=str(cohort_input),
        out=str(out_manifest),
        ready_out=str(ready_manifest),
        summary_out=str(summary_out),
        ready_only=False,
        processed_only=False,
        strict_pre_treatment_denominator=True,
        expected_pre_treatment_cohorts=5,
        run_manifest=str(run_manifest),
    )

    try:
        cmd_intake_build_geo_sample_manifest(args)
        assert False, "expected strict denominator mismatch to raise RuntimeError"
    except RuntimeError as exc:
        assert "pre-treatment cohort denominator mismatch" in str(exc)


def test_build_geo_sample_manifest_applies_curated_labels(tmp_path: Path) -> None:
    # Spec 010 Gate-2: s3 is unknown/unknown from inference and would be excluded;
    # the curated sheet supplies its labels by GSM sample_id (different cohort_id
    # naming on purpose) and it must become ready.
    cohort_input = tmp_path / "cohort_input.tsv"
    curated = tmp_path / "curated.tsv"
    out_manifest = tmp_path / "sample_manifest.tsv"
    ready_manifest = tmp_path / "sample_manifest_ready.tsv"
    summary_out = tmp_path / "summary.md"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    _write_input(cohort_input)
    write_tsv(
        curated,
        fieldnames=["cohort_id", "sample_id", "response_label", "timing_category"],
        rows=[
            {
                "cohort_id": "gse_x_nsclc_pd1",
                "sample_id": "s3",
                "response_label": "responder",
                "timing_category": "pre-treatment",
            },
        ],
    )

    args = Namespace(
        cohort_input_table=str(cohort_input),
        curated_manifest=str(curated),
        out=str(out_manifest),
        ready_out=str(ready_manifest),
        summary_out=str(summary_out),
        ready_only=False,
        processed_only=False,
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_sample_manifest(args) == 0

    rows = {r["sample_id"]: r for r in read_tsv(out_manifest)}
    assert rows["s3"]["response_label"] == "responder"
    assert rows["s3"]["timing_category"] == "pre-treatment"
    assert rows["s3"]["include_flag"] == "true"
    assert rows["s3"]["response_label_source"] == "manual_curation_sheet_applied"
    assert rows["s3"]["timing_provenance"] == "manual_curation_sheet"
    # was 2 ready without curation; s3 is rescued -> 3
    assert len(read_tsv(ready_manifest)) == 3


def test_build_geo_sample_manifest_curation_disabled_when_empty(tmp_path: Path) -> None:
    # Backward-compat: join disabled -> inference only, s3 stays excluded.
    cohort_input = tmp_path / "cohort_input.tsv"
    out_manifest = tmp_path / "sample_manifest.tsv"
    ready_manifest = tmp_path / "sample_manifest_ready.tsv"
    summary_out = tmp_path / "summary.md"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    _write_input(cohort_input)

    args = Namespace(
        cohort_input_table=str(cohort_input),
        curated_manifest="",
        out=str(out_manifest),
        ready_out=str(ready_manifest),
        summary_out=str(summary_out),
        ready_only=False,
        processed_only=False,
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_sample_manifest(args) == 0
    assert len(read_tsv(ready_manifest)) == 2
