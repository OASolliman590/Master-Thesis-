from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pandas as pd

from src.pipeline.cli import (
    _looks_like_count_matrix,
    cmd_intake_apply_characteristics_mapping,
    cmd_intake_extract_characteristics,
    cmd_intake_extract_expression_aliases,
    cmd_intake_merge_extracted_metadata,
)
from src.pipeline.common.io import read_tsv, write_tsv


def _write_soft(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_looks_like_count_matrix_distinguishes_counts_from_logged_values() -> None:
    count_df = pd.DataFrame({"S1": [0, 10, 25], "S2": [3, 9, 30]}, index=["G1", "G2", "G3"])
    logged_df = pd.DataFrame({"S1": [-1.2, 1.5], "S2": [0.0, 2.7]}, index=["G1", "G2"])

    assert _looks_like_count_matrix(count_df) is True
    assert _looks_like_count_matrix(logged_df) is False


def test_extract_characteristics_writes_long_wide_and_inventory(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "folder1"
    soft_path = cohort_dir / "GSE12345_family.soft"
    _write_soft(
        soft_path,
        "\n".join(
            [
                "^SAMPLE = GSM1",
                "!Sample_title = Pt1",
                "!Sample_source_name_ch1 = tumor",
                "!Sample_description = baseline biopsy",
                "!Sample_characteristics_ch1 = response: PR",
                "!Sample_characteristics_ch1 = visit (pre or on treatment): Pre",
                "^SAMPLE = GSM2",
                "!Sample_title = Pt2",
                "!Sample_source_name_ch1 = tumor",
                "!Sample_characteristics_ch1 = response: PD",
            ]
        )
        + "\n",
    )
    expression_manifest = tmp_path / "geo_tables.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "downloads_folder", "primary_expression_file"],
        rows=[
            {
                "cohort_id": "gse12345_test",
                "downloads_folder": "folder1",
                "primary_expression_file": "dummy.tsv",
            }
        ],
    )

    out_dir = tmp_path / "out"
    args = Namespace(
        downloads_root=str(downloads_root),
        expression_manifest=str(expression_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_extract_characteristics(args) == 0

    long_rows = read_tsv(out_dir / "characteristics_extracted_long.tsv")
    wide_rows = read_tsv(out_dir / "characteristics_extracted_wide.tsv")
    inventory_rows = read_tsv(out_dir / "characteristic_key_inventory.tsv")

    assert any(r["field_key"] == "response" and r["field_value"] == "PR" for r in long_rows)
    assert any(r["sample_id"] == "GSM1" and r["visit_pre_or_on_treatment"] == "Pre" for r in wide_rows)
    assert any(r["char_key"] == "response" and r["relevance_class"] == "response" for r in inventory_rows)


def test_apply_characteristics_mapping_maps_response_and_timing(tmp_path: Path) -> None:
    characteristics = tmp_path / "characteristics.tsv"
    write_tsv(
        characteristics,
        fieldnames=["cohort_id", "sample_id", "field_source", "field_key", "field_value"],
        rows=[
            {
                "cohort_id": "gse91061_melanoma_pd1",
                "sample_id": "GSM1",
                "field_source": "characteristics",
                "field_key": "response",
                "field_value": "PR",
            },
            {
                "cohort_id": "gse91061_melanoma_pd1",
                "sample_id": "GSM1",
                "field_source": "characteristics",
                "field_key": "visit (pre or on treatment)",
                "field_value": "Pre",
            },
        ],
    )
    response_mapping = tmp_path / "response.tsv"
    timing_mapping = tmp_path / "timing.tsv"
    write_tsv(
        response_mapping,
        fieldnames=["cohort_id", "source_field", "source_value", "pipeline_label", "notes"],
        rows=[
            {
                "cohort_id": "DEFAULT",
                "source_field": "*",
                "source_value": "PR",
                "pipeline_label": "responder",
                "notes": "",
            }
        ],
    )
    write_tsv(
        timing_mapping,
        fieldnames=["cohort_id", "source_field", "source_value", "pipeline_label", "notes"],
        rows=[
            {
                "cohort_id": "gse91061_melanoma_pd1",
                "source_field": "visit (pre or on treatment)",
                "source_value": "Pre",
                "pipeline_label": "pre-treatment",
                "notes": "",
            }
        ],
    )

    out_dir = tmp_path / "out"
    args = Namespace(
        characteristics=str(characteristics),
        response_mapping=str(response_mapping),
        timing_mapping=str(timing_mapping),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_apply_characteristics_mapping(args) == 0

    mapped_rows = read_tsv(out_dir / "response_labels_mapped.tsv")
    assert mapped_rows[0]["response_label"] == "responder"
    assert mapped_rows[0]["timing_category"] == "pre-treatment"
    assert mapped_rows[0]["confidence"] == "high"


def test_extract_expression_aliases_uses_title_transform(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "folder2"
    _write_soft(
        cohort_dir / "GSE23456_family.soft",
        "\n".join(
            [
                "^SAMPLE = GSM9",
                "!Sample_title = RNA-seq_Dis_01",
                "!Sample_source_name_ch1 = tumor",
            ]
        )
        + "\n",
    )
    expr_path = cohort_dir / "expr.tsv"
    expr_path.write_text("gene_id\tDis_01\nGENE1\t5\nGENE2\t7\n", encoding="utf-8")
    expression_manifest = tmp_path / "geo_tables.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "downloads_folder", "primary_expression_file"],
        rows=[
            {
                "cohort_id": "gse23456_test",
                "downloads_folder": "folder2",
                "primary_expression_file": "expr.tsv",
            }
        ],
    )

    out_dir = tmp_path / "out"
    args = Namespace(
        downloads_root=str(downloads_root),
        expression_manifest=str(expression_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_extract_expression_aliases(args) == 0

    alias_rows = read_tsv(out_dir / "expression_aliases.tsv")
    assert alias_rows[0]["expression_sample_alias"] == "Dis_01"
    assert alias_rows[0]["match_status"] == "matched"


def test_merge_extracted_metadata_updates_manifest_and_eligibility(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "pair_id",
            "input_class",
            "analysis_role",
            "include_flag",
            "exclude_reason",
            "response_label_source",
            "comparison_tracks_final",
            "expression_sample_alias",
        ],
        rows=[
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S1",
                "patient_id": "P1",
                "cancer_type": "Melanoma",
                "therapy_class": "ICI monotherapy",
                "therapy_agent": "anti-PD1",
                "specimen_type": "bulk tumor sample",
                "timing_category": "unknown",
                "response_label": "unknown",
                "pair_id": "",
                "input_class": "processed_matrix",
                "analysis_role": "analysis",
                "include_flag": "false",
                "exclude_reason": "response_unknown;timing_unknown",
                "response_label_source": "pending_manual_curation",
                "comparison_tracks_final": "PRE_RESPONSE",
                "expression_sample_alias": "",
            },
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S2",
                "patient_id": "P2",
                "cancer_type": "Melanoma",
                "therapy_class": "ICI monotherapy",
                "therapy_agent": "anti-PD1",
                "specimen_type": "bulk tumor sample",
                "timing_category": "unknown",
                "response_label": "unknown",
                "pair_id": "",
                "input_class": "processed_matrix",
                "analysis_role": "analysis",
                "include_flag": "false",
                "exclude_reason": "response_unknown;timing_unknown",
                "response_label_source": "pending_manual_curation",
                "comparison_tracks_final": "PRE_RESPONSE",
                "expression_sample_alias": "",
            },
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S3",
                "patient_id": "P3",
                "cancer_type": "Melanoma",
                "therapy_class": "ICI monotherapy",
                "therapy_agent": "anti-PD1",
                "specimen_type": "bulk tumor sample",
                "timing_category": "unknown",
                "response_label": "unknown",
                "pair_id": "",
                "input_class": "processed_matrix",
                "analysis_role": "analysis",
                "include_flag": "false",
                "exclude_reason": "response_unknown;timing_unknown",
                "response_label_source": "pending_manual_curation",
                "comparison_tracks_final": "PRE_RESPONSE",
                "expression_sample_alias": "",
            },
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S4",
                "patient_id": "P4",
                "cancer_type": "Melanoma",
                "therapy_class": "ICI monotherapy",
                "therapy_agent": "anti-PD1",
                "specimen_type": "bulk tumor sample",
                "timing_category": "unknown",
                "response_label": "unknown",
                "pair_id": "",
                "input_class": "processed_matrix",
                "analysis_role": "analysis",
                "include_flag": "false",
                "exclude_reason": "response_unknown;timing_unknown",
                "response_label_source": "pending_manual_curation",
                "comparison_tracks_final": "PRE_RESPONSE",
                "expression_sample_alias": "",
            },
        ],
    )
    response_labels = tmp_path / "mapped.tsv"
    write_tsv(
        response_labels,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "response_label",
            "timing_category",
            "response_source_field",
            "timing_source_field",
            "confidence",
        ],
        rows=[
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S1",
                "response_label": "responder",
                "timing_category": "pre-treatment",
                "response_source_field": "response",
                "timing_source_field": "visit",
                "confidence": "high",
            },
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S2",
                "response_label": "responder",
                "timing_category": "pre-treatment",
                "response_source_field": "response",
                "timing_source_field": "visit",
                "confidence": "high",
            },
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S3",
                "response_label": "non_responder",
                "timing_category": "pre-treatment",
                "response_source_field": "response",
                "timing_source_field": "visit",
                "confidence": "high",
            },
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S4",
                "response_label": "non_responder",
                "timing_category": "pre-treatment",
                "response_source_field": "response",
                "timing_source_field": "visit",
                "confidence": "high",
            },
        ],
    )
    expression_aliases = tmp_path / "aliases.tsv"
    write_tsv(
        expression_aliases,
        fieldnames=["cohort_id", "sample_id", "expression_sample_alias", "match_method", "match_status"],
        rows=[
            {
                "cohort_id": "gse77777_test",
                "sample_id": "S1",
                "expression_sample_alias": "Alias1",
                "match_method": "title_exact",
                "match_status": "matched",
            }
        ],
    )

    out_manifest = tmp_path / "updated_manifest.tsv"
    eligibility_report = tmp_path / "eligibility.tsv"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        response_labels=str(response_labels),
        expression_aliases=str(expression_aliases),
        out=str(out_manifest),
        eligibility_report=str(eligibility_report),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_merge_extracted_metadata(args) == 0

    updated_rows = read_tsv(out_manifest)
    report_rows = read_tsv(eligibility_report)
    assert all(row["include_flag"] == "true" for row in updated_rows)
    assert updated_rows[0]["expression_sample_alias"] == "Alias1"
    assert report_rows[0]["de_eligible"] == "true"
