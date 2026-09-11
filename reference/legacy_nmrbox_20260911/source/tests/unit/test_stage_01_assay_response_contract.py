from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd

from src.pipeline.cli import cmd_intake_build_response_record, cmd_intake_detect_assay_type
from src.pipeline.common.io import read_tsv, write_tsv
from src.pipeline.modules._01_dataset_intake.assay_detect import classify_expression_matrix


def _df(values: np.ndarray) -> pd.DataFrame:
    cols = [f"S{i+1}" for i in range(values.shape[1])]
    idx = [f"G{i+1}" for i in range(values.shape[0])]
    return pd.DataFrame(values, index=idx, columns=cols)


def test_assay_detector_covers_contract_classes() -> None:
    raw_counts = _df(np.array([[1, 4, 7], [0, 10, 3], [6, 2, 9]], dtype=float))
    tpm = _df(np.array([[200000.0, 500000.0], [300000.0, 300000.0], [500000.0, 200000.0]]))
    rlog = _df(np.array([[-2.1, -1.8, -0.4], [3.2, 1.2, 0.0], [1.8, 2.4, 0.4]]))
    microarray = _df(np.array([[-140.0, 180.0], [90.0, -70.0], [50.0, 60.0]]))
    log_no_neg = _df(np.array([[2.1, 4.4], [1.2, 3.8], [0.8, 5.5]]))
    normalized_const_colsum = _df(
        np.array([[12.1, 8.4], [10.7, 14.2], [7.2, 7.4], [9.9, 9.8]], dtype=float)
    )
    rounded_counts_suspect = _df(np.array([[1, 2, 3], [1.2, 1.8, 2.1], [4, 4.5, 5]], dtype=float))
    methylation = _df(
        np.tile(np.array([[0.15, 0.45, 0.82]], dtype=float), (120000, 1))
    )
    illumina_probe = pd.DataFrame(
        {
            "RCC-1": [185.7, 168.4, 166.2],
            "Detection Pval": [0.17, 0.64, 0.70],
            "RCC-2": [141.3, 164.6, 150.1],
            "Detection Pval.1": [0.75, 0.16, 0.50],
        },
        index=["ILMN_3166687", "ILMN_3165566", "ILMN_3164811"],
    )

    assert classify_expression_matrix(raw_counts).assay_type == "raw_counts"
    assert classify_expression_matrix(tpm).assay_type == "tpm"
    assert classify_expression_matrix(rlog).assay_type == "rlog_vst"
    assert classify_expression_matrix(microarray).assay_type == "microarray_intensity"
    assert classify_expression_matrix(illumina_probe).assay_type == "microarray_probe_matrix"
    assert classify_expression_matrix(log_no_neg).assay_type == "log_normalized"
    assert classify_expression_matrix(normalized_const_colsum).assay_type == "normalized_other"
    assert classify_expression_matrix(rounded_counts_suspect).assay_type == "raw_counts_suspect"
    assert classify_expression_matrix(methylation).assay_type == "methylation_beta"


def test_assay_override_precedence_and_conflict_log(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    expr_dir = downloads_root / "cohort_a"
    expr_dir.mkdir(parents=True)
    expr_file = expr_dir / "matrix.tsv"
    expr_file.write_text(
        "gene\tS1\tS2\nG1\t100000\t200000\nG2\t300000\t300000\nG3\t600000\t500000\n",
        encoding="utf-8",
    )
    expression_manifest = tmp_path / "geo_tables.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=[
            "cohort_id",
            "source_type_selected",
            "primary_expression_file",
            "downloads_folder",
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "source_type_selected": "processed_matrix",
                "primary_expression_file": "matrix.tsv",
                "downloads_folder": "cohort_a",
            }
        ],
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "response_label",
            "response_label_source",
            "timing_category",
            "assay_type_override",
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "S1",
                "response_label": "responder",
                "response_label_source": "manual_curation_sheet_applied",
                "timing_category": "pre-treatment",
                "assay_type_override": "raw_counts",
            }
        ],
    )

    out_dir = tmp_path / "out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_detect_assay_type(args) == 0

    rows = read_tsv(out_dir / "assay_detection.tsv")
    assert rows[0]["assay_type"] == "raw_counts"
    assert rows[0]["assay_type_detected"] == "tpm"
    assert rows[0]["override_applied"] == "true"
    assert rows[0]["assay_type_override_conflict"] == "true"


def test_response_and_timing_provenance_contract(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "response_label",
            "response_label_source",
            "timing_category",
            "metadata_text",
            "original_endpoint",
        ],
        rows=[
            {
                "cohort_id": "curated_recist",
                "sample_id": "X1",
                "response_label": "responder",
                "response_label_source": "manual_curation_sheet_applied",
                "timing_category": "pre-treatment",
                "metadata_text": "io.response: PR",
                "original_endpoint": "RECIST 1.1 BOR",
            },
            {
                "cohort_id": "text_only",
                "sample_id": "NR001",
                "response_label": "unknown",
                "response_label_source": "",
                "timing_category": "",
                "metadata_text": "best response: CR",
                "original_endpoint": "RECIST 1.1 BOR",
            },
            {
                "cohort_id": "sampleid_only",
                "sample_id": "CR007",
                "response_label": "unknown",
                "response_label_source": "",
                "timing_category": "",
                "metadata_text": "",
                "original_endpoint": "durable clinical benefit",
            },
        ],
    )

    out_dir = tmp_path / "out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_build_response_record(args) == 0

    defs = {r["cohort_id"]: r for r in read_tsv(out_dir / "response_definition.tsv")}
    assert defs["curated_recist"]["label_provenance"] == "curated"
    assert defs["text_only"]["label_provenance"] == "text_inferred"
    assert defs["sampleid_only"]["label_provenance"] == "sampleid_inferred"
    assert defs["sampleid_only"]["needs_manual_confirmation"] == "true"
    assert defs["sampleid_only"]["sd_handling"] == "SD=benefit_if_durable"

    timing = read_tsv(out_dir / "timing_provenance.tsv")
    timing_by_sample = {row["sample_id"]: row for row in timing}
    assert timing_by_sample["X1"]["timing_provenance"] == "curated"
    assert timing_by_sample["NR001"]["timing_provenance"] in {"text_inferred", "default_pre"}
    assert timing_by_sample["CR007"]["timing_provenance"] == "default_pre"


def test_stage01_contract_end_to_end_fixture_outputs_records(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    (downloads_root / "c_raw").mkdir(parents=True)
    (downloads_root / "c_tpm").mkdir(parents=True)
    (downloads_root / "c_unreadable").mkdir(parents=True)
    (downloads_root / "c_raw" / "expr.tsv").write_text(
        "gene\tS1\tS2\nG1\t10\t12\nG2\t0\t5\nG3\t7\t8\n", encoding="utf-8"
    )
    (downloads_root / "c_tpm" / "expr.tsv").write_text(
        "gene\tT1\tT2\nG1\t200000\t500000\nG2\t300000\t300000\nG3\t500000\t200000\n",
        encoding="utf-8",
    )
    (downloads_root / "c_unreadable" / "expr.tsv").write_text("not\ta\tmatrix\nx\ty\tz\n", encoding="utf-8")

    expression_manifest = tmp_path / "geo.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=[
            "cohort_id",
            "source_type_selected",
            "primary_expression_file",
            "downloads_folder",
        ],
        rows=[
            {
                "cohort_id": "c_raw",
                "source_type_selected": "raw_counts",
                "primary_expression_file": "expr.tsv",
                "downloads_folder": "c_raw",
            },
            {
                "cohort_id": "c_tpm",
                "source_type_selected": "processed_matrix",
                "primary_expression_file": "expr.tsv",
                "downloads_folder": "c_tpm",
            },
            {
                "cohort_id": "c_unreadable",
                "source_type_selected": "processed_matrix",
                "primary_expression_file": "expr.tsv",
                "downloads_folder": "c_unreadable",
            },
        ],
    )
    sample_manifest = tmp_path / "sample.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "response_label",
            "response_label_source",
            "timing_category",
            "metadata_text",
            "original_endpoint",
        ],
        rows=[
            {
                "cohort_id": "c_raw",
                "sample_id": "CR11",
                "response_label": "unknown",
                "response_label_source": "",
                "timing_category": "pre-treatment",
                "metadata_text": "",
                "original_endpoint": "RECIST 1.1 BOR",
            },
            {
                "cohort_id": "c_tpm",
                "sample_id": "S2",
                "response_label": "responder",
                "response_label_source": "manual_curation_sheet_applied",
                "timing_category": "",
                "metadata_text": "collection: Baseline",
                "original_endpoint": "durable clinical benefit",
            },
            {
                "cohort_id": "c_unreadable",
                "sample_id": "NR01",
                "response_label": "unknown",
                "response_label_source": "",
                "timing_category": "",
                "metadata_text": "",
                "original_endpoint": "",
            },
        ],
    )

    out_dir = tmp_path / "out"
    assay_args = Namespace(
        sample_manifest=str(sample_manifest),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    response_args = Namespace(
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_detect_assay_type(assay_args) == 0
    assert cmd_intake_build_response_record(response_args) == 0

    assay_rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "assay_detection.tsv")}
    assert assay_rows["c_raw"]["assay_type"] == "raw_counts"
    assert assay_rows["c_tpm"]["assay_type"] == "tpm"
    assert assay_rows["c_unreadable"]["assay_type"] == "unreadable"

    response_rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "response_definition.tsv")}
    assert response_rows["c_raw"]["label_provenance"] == "sampleid_inferred"
    assert response_rows["c_tpm"]["label_provenance"] == "curated"
    assert response_rows["c_tpm"]["sd_handling"] == "SD=benefit_if_durable"

    timing_rows = {row["sample_id"]: row for row in read_tsv(out_dir / "timing_provenance.tsv")}
    assert timing_rows["CR11"]["timing_provenance"] == "curated"
    assert timing_rows["S2"]["timing_provenance"] == "text_inferred"
    assert timing_rows["NR01"]["timing_provenance"] == "default_pre"


def test_stage01_flags_all_known_unreadable_series_matrix_cohorts(tmp_path: Path) -> None:
    unreadable_cohorts = [
        "gse202069_hcc_pdl1_tremelimumab",
        "gse305240_nsclc_atezolizumab",
        "gse305511_hcc_atezolizumab_bevacizumab",
        "gse222932_urothelial_guadecitabine_atezolizumab",
    ]
    downloads_root = tmp_path / "downloads"
    rows = []
    sample_rows = []
    for cohort in unreadable_cohorts:
        cohort_dir = downloads_root / cohort
        cohort_dir.mkdir(parents=True, exist_ok=True)
        expr_file = cohort_dir / "expr.tsv"
        expr_file.write_text("not\ta\tmatrix\nx\ty\tz\n", encoding="utf-8")
        rows.append(
            {
                "cohort_id": cohort,
                "source_type_selected": "processed_matrix",
                "primary_expression_file": "expr.tsv",
                "downloads_folder": cohort,
            }
        )
        sample_rows.append(
            {
                "cohort_id": cohort,
                "sample_id": f"{cohort}_S1",
                "response_label": "unknown",
                "response_label_source": "",
                "timing_category": "",
                "metadata_text": "",
                "original_endpoint": "",
            }
        )

    expression_manifest = tmp_path / "geo.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "source_type_selected", "primary_expression_file", "downloads_folder"],
        rows=rows,
    )
    sample_manifest = tmp_path / "sample.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "response_label",
            "response_label_source",
            "timing_category",
            "metadata_text",
            "original_endpoint",
        ],
        rows=sample_rows,
    )
    out_dir = tmp_path / "out"
    assay_args = Namespace(
        sample_manifest=str(sample_manifest),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    response_args = Namespace(
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_detect_assay_type(assay_args) == 0
    assert cmd_intake_build_response_record(response_args) == 0

    assay_rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "assay_detection.tsv")}
    response_rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "response_definition.tsv")}
    for cohort in unreadable_cohorts:
        assert assay_rows[cohort]["assay_type"] == "unreadable"
        assert "known_series_matrix_unreadable" in assay_rows[cohort]["cohort_flags"]
        assert "known_series_matrix_unreadable" in response_rows[cohort]["cohort_flags"]
