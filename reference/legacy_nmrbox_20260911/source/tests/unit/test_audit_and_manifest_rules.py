from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_cohort_audit, cmd_manifest_build
from src.pipeline.common.io import read_tsv, write_tsv


def test_cohort_audit_applies_provenance_and_duplicate_rules(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.tsv"
    inventory_path = tmp_path / "inventory.tsv"
    out_dir = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        candidate_path,
        fieldnames=[
            "candidate_id",
            "source_stream",
            "cancer_type",
            "therapy_context",
            "comparison_type",
            "resolved_accession",
            "publication",
            "proposed_role",
            "notes",
        ],
        rows=[
            {
                "candidate_id": "cand_a",
                "source_stream": "GEO",
                "cancer_type": "Melanoma",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "GSE1000",
                "publication": "PMID:1",
                "proposed_role": "discovery",
                "notes": "",
            },
            {
                "candidate_id": "cand_b",
                "source_stream": "GEO",
                "cancer_type": "Melanoma",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "GSE1000",
                "publication": "PMID:2",
                "proposed_role": "validation",
                "notes": "",
            },
            {
                "candidate_id": "cand_c",
                "source_stream": "GEO",
                "cancer_type": "NSCLC",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "",
                "publication": "PMID:3",
                "proposed_role": "discovery",
                "notes": "",
            },
            {
                "candidate_id": "cand_d",
                "source_stream": "GEO",
                "cancer_type": "NSCLC",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "GSE2000",
                "publication": "",
                "proposed_role": "discovery",
                "notes": "",
            },
            {
                "candidate_id": "cand_e",
                "source_stream": "GEO",
                "cancer_type": "NSCLC",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "GSE3000",
                "publication": "PMID:5",
                "proposed_role": "validation",
                "notes": "",
            },
        ],
    )
    write_tsv(inventory_path, fieldnames=["accession"], rows=[{"accession": "GSE9999"}])

    args = Namespace(
        candidate_roster=str(candidate_path),
        inventory=str(inventory_path),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_cohort_audit(args) == 0

    rows = {r["candidate_id"]: r for r in read_tsv(out_dir / "cohort_promotion_audit.tsv")}
    assert rows["cand_a"]["decision"] == "hold"
    assert "duplicate_candidate_accessions" in rows["cand_a"]["notes"]
    assert rows["cand_b"]["decision"] == "hold"
    assert rows["cand_c"]["decision"] == "hold"
    assert "missing_accession" in rows["cand_c"]["notes"]
    assert rows["cand_d"]["decision"] == "hold"
    assert "missing_publication_provenance" in rows["cand_d"]["notes"]
    assert rows["cand_e"]["decision"] == "promote_validation"


def test_cohort_audit_consumes_stage01_contract_records_for_needs_curation(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.tsv"
    inventory_path = tmp_path / "inventory.tsv"
    assay_detection = tmp_path / "assay_detection.tsv"
    response_definition = tmp_path / "response_definition.tsv"
    out_dir = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        candidate_path,
        fieldnames=[
            "candidate_id",
            "source_stream",
            "cancer_type",
            "therapy_context",
            "comparison_type",
            "resolved_accession",
            "publication",
            "proposed_role",
            "notes",
        ],
        rows=[
            {
                "candidate_id": "gse5000_melanoma",
                "source_stream": "GEO",
                "cancer_type": "Melanoma",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "GSE5000",
                "publication": "PMID:1",
                "proposed_role": "discovery",
                "notes": "",
            },
            {
                "candidate_id": "gse6000_nsclc",
                "source_stream": "GEO",
                "cancer_type": "NSCLC",
                "therapy_context": "ICI",
                "comparison_type": "PRE_RESPONSE",
                "resolved_accession": "GSE6000",
                "publication": "PMID:2",
                "proposed_role": "validation",
                "notes": "",
            },
        ],
    )
    write_tsv(inventory_path, fieldnames=["accession"], rows=[])
    write_tsv(
        assay_detection,
        fieldnames=[
            "cohort_id",
            "assay_type",
            "detection_confidence",
        ],
        rows=[
            {"cohort_id": "gse5000_melanoma", "assay_type": "normalized_other", "detection_confidence": "0.42"},
            {"cohort_id": "gse6000_nsclc", "assay_type": "rlog_vst", "detection_confidence": "0.93"},
        ],
    )
    write_tsv(
        response_definition,
        fieldnames=[
            "cohort_id",
            "label_provenance",
            "needs_manual_confirmation",
        ],
        rows=[
            {
                "cohort_id": "gse5000_melanoma",
                "label_provenance": "curated",
                "needs_manual_confirmation": "false",
            },
            {
                "cohort_id": "gse6000_nsclc",
                "label_provenance": "sampleid_inferred",
                "needs_manual_confirmation": "true",
            },
        ],
    )

    args = Namespace(
        candidate_roster=str(candidate_path),
        inventory=str(inventory_path),
        assay_detection=str(assay_detection),
        response_definition=str(response_definition),
        min_assay_confidence=0.75,
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_cohort_audit(args) == 0

    rows = {r["candidate_id"]: r for r in read_tsv(out_dir / "cohort_promotion_audit.tsv")}
    assert rows["gse5000_melanoma"]["audit_status"] == "needs_curation"
    assert rows["gse5000_melanoma"]["include_decision"] == "hold"
    assert rows["gse5000_melanoma"]["reason"] == "low_assay_confidence"
    assert rows["gse5000_melanoma"]["decision"] == "hold"

    assert rows["gse6000_nsclc"]["audit_status"] == "needs_curation"
    assert rows["gse6000_nsclc"]["include_decision"] == "hold"
    assert rows["gse6000_nsclc"]["reason"] == "response_needs_manual_confirmation"
    assert rows["gse6000_nsclc"]["decision"] == "hold"


def test_manifest_build_excludes_unknown_timing_and_missing_cohort(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    discovery_path = tmp_path / "discovery.tsv"
    retrieval_path = tmp_path / "retrieval.tsv"
    intake_path = tmp_path / "intake.tsv"
    out_path = tmp_path / "sample_manifest.tsv"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_path,
        fieldnames=[
            "cohort_id",
            "accession",
            "cancer_type",
            "therapy_agent",
            "assay_type",
            "initial_analysis_slice",
            "why_in_core_v1",
        ],
        rows=[
            {
                "cohort_id": "c_ok",
                "accession": "GSE1",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
                "assay_type": "bulk RNA-seq",
                "initial_analysis_slice": "pre-treatment discovery",
                "why_in_core_v1": "test",
            },
            {
                "cohort_id": "c_bad",
                "accession": "GSE2",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "assay_type": "bulk RNA-seq",
                "initial_analysis_slice": "",
                "why_in_core_v1": "test",
            },
        ],
    )
    write_tsv(retrieval_path, fieldnames=["cohort_id"], rows=[{"cohort_id": "c_ok"}])
    write_tsv(
        intake_path,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "assay_type",
            "file_format",
            "input_class",
            "read_layout",
            "is_paired_sample",
            "normalization_state",
            "intake_include_flag",
            "intake_exclude_reason",
        ],
        rows=[
            {
                "cohort_id": "c_ok",
                "sample_id": "c_ok__R_01",
                "assay_type": "bulk RNA-seq",
                "file_format": "fastq.gz",
                "input_class": "FASTQ",
                "read_layout": "unknown",
                "is_paired_sample": "false",
                "normalization_state": "raw",
                "intake_include_flag": "true",
                "intake_exclude_reason": "",
            },
            {
                "cohort_id": "c_bad",
                "sample_id": "c_bad__sample_01",
                "assay_type": "bulk RNA-seq",
                "file_format": "fastq.gz",
                "input_class": "FASTQ",
                "read_layout": "unknown",
                "is_paired_sample": "false",
                "normalization_state": "raw",
                "intake_include_flag": "true",
                "intake_exclude_reason": "",
            },
            {
                "cohort_id": "c_missing",
                "sample_id": "c_missing__sample_01",
                "assay_type": "bulk RNA-seq",
                "file_format": "tsv",
                "input_class": "unsupported",
                "read_layout": "unknown",
                "is_paired_sample": "false",
                "normalization_state": "processed",
                "intake_include_flag": "true",
                "intake_exclude_reason": "",
            },
        ],
    )

    args = Namespace(
        discovery_manifest=str(discovery_path),
        retrieval_ledger=str(retrieval_path),
        intake_record=str(intake_path),
        out=str(out_path),
        run_manifest=str(run_manifest),
    )
    assert cmd_manifest_build(args) == 0

    rows = {r["cohort_id"]: r for r in read_tsv(out_path)}
    assert rows["c_ok"]["include_flag"] == "true"
    assert rows["c_ok"]["response_label"] == "responder"
    assert rows["c_bad"]["include_flag"] == "false"
    assert "missing_or_ambiguous_timing_category" in rows["c_bad"]["exclude_reason"]
    assert rows["c_missing"]["include_flag"] == "false"
    assert "cohort_missing_from_discovery_manifest" in rows["c_missing"]["exclude_reason"]
    assert "unsupported_input_class" in rows["c_missing"]["exclude_reason"]


def test_manifest_build_patient_manifest_authority_overrides_response_and_timing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    discovery_path = tmp_path / "discovery.tsv"
    retrieval_path = tmp_path / "retrieval.tsv"
    intake_path = tmp_path / "intake.tsv"
    patient_manifest = tmp_path / "patient_manifest.tsv"
    out_path = tmp_path / "sample_manifest.tsv"
    divergence_out = tmp_path / "divergences.tsv"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_path,
        fieldnames=[
            "cohort_id",
            "accession",
            "cancer_type",
            "therapy_agent",
            "assay_type",
            "initial_analysis_slice",
            "why_in_core_v1",
        ],
        rows=[
            {
                "cohort_id": "c_patient",
                "accession": "GSE1",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
                "assay_type": "bulk RNA-seq",
                "initial_analysis_slice": "",
                "why_in_core_v1": "test",
            }
        ],
    )
    write_tsv(retrieval_path, fieldnames=["cohort_id"], rows=[{"cohort_id": "c_patient"}])
    write_tsv(
        intake_path,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "assay_type",
            "file_format",
            "input_class",
            "read_layout",
            "is_paired_sample",
            "normalization_state",
            "intake_include_flag",
            "intake_exclude_reason",
            "response_label_inferred",
            "timing_category_inferred",
        ],
        rows=[
            {
                "cohort_id": "c_patient",
                "sample_id": "S1",
                "assay_type": "bulk RNA-seq",
                "file_format": "tsv",
                "input_class": "processed_matrix",
                "read_layout": "unknown",
                "is_paired_sample": "false",
                "normalization_state": "processed",
                "intake_include_flag": "true",
                "intake_exclude_reason": "",
                "response_label_inferred": "non_responder",
                "timing_category_inferred": "on-treatment",
            }
        ],
    )
    write_tsv(
        patient_manifest,
        fieldnames=[
            "patient_uid",
            "patient_id_raw",
            "cohort_id",
            "response_label",
            "pre_sample_ids",
            "on_sample_ids",
            "post_sample_ids",
            "unknown_sample_ids",
        ],
        rows=[
            {
                "patient_uid": "c_patient::P1",
                "patient_id_raw": "P1",
                "cohort_id": "c_patient",
                "response_label": "responder",
                "pre_sample_ids": "S1",
                "on_sample_ids": "",
                "post_sample_ids": "",
                "unknown_sample_ids": "",
            }
        ],
    )

    args = Namespace(
        discovery_manifest=str(discovery_path),
        retrieval_ledger=str(retrieval_path),
        intake_record=str(intake_path),
        out=str(out_path),
        patient_manifest=str(patient_manifest),
        divergence_out=str(divergence_out),
        run_manifest=str(run_manifest),
    )
    assert cmd_manifest_build(args) == 0

    row = read_tsv(out_path)[0]
    assert row["timing_category"] == "pre-treatment"
    assert row["response_label"] == "responder"
    assert row["response_label_source"] == "patient_manifest"
    assert row["include_flag"] == "true"

    divergences = read_tsv(divergence_out)
    assert {r["field"] for r in divergences} == {"timing_category", "response_label"}
    assert all(r["resolution"] == "patient_manifest_wins" for r in divergences)


def test_manifest_build_patient_manifest_unknown_values_fall_back(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    discovery_path = tmp_path / "discovery.tsv"
    retrieval_path = tmp_path / "retrieval.tsv"
    intake_path = tmp_path / "intake.tsv"
    patient_manifest = tmp_path / "patient_manifest.tsv"
    out_path = tmp_path / "sample_manifest.tsv"
    divergence_out = tmp_path / "divergences.tsv"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_path,
        fieldnames=[
            "cohort_id",
            "accession",
            "cancer_type",
            "therapy_agent",
            "assay_type",
            "initial_analysis_slice",
            "why_in_core_v1",
        ],
        rows=[
            {
                "cohort_id": "c_fallback",
                "accession": "GSE2",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
                "assay_type": "bulk RNA-seq",
                "initial_analysis_slice": "pre-treatment discovery",
                "why_in_core_v1": "test",
            }
        ],
    )
    write_tsv(retrieval_path, fieldnames=["cohort_id"], rows=[{"cohort_id": "c_fallback"}])
    write_tsv(
        intake_path,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "assay_type",
            "file_format",
            "input_class",
            "read_layout",
            "is_paired_sample",
            "normalization_state",
            "intake_include_flag",
            "intake_exclude_reason",
            "response_label_inferred",
            "timing_category_inferred",
        ],
        rows=[
            {
                "cohort_id": "c_fallback",
                "sample_id": "c_fallback__R_01",
                "assay_type": "bulk RNA-seq",
                "file_format": "tsv",
                "input_class": "processed_matrix",
                "read_layout": "unknown",
                "is_paired_sample": "false",
                "normalization_state": "processed",
                "intake_include_flag": "true",
                "intake_exclude_reason": "",
                "response_label_inferred": "responder",
                "timing_category_inferred": "pre-treatment",
            }
        ],
    )
    write_tsv(
        patient_manifest,
        fieldnames=[
            "patient_uid",
            "patient_id_raw",
            "cohort_id",
            "response_label",
            "pre_sample_ids",
            "on_sample_ids",
            "post_sample_ids",
            "unknown_sample_ids",
        ],
        rows=[
            {
                "patient_uid": "c_fallback::P1",
                "patient_id_raw": "P1",
                "cohort_id": "c_fallback",
                "response_label": "unknown",
                "pre_sample_ids": "",
                "on_sample_ids": "",
                "post_sample_ids": "",
                "unknown_sample_ids": "c_fallback__R_01",
            }
        ],
    )

    args = Namespace(
        discovery_manifest=str(discovery_path),
        retrieval_ledger=str(retrieval_path),
        intake_record=str(intake_path),
        out=str(out_path),
        patient_manifest=str(patient_manifest),
        divergence_out=str(divergence_out),
        run_manifest=str(run_manifest),
    )
    assert cmd_manifest_build(args) == 0

    row = read_tsv(out_path)[0]
    assert row["timing_category"] == "pre-treatment"
    assert row["response_label"] == "responder"
    assert row["response_label_source"] == "intake_metadata_inference"
    assert read_tsv(divergence_out) == []
