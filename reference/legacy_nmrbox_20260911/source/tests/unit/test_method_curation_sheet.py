from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_method_curation_sheet
from src.pipeline.common.io import read_tsv, write_tsv


def test_method_curation_sheet_prioritizes_manual_queue(tmp_path: Path) -> None:
    discovery_manifest = tmp_path / "discovery.tsv"
    method_inspection = tmp_path / "method.tsv"
    out_dir = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_manifest,
        fieldnames=[
            "cohort_id",
            "accession",
            "source_db",
            "cancer_type",
            "therapy_agent",
            "therapy_class",
            "timing_category",
            "response_framework",
            "n_samples_total",
            "n_responders",
            "n_nonresponders",
            "manual_confirmation_required",
            "manual_confirmation_reason",
            "notes",
        ],
        rows=[
            {
                "cohort_id": "c_ready",
                "accession": "GSE100001; SRP100001",
                "source_db": "GEO/SRA",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
                "therapy_class": "ICI monotherapy",
                "timing_category": "pre-treatment",
                "response_framework": "responder vs non-responder",
                "n_samples_total": "20",
                "n_responders": "9",
                "n_nonresponders": "11",
                "manual_confirmation_required": "false",
                "manual_confirmation_reason": "",
                "notes": "PMID 31234567",
            },
            {
                "cohort_id": "c_blocked",
                "accession": "GSE200002",
                "source_db": "GEO",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PDL1",
                "therapy_class": "ICI monotherapy",
                "timing_category": "likely pre-treatment",
                "response_framework": "R/NR expected; manual harmonization pending",
                "n_samples_total": "12",
                "n_responders": "",
                "n_nonresponders": "",
                "manual_confirmation_required": "true",
                "manual_confirmation_reason": "response_framework_needs_manual_confirmation",
                "notes": "",
            },
        ],
    )

    write_tsv(
        method_inspection,
        fieldnames=[
            "cohort_id",
            "recommended_primary_contrast",
            "recommended_analysis_method",
            "curation_flags",
        ],
        rows=[
            {
                "cohort_id": "c_ready",
                "recommended_primary_contrast": "PRE_RESPONSE",
                "recommended_analysis_method": "count_model_deseq2_or_edger",
                "curation_flags": "none",
            },
            {
                "cohort_id": "c_blocked",
                "recommended_primary_contrast": "NONE",
                "recommended_analysis_method": "limma_or_linear_model_scale_aware",
                "curation_flags": "response_labels_incomplete;timing_labels_incomplete",
            },
        ],
    )

    args = Namespace(
        discovery_manifest=str(discovery_manifest),
        method_inspection=str(method_inspection),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_method_curation_sheet(args) == 0

    rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "study_manual_curation.tsv")}
    ready = rows["c_ready"]
    blocked = rows["c_blocked"]

    assert ready["manual_review_status"] == "ready_for_modeling"
    assert ready["manual_review_priority"] == "low"
    assert ready["pmid_candidates"] == "31234567"
    assert ready["review_blockers"] == "none"

    assert blocked["manual_review_status"] == "pending_manual_review"
    assert blocked["manual_review_priority"] == "high"
    assert "missing_responder_counts" in blocked["review_blockers"]
    assert "contrast_not_eligible_from_manifest" in blocked["review_blockers"]


def test_method_curation_sheet_preserves_existing_manual_fields(tmp_path: Path) -> None:
    discovery_manifest = tmp_path / "discovery.tsv"
    method_inspection = tmp_path / "method.tsv"
    out_dir = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_manifest,
        fieldnames=[
            "cohort_id",
            "accession",
            "source_db",
            "cancer_type",
            "therapy_agent",
            "therapy_class",
            "timing_category",
            "response_framework",
            "n_samples_total",
            "n_responders",
            "n_nonresponders",
            "manual_confirmation_required",
            "manual_confirmation_reason",
            "notes",
        ],
        rows=[
            {
                "cohort_id": "c_keep",
                "accession": "GSE300003",
                "source_db": "GEO",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "therapy_class": "ICI monotherapy",
                "timing_category": "pre-treatment",
                "response_framework": "responder vs non-responder",
                "n_samples_total": "10",
                "n_responders": "4",
                "n_nonresponders": "6",
                "manual_confirmation_required": "false",
                "manual_confirmation_reason": "",
                "notes": "",
            }
        ],
    )
    write_tsv(
        method_inspection,
        fieldnames=[
            "cohort_id",
            "recommended_primary_contrast",
            "recommended_analysis_method",
            "curation_flags",
        ],
        rows=[
            {
                "cohort_id": "c_keep",
                "recommended_primary_contrast": "PRE_RESPONSE",
                "recommended_analysis_method": "count_model_deseq2_or_edger",
                "curation_flags": "none",
            }
        ],
    )
    existing_sheet = out_dir / "study_manual_curation.tsv"
    write_tsv(
        existing_sheet,
        fieldnames=[
            "cohort_id",
            "confirmed_disease",
            "confirmed_drug_regimen",
            "confirmed_timing_schema",
            "confirmed_response_schema",
            "paired_pre_post_available",
            "responder_count_confirmed",
            "nonresponder_count_confirmed",
            "curator",
            "curation_date",
            "curation_notes",
        ],
        rows=[
            {
                "cohort_id": "c_keep",
                "confirmed_disease": "Lung adenocarcinoma",
                "confirmed_drug_regimen": "nivolumab",
                "confirmed_timing_schema": "pre-treatment",
                "confirmed_response_schema": "R/NR",
                "paired_pre_post_available": "no",
                "responder_count_confirmed": "4",
                "nonresponder_count_confirmed": "6",
                "curator": "omara",
                "curation_date": "2026-03-22",
                "curation_notes": "manually validated",
            }
        ],
    )

    args = Namespace(
        discovery_manifest=str(discovery_manifest),
        method_inspection=str(method_inspection),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_method_curation_sheet(args) == 0

    rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "study_manual_curation.tsv")}
    row = rows["c_keep"]
    assert row["confirmed_disease"] == "Lung adenocarcinoma"
    assert row["curator"] == "omara"
    assert row["curation_notes"] == "manually validated"
