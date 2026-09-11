from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_method_apply_curation
from src.pipeline.common.io import read_tsv, write_tsv


def test_method_apply_curation_updates_manifest_and_builds_projection(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    curation_sheet = tmp_path / "study_manual_curation.tsv"
    out_manifest = tmp_path / "sample_manifest_curated.tsv"
    projection_out = tmp_path / "sample_manifest_projection.tsv"
    audit_out = tmp_path / "curation_apply_audit.tsv"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

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
        ],
        rows=[
            {
                "cohort_id": "c1",
                "sample_id": "c1__sample_01",
                "patient_id": "c1",
                "cancer_type": "Unknown",
                "therapy_class": "unknown",
                "therapy_agent": "unknown",
                "specimen_type": "bulk tumor sample",
                "timing_category": "unknown",
                "response_label": "unknown",
                "pair_id": "",
                "input_class": "raw_counts",
                "analysis_role": "analysis",
                "include_flag": "true",
                "exclude_reason": "",
                "response_label_source": "pending_manual_curation",
            }
        ],
    )

    write_tsv(
        curation_sheet,
        fieldnames=[
            "cohort_id",
            "cancer_type_declared",
            "therapy_agent_declared",
            "timing_declared",
            "n_responders_declared",
            "n_nonresponders_declared",
            "manual_review_status",
            "confirmed_disease",
            "confirmed_drug_regimen",
            "confirmed_timing_schema",
            "paired_pre_post_available",
            "responder_count_confirmed",
            "nonresponder_count_confirmed",
        ],
        rows=[
            {
                "cohort_id": "c1",
                "cancer_type_declared": "Melanoma",
                "therapy_agent_declared": "anti-PD1",
                "timing_declared": "pre-treatment; on-treatment",
                "n_responders_declared": "",
                "n_nonresponders_declared": "",
                "manual_review_status": "ready_for_modeling",
                "confirmed_disease": "Cutaneous melanoma",
                "confirmed_drug_regimen": "nivolumab",
                "confirmed_timing_schema": "pre-treatment; on-treatment",
                "paired_pre_post_available": "yes",
                "responder_count_confirmed": "2",
                "nonresponder_count_confirmed": "1",
            }
        ],
    )

    args = Namespace(
        sample_manifest=str(sample_manifest),
        curation_sheet=str(curation_sheet),
        out=str(out_manifest),
        projection_out=str(projection_out),
        audit_out=str(audit_out),
        run_manifest=str(run_manifest),
    )
    assert cmd_method_apply_curation(args) == 0

    curated_rows = read_tsv(out_manifest)
    assert len(curated_rows) == 1
    curated = curated_rows[0]
    assert curated["cancer_type"] == "Cutaneous melanoma"
    assert curated["therapy_agent"] == "nivolumab"
    assert curated["timing_category"] == "pre-treatment"
    assert curated["response_label_source"] == "manual_curation_sheet_applied"

    projection_rows = read_tsv(projection_out)
    assert len(projection_rows) == 6
    assert any(row["timing_category"] == "on-treatment" for row in projection_rows)
    assert all(row["pair_id"] for row in projection_rows)
    assert sum(1 for row in projection_rows if row["response_label"] == "responder") == 4
    assert sum(1 for row in projection_rows if row["response_label"] == "non_responder") == 2

    audit_rows = read_tsv(audit_out)
    assert len(audit_rows) == 1
    assert audit_rows[0]["status"] == "ready_for_modeling"
    assert audit_rows[0]["projection_rows"] == "6"

