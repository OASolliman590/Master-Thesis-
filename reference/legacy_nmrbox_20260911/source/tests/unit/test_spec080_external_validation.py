from __future__ import annotations

from pathlib import Path

from src.pipeline.cli import main
from src.pipeline.common.io import read_tsv, write_tsv


def _write_signature(path: Path) -> None:
    write_tsv(
        path,
        fieldnames=[
            "analysis_id",
            "signature_version",
            "gene_symbol",
            "signature_direction",
            "effect",
        ],
        rows=[
            {
                "analysis_id": "PRE_RESPONSE",
                "signature_version": "responder_signature_v1",
                "gene_symbol": "GENE_UP",
                "signature_direction": "up",
                "effect": "1.5",
            },
            {
                "analysis_id": "PRE_RESPONSE",
                "signature_version": "responder_signature_v1",
                "gene_symbol": "GENE_DOWN",
                "signature_direction": "down",
                "effect": "-1.2",
            },
            {
                "analysis_id": "PRE_RESPONSE",
                "signature_version": "responder_signature_v1",
                "gene_symbol": "MISSING_GENE",
                "signature_direction": "up",
                "effect": "0.8",
            },
        ],
    )


def test_external_validation_run_excludes_overlap_and_scores_frozen_signature(tmp_path: Path) -> None:
    signature = tmp_path / "pre_signature.tsv"
    _write_signature(signature)

    expr = tmp_path / "external_expr.tsv"
    expr.write_text(
        "\n".join(
            [
                "gene_id\tS_R1\tS_R2\tS_N1\tS_N2",
                "GENE_UP\t9\t8\t2\t3",
                "GENE_DOWN\t1\t2\t8\t7",
                "GENE_OUTSIDE_SIGNATURE\t100\t90\t80\t70",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    candidate_roster = tmp_path / "candidate_roster.tsv"
    write_tsv(
        candidate_roster,
        fieldnames=[
            "candidate_id",
            "cohort_id",
            "accession",
            "publication_id",
            "cancer_type_raw",
            "therapy_agent_raw",
            "therapy_class",
            "expression_data_status",
            "response_label_status",
            "timing_label_status",
            "candidate_source",
            "curation_status",
            "notes",
        ],
        rows=[
            {
                "candidate_id": "CAND_EXT",
                "cohort_id": "external_melanoma_pd1",
                "accession": "GSE999999",
                "publication_id": "PMID_EXT",
                "cancer_type_raw": "Melanoma",
                "therapy_agent_raw": "nivolumab",
                "therapy_class": "PD-1",
                "expression_data_status": "available",
                "response_label_status": "confirmed",
                "timing_label_status": "confirmed",
                "candidate_source": "fixture",
                "curation_status": "curated",
                "notes": "",
            },
            {
                "candidate_id": "CAND_OVERLAP",
                "cohort_id": "derivation_like",
                "accession": "GSE123456",
                "publication_id": "PMID_DERIVATION",
                "cancer_type_raw": "Melanoma",
                "therapy_agent_raw": "nivolumab",
                "therapy_class": "PD-1",
                "expression_data_status": "available",
                "response_label_status": "confirmed",
                "timing_label_status": "confirmed",
                "candidate_source": "fixture",
                "curation_status": "curated",
                "notes": "",
            },
            {
                "candidate_id": "CAND_TCGA",
                "cohort_id": "TCGA-SKCM",
                "accession": "TCGA-SKCM",
                "publication_id": "",
                "cancer_type_raw": "Melanoma",
                "therapy_agent_raw": "",
                "therapy_class": "",
                "expression_data_status": "available",
                "response_label_status": "missing",
                "timing_label_status": "missing",
                "candidate_source": "fixture",
                "curation_status": "uncurated",
                "notes": "",
            },
            {
                "candidate_id": "CAND_NEEDS_PAPER",
                "cohort_id": "external_unclear",
                "accession": "GSE888888",
                "publication_id": "PMID_UNCLEAR",
                "cancer_type_raw": "NSCLC",
                "therapy_agent_raw": "pembrolizumab",
                "therapy_class": "PD-1",
                "expression_data_status": "available",
                "response_label_status": "confirmed",
                "timing_label_status": "missing",
                "candidate_source": "fixture",
                "curation_status": "needs_paper_curation",
                "notes": "",
            },
        ],
    )

    derivation_lock = tmp_path / "derivation_lock.tsv"
    write_tsv(
        derivation_lock,
        fieldnames=[
            "lock_id",
            "analysis_id",
            "cohort_id",
            "accession",
            "secondary_accessions",
            "publication_id",
            "sample_id",
            "patient_id",
            "source_artifact",
        ],
        rows=[
            {
                "lock_id": "LOCK1",
                "analysis_id": "PRE_RESPONSE",
                "cohort_id": "derivation_like",
                "accession": "GSE123456",
                "secondary_accessions": "",
                "publication_id": "PMID_DERIVATION",
                "sample_id": "DERIVATION_SAMPLE",
                "patient_id": "",
                "source_artifact": "fixture",
            }
        ],
    )

    sample_manifest = tmp_path / "external_samples.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "external_sample_id",
            "candidate_id",
            "cohort_id",
            "patient_id",
            "timing_category",
            "response_label",
            "therapy_agent",
            "therapy_class",
            "cancer_type",
            "expression_file",
            "include_flag",
            "exclude_reason",
        ],
        rows=[
            {
                "external_sample_id": "S_R1",
                "candidate_id": "CAND_EXT",
                "cohort_id": "external_melanoma_pd1",
                "patient_id": "P1",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "therapy_agent": "nivolumab",
                "therapy_class": "PD-1",
                "cancer_type": "Melanoma",
                "expression_file": str(expr),
                "include_flag": "true",
                "exclude_reason": "",
            },
            {
                "external_sample_id": "S_R2",
                "candidate_id": "CAND_EXT",
                "cohort_id": "external_melanoma_pd1",
                "patient_id": "P2",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "therapy_agent": "nivolumab",
                "therapy_class": "PD-1",
                "cancer_type": "Melanoma",
                "expression_file": str(expr),
                "include_flag": "true",
                "exclude_reason": "",
            },
            {
                "external_sample_id": "S_N1",
                "candidate_id": "CAND_EXT",
                "cohort_id": "external_melanoma_pd1",
                "patient_id": "P3",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "therapy_agent": "nivolumab",
                "therapy_class": "PD-1",
                "cancer_type": "Melanoma",
                "expression_file": str(expr),
                "include_flag": "true",
                "exclude_reason": "",
            },
            {
                "external_sample_id": "S_N2",
                "candidate_id": "CAND_EXT",
                "cohort_id": "external_melanoma_pd1",
                "patient_id": "P4",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "therapy_agent": "nivolumab",
                "therapy_class": "PD-1",
                "cancer_type": "Melanoma",
                "expression_file": str(expr),
                "include_flag": "true",
                "exclude_reason": "",
            },
            {
                "external_sample_id": "DERIVATION_SAMPLE",
                "candidate_id": "CAND_OVERLAP",
                "cohort_id": "derivation_like",
                "patient_id": "P5",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "therapy_agent": "nivolumab",
                "therapy_class": "PD-1",
                "cancer_type": "Melanoma",
                "expression_file": str(expr),
                "include_flag": "true",
                "exclude_reason": "",
            },
        ],
    )

    out_dir = tmp_path / "external_validation"
    run_manifest = tmp_path / "logs" / "external_validation.yaml"
    result = main(
        [
            "external-validation",
            "run",
            "--candidate-roster",
            str(candidate_roster),
            "--derivation-lock",
            str(derivation_lock),
            "--sample-manifest",
            str(sample_manifest),
            "--signature",
            str(signature),
            "--out",
            str(out_dir),
            "--run-manifest",
            str(run_manifest),
        ]
    )

    assert result == 0

    roster = {
        row["candidate_id"]: row
        for row in read_tsv(out_dir / "eligibility" / "external_validation_cohort_roster.tsv")
    }
    assert roster["CAND_EXT"]["eligibility_status"] == "eligible"
    assert roster["CAND_EXT"]["claim_class"] == "external_ici_validation"
    assert roster["CAND_OVERLAP"]["eligibility_status"] == "excluded"
    assert roster["CAND_OVERLAP"]["independence_status"] == "overlap_detected"
    assert roster["CAND_TCGA"]["eligibility_status"] == "excluded"
    assert roster["CAND_TCGA"]["claim_class"] == "not_eligible"
    assert roster["CAND_NEEDS_PAPER"]["eligibility_status"] == "needs_paper_curation"

    leakage = read_tsv(out_dir / "eligibility" / "leakage_audit.tsv")
    assert any(row["leakage_status"] == "fail_overlap" for row in leakage)

    membership = read_tsv(out_dir / "membership" / "external_validation_membership.tsv")
    assert {row["external_sample_id"] for row in membership} == {
        "S_R1",
        "S_R2",
        "S_N1",
        "S_N2",
    }
    assert {row["analysis_id"] for row in membership} == {"PRE_RESPONSE"}

    scores = read_tsv(out_dir / "scores" / "external_signature_scores.tsv")
    assert len(scores) == 4
    assert all(row["n_signature_genes"] == "3" for row in scores)
    assert all(row["n_genes_observed"] == "2" for row in scores)
    assert all(row["scoring_method"] == "direction_weighted_mean_zscore_no_refit" for row in scores)

    coverage = read_tsv(out_dir / "scores" / "external_signature_gene_coverage.tsv")
    missing = [row for row in coverage if row["gene_symbol"] == "MISSING_GENE"]
    assert missing and all(row["observed_status"] == "missing" for row in missing)
    assert not any(row["gene_symbol"] == "GENE_OUTSIDE_SIGNATURE" for row in coverage)

    by_cohort = read_tsv(out_dir / "validation" / "external_validation_by_cohort.tsv")
    assert by_cohort[0]["validation_status"] == "completed"
    assert by_cohort[0]["claim_class"] == "external_ici_validation"
    assert float(by_cohort[0]["effect_size"]) > 0

    summary = read_tsv(out_dir / "validation" / "external_validation_summary.tsv")
    assert summary[0]["analysis_id"] == "PRE_RESPONSE"
    assert summary[0]["claim_class"] == "external_ici_validation"
    assert summary[0]["validation_status"] == "completed"
    assert "independent ICI-treated" in summary[0]["plain_language_interpretation"]

    boundaries = read_tsv(out_dir / "validation" / "external_validation_claim_boundaries.tsv")
    assert any(row["disallowed_label"] == "TCGA_response_validation" for row in boundaries)
    assert run_manifest.exists()
