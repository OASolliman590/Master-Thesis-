from __future__ import annotations

import importlib
from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_de_run, cmd_intake_build_sample_allocation
from src.pipeline.common.contrast_resolver import (
    build_treatment_delta_pair_audit,
    is_contrast_eligible,
)
from src.pipeline.common.io import read_tsv, write_tsv


allocation_module = importlib.import_module(
    "src.pipeline.modules.01_dataset_intake.sample_allocation"
)


def test_sample_allocation_assigns_unknown_response_to_unallocated() -> None:
    rows = [
        {
            "cohort_id": "cohort_a",
            "sample_id": "S1",
            "timing_category": "pre-treatment",
            "response_label": "responder",
            "include_flag": "true",
        },
        {
            "cohort_id": "cohort_a",
            "sample_id": "S2",
            "timing_category": "post-treatment",
            "response_label": "unknown",
            "include_flag": "false",
        },
    ]

    allocated = allocation_module.build_sample_allocation(rows)

    assert allocated[0]["assigned_bucket"] == "PRE_RESPONSE"
    assert allocated[0]["eligible_contrasts"] == "PRE_RESPONSE"
    assert allocated[1]["assigned_bucket"] == "UNALLOCATED_REQUIRES_CURATION"
    assert allocated[1]["unallocated_reason"] == "unknown_response"


def test_build_sample_allocation_cli_writes_reproducibility_bundle(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "timing_category", "response_label", "include_flag"],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "S1",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "include_flag": "true",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "S2",
                "timing_category": "pre-treatment",
                "response_label": "unknown",
                "include_flag": "false",
            },
        ],
    )
    out_dir = tmp_path / "spec_008"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )

    assert cmd_intake_build_sample_allocation(args) == 0

    allocation_rows = read_tsv(out_dir / "sample_allocation_matrix.tsv")
    unallocated_rows = read_tsv(out_dir / "unallocated_samples.tsv")
    assert len(allocation_rows) == 2
    assert len(unallocated_rows) == 1
    assert (out_dir / "reproducibility" / "commands.sh").exists()
    assert (out_dir / "reproducibility" / "environment.yml").exists()
    assert (out_dir / "reproducibility" / "checksums.sha256").exists()
    assert (out_dir / "treatment_delta_pair_audit.tsv").exists()
    assert (out_dir / "treatment_delta_pair_summary.tsv").exists()
    assert (out_dir / "curation_templates" / "unallocated_curation_template_index.tsv").exists()


def test_treatment_delta_pair_audit_explains_blockers() -> None:
    rows = [
        {
            "cohort_id": "cohort_a",
            "sample_id": "S1",
            "pair_id": "P1",
            "timing_category": "pre-treatment",
            "response_label": "responder",
        },
        {
            "cohort_id": "cohort_a",
            "sample_id": "S2",
            "pair_id": "P1",
            "timing_category": "post-treatment",
            "response_label": "responder",
        },
        {
            "cohort_id": "cohort_a",
            "sample_id": "S3",
            "pair_id": "P2",
            "timing_category": "pre-treatment",
            "response_label": "unknown",
        },
    ]

    audit_rows = build_treatment_delta_pair_audit(rows)

    assert audit_rows[0]["delta_pair_status"] == "eligible"
    assert audit_rows[1]["delta_pair_status"] == "blocked"
    assert audit_rows[1]["blocker_reason"] == "missing_or_conflicting_response"


def test_contrast_eligibility_uses_pre_include_filter_only() -> None:
    rows = []
    for idx, label in enumerate(["responder", "responder", "non_responder", "non_responder"], start=1):
        rows.append(
            {
                "cohort_id": "cohort_a",
                "sample_id": f"S{idx}",
                "timing_category": "post-treatment",
                "response_label": label,
                "include_flag": "false",
            }
        )

    assert is_contrast_eligible(rows, "POST_RESPONSE")
    assert not is_contrast_eligible(rows, "PRE_RESPONSE")


def _write_de_fixture(tmp_path: Path, timing: str, contrast: str) -> tuple[Namespace, Path]:
    cohort_id = f"cohort_{contrast.lower()}"
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / cohort_id
    cohort_dir.mkdir(parents=True)
    expr_path = cohort_dir / "expr.tsv"
    expr_path.write_text(
        "\n".join(
            [
                "gene_id\tS1\tS2\tS3\tS4",
                "CD274\t10\t11\t3\t4",
                "IFNG\t8\t9\t2\t3",
                "CXCL9\t7\t8\t1\t2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sample_manifest = tmp_path / f"{contrast.lower()}_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "include_flag",
            "input_class",
            "timing_category",
            "response_label",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
        ],
        rows=[
            {
                "cohort_id": cohort_id,
                "sample_id": "S1",
                "include_flag": "false",
                "input_class": "processed_matrix",
                "timing_category": timing,
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S2",
                "include_flag": "false",
                "input_class": "processed_matrix",
                "timing_category": timing,
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S3",
                "include_flag": "false",
                "input_class": "processed_matrix",
                "timing_category": timing,
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S4",
                "include_flag": "false",
                "input_class": "processed_matrix",
                "timing_category": timing,
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
        ],
    )
    expression_manifest = tmp_path / f"{contrast.lower()}_geo.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": cohort_id, "primary_expression_file": "expr.tsv"}],
    )
    registry_path = tmp_path / f"{contrast.lower()}_registry.tsv"
    out_dir = tmp_path / "de_out"
    args = Namespace(
        contrast=contrast,
        sample_manifest=str(sample_manifest),
        ingest_dir=str(tmp_path / "ingest"),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        count_method="deseq2",
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.0,
        max_unmapped_ensembl_fraction=1.0,
        max_duplicate_collapse_fraction=1.0,
        allow_weak_gene_mapping=True,
        comparison_registry=str(registry_path),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    return args, registry_path


def test_de_run_supports_post_response(tmp_path: Path) -> None:
    args, registry_path = _write_de_fixture(tmp_path, "post-treatment", "POST_RESPONSE")

    assert cmd_de_run(args) == 0

    registry_rows = read_tsv(registry_path)
    assert registry_rows[0]["analysis_type"] == "POST_RESPONSE"
    assert registry_rows[0]["n_group_A"] == "2"
    assert registry_rows[0]["n_group_B"] == "2"


def test_de_run_supports_on_response(tmp_path: Path) -> None:
    args, registry_path = _write_de_fixture(tmp_path, "on-treatment", "ON_RESPONSE")

    assert cmd_de_run(args) == 0

    registry_rows = read_tsv(registry_path)
    assert registry_rows[0]["analysis_type"] == "ON_RESPONSE"
    assert registry_rows[0]["n_group_A"] == "2"
    assert registry_rows[0]["n_group_B"] == "2"
