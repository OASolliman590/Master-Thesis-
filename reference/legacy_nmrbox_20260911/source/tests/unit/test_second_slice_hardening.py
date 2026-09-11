from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_de_run, cmd_intake_gene_audit, cmd_validate_run
from src.pipeline.common.io import read_tsv, write_tsv


def test_intake_gene_audit_resolves_local_config_defaults(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"
    out_dir = tmp_path / "audit_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    cohort_id = "cohort_x"
    expr_rel = "expr.tsv"
    expr_file = downloads_root / cohort_id / expr_rel
    expr_file.parent.mkdir(parents=True, exist_ok=True)
    expr_file.write_text("gene_id\ts1\nENSG999999999999\t10\n", encoding="utf-8")

    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "include_flag", "sync_status", "input_class"],
        rows=[{"cohort_id": cohort_id, "sample_id": "s1", "include_flag": "true", "sync_status": "", "input_class": "raw_counts"}],
    )
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": cohort_id, "primary_expression_file": expr_rel}],
    )

    args = Namespace(
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        include_excluded=False,
        allow_stub_rows=False,
        strict=False,
        downloads_root=str(downloads_root),
        expression_manifest=str(expression_manifest),
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_gene_audit(args) == 0

    summary_rows = read_tsv(out_dir / "gene_id_audit_by_cohort.tsv")
    assert len(summary_rows) == 1
    assert summary_rows[0]["cohort_id"] == cohort_id
    assert summary_rows[0]["status"] == "fail"
    assert "min_hgnc_mapping_rate" in summary_rows[0]["fail_reason"]


def test_validate_run_inherits_upstream_readiness_language(tmp_path: Path) -> None:
    signature = tmp_path / "signature.tsv"
    out_dir = tmp_path / "validate_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    results_root = tmp_path / "results"
    results_root.mkdir(parents=True, exist_ok=True)

    write_tsv(signature, fieldnames=["gene_id"], rows=[])

    args = Namespace(
        signature=str(signature),
        validation_manifest="",
        results_root=str(results_root),
        contrast="PRE_RESPONSE",
        indirect_meta="",
        mega_results="",
        mega_concordance="",
        tcga_projection="",
        sample_manifest=str(tmp_path / "sample_manifest.tsv"),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_validate_run(args) == 0

    summary_rows = read_tsv(out_dir / "validation_concordance_summary.tsv")
    assert len(summary_rows) == 1
    row = summary_rows[0]
    assert row["status"] == "blocked_missing_indirect_meta"
    assert row["signature_readiness_status"] == "blocked"
    assert row["signature_readiness_reason"] == "empty_signature"
    assert row["upstream_meta_status"] == "blocked"
    assert row["upstream_meta_reason"] == "blocked_missing_indirect_meta"
    assert row["readiness_status"] == "blocked"
    assert row["readiness_reason"] == "upstream_signature_or_meta_blocked"

    readiness_rows = read_tsv(out_dir / "validation_readiness_status.tsv")
    by_stage = {r["stage"]: r for r in readiness_rows}
    assert by_stage["signature_upstream"]["status"] == "blocked"
    assert by_stage["signature_upstream"]["reason"] == "empty_signature"
    assert by_stage["meta_upstream"]["status"] == "blocked"
    assert by_stage["meta_upstream"]["reason"] == "blocked_missing_indirect_meta"
    assert by_stage["validation_concordance"]["status"] == "blocked"
    assert by_stage["validation_concordance"]["reason"] == "upstream_signature_or_meta_blocked"
    assert by_stage["external_validation"]["status"] == "missing"
    assert by_stage["external_validation"]["reason"] == "missing_external_holdout_evaluation"

    summary_md = (out_dir / "validation_summary.md").read_text(encoding="utf-8")
    assert "signature_readiness_status: blocked" in summary_md
    assert "upstream_meta_status: blocked" in summary_md
    assert "validation_readiness_status: blocked" in summary_md
    assert "external_validation_status: missing" in summary_md

    external_rows = read_tsv(out_dir / "validation_external_holdout.tsv")
    assert len(external_rows) == 1
    assert external_rows[0]["status"] == "missing"
    assert external_rows[0]["reason"] == "missing_external_holdout_evaluation"
    assert (out_dir / "robustness_concordance.tsv").exists()
    assert (out_dir / "robustness_concordance_summary.tsv").exists()
    assert (out_dir / "reproducibility" / "commands.sh").exists()
    assert (out_dir / "reproducibility" / "environment.yml").exists()
    assert (out_dir / "reproducibility" / "checksums.sha256").exists()


def test_validate_run_summarizes_external_holdout_metrics_when_provided(tmp_path: Path) -> None:
    signature = tmp_path / "signature.tsv"
    out_dir = tmp_path / "validate_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    heldout = tmp_path / "heldout.tsv"
    write_tsv(signature, fieldnames=["gene_id"], rows=[{"gene_id": "GENE1"}])
    write_tsv(
        heldout,
        fieldnames=["fold_id", "auc", "effect_concordance"],
        rows=[
            {"fold_id": "1", "auc": "0.71", "effect_concordance": "0.66"},
            {"fold_id": "2", "auc": "0.81", "effect_concordance": "0.74"},
        ],
    )

    args = Namespace(
        signature=str(signature),
        validation_manifest="",
        results_root="",
        contrast="PRE_RESPONSE",
        indirect_meta="",
        mega_results="",
        mega_concordance="",
        tcga_projection="",
        heldout_evaluation=str(heldout),
        sample_manifest=str(tmp_path / "sample_manifest.tsv"),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_validate_run(args) == 0

    readiness_rows = read_tsv(out_dir / "validation_readiness_status.tsv")
    by_stage = {r["stage"]: r for r in readiness_rows}
    assert by_stage["external_validation"]["status"] == "completed"
    assert by_stage["external_validation"]["reason"] == "external_holdout_evaluation_available"
    assert "rows=2" in by_stage["external_validation"]["detail"]

    external_rows = read_tsv(out_dir / "validation_external_holdout.tsv")
    assert external_rows[0]["status"] == "completed"
    assert external_rows[0]["n_rows"] == "2"
    assert external_rows[0]["n_valid_auc"] == "2"
    assert external_rows[0]["n_valid_effect_concordance"] == "2"
    assert external_rows[0]["auc_mean"] == "0.76"
    assert external_rows[0]["auc_min"] == "0.71"
    assert external_rows[0]["auc_max"] == "0.81"
    assert external_rows[0]["effect_concordance_mean"] == "0.7"
    assert external_rows[0]["effect_concordance_min"] == "0.66"
    assert external_rows[0]["effect_concordance_max"] == "0.74"

    summary_rows = read_tsv(out_dir / "validation_concordance_summary.tsv")
    assert summary_rows[0]["external_validation_status"] == "completed"
    assert summary_rows[0]["external_validation_reason"] == "external_holdout_evaluation_available"


def test_validate_run_uses_nested_loco_metrics_without_external_overclaim(tmp_path: Path) -> None:
    signature = tmp_path / "signature.tsv"
    results_root = tmp_path / "results"
    out_dir = tmp_path / "validate_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    meta_dir = results_root / "meta" / "PRE_RESPONSE"
    meta_dir.mkdir(parents=True, exist_ok=True)

    write_tsv(
        signature,
        fieldnames=["gene_id", "signature_direction"],
        rows=[
            {"gene_id": "GENE1", "signature_direction": "up"},
            {"gene_id": "GENE2", "signature_direction": "down"},
        ],
    )
    write_tsv(
        meta_dir / "meta_effects.tsv",
        fieldnames=["gene_id", "meta_effect_random", "meta_fdr"],
        rows=[
            {"gene_id": "GENE1", "meta_effect_random": "0.5", "meta_fdr": "0.01"},
            {"gene_id": "GENE2", "meta_effect_random": "-0.4", "meta_fdr": "0.02"},
        ],
    )
    write_tsv(
        meta_dir / "meta_leave_one_out_summary.tsv",
        fieldnames=[
            "gene_id",
            "analysis_id",
            "full_meta_effect_random",
            "full_meta_fdr",
            "n_loo_runs",
            "max_abs_delta_effect",
            "direction_flip_any",
            "loo_support_fraction",
            "signature_stability_label",
            "effect_scale_status",
            "common_effect_scale",
        ],
        rows=[
            {
                "gene_id": "GENE1",
                "analysis_id": "PRE_RESPONSE",
                "full_meta_effect_random": "0.5",
                "full_meta_fdr": "0.01",
                "n_loo_runs": "3",
                "max_abs_delta_effect": "0.05",
                "direction_flip_any": "false",
                "loo_support_fraction": "1.0",
                "signature_stability_label": "stable",
                "effect_scale_status": "common_scale",
                "common_effect_scale": "true",
            },
            {
                "gene_id": "GENE2",
                "analysis_id": "PRE_RESPONSE",
                "full_meta_effect_random": "-0.4",
                "full_meta_fdr": "0.02",
                "n_loo_runs": "3",
                "max_abs_delta_effect": "0.5",
                "direction_flip_any": "true",
                "loo_support_fraction": "0.5",
                "signature_stability_label": "unstable",
                "effect_scale_status": "common_scale",
                "common_effect_scale": "true",
            },
        ],
    )

    args = Namespace(
        signature=str(signature),
        validation_manifest="",
        results_root=str(results_root),
        contrast="PRE_RESPONSE",
        indirect_meta="",
        mega_results="",
        mega_concordance="",
        tcga_projection="",
        heldout_evaluation="",
        sample_manifest=str(tmp_path / "sample_manifest.tsv"),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_validate_run(args) == 0

    nested_rows = read_tsv(out_dir / "nested_loco_evaluation.tsv")
    assert len(nested_rows) == 2
    assert nested_rows[0]["evidence_scope"] == "internal_nested_loco_robustness"
    assert nested_rows[0]["robustness_pass"] == "true"
    assert nested_rows[1]["robustness_pass"] == "false"

    nested_summary = read_tsv(out_dir / "nested_loco_evaluation_summary.tsv")
    assert nested_summary[0]["status"] == "completed"
    assert nested_summary[0]["effect_concordance"] == "0.5"
    assert nested_summary[0]["stability_fraction"] == "0.5"

    readiness_rows = read_tsv(out_dir / "validation_readiness_status.tsv")
    by_stage = {r["stage"]: r for r in readiness_rows}
    assert by_stage["nested_loco_robustness"]["status"] == "completed"
    assert by_stage["meta_upstream"]["status"] == "completed"
    assert by_stage["meta_upstream"]["reason"] == "nested_loco_robustness_available"
    assert by_stage["validation_concordance"]["status"] == "completed"
    assert by_stage["external_validation"]["status"] == "missing"

    summary_md = (out_dir / "validation_summary.md").read_text(encoding="utf-8")
    assert "nested_loco_status: completed" in summary_md
    assert "external_validation_status: missing" in summary_md
    assert "internal nested LOCO robustness, not external validation" in summary_md


def test_validate_run_rejects_malformed_external_holdout_schema(tmp_path: Path) -> None:
    signature = tmp_path / "signature.tsv"
    out_dir = tmp_path / "validate_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    heldout = tmp_path / "heldout_bad.tsv"
    write_tsv(signature, fieldnames=["gene_id"], rows=[{"gene_id": "GENE1"}])
    write_tsv(
        heldout,
        fieldnames=["fold_id", "auc"],
        rows=[{"fold_id": "1", "auc": "0.71"}],
    )

    args = Namespace(
        signature=str(signature),
        validation_manifest="",
        results_root="",
        contrast="PRE_RESPONSE",
        indirect_meta="",
        mega_results="",
        mega_concordance="",
        tcga_projection="",
        heldout_evaluation=str(heldout),
        sample_manifest=str(tmp_path / "sample_manifest.tsv"),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    try:
        cmd_validate_run(args)
        assert False, "expected malformed heldout schema to raise RuntimeError"
    except RuntimeError as exc:
        assert "heldout evaluation contract requires columns" in str(exc)


def test_validate_run_rejects_out_of_range_external_holdout_metrics(tmp_path: Path) -> None:
    signature = tmp_path / "signature.tsv"
    out_dir = tmp_path / "validate_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    heldout = tmp_path / "heldout_bad_values.tsv"
    write_tsv(signature, fieldnames=["gene_id"], rows=[{"gene_id": "GENE1"}])
    write_tsv(
        heldout,
        fieldnames=["fold_id", "auc", "effect_concordance"],
        rows=[
            {"fold_id": "1", "auc": "1.2", "effect_concordance": "0.6"},
        ],
    )

    args = Namespace(
        signature=str(signature),
        validation_manifest="",
        results_root="",
        contrast="PRE_RESPONSE",
        indirect_meta="",
        mega_results="",
        mega_concordance="",
        tcga_projection="",
        heldout_evaluation=str(heldout),
        sample_manifest=str(tmp_path / "sample_manifest.tsv"),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    try:
        cmd_validate_run(args)
        assert False, "expected out-of-range heldout metrics to raise RuntimeError"
    except RuntimeError as exc:
        assert "heldout evaluation values must be in [0,1]" in str(exc)


def test_validate_run_rejects_external_holdout_without_numeric_metrics(tmp_path: Path) -> None:
    signature = tmp_path / "signature.tsv"
    out_dir = tmp_path / "validate_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    heldout = tmp_path / "heldout_non_numeric.tsv"
    write_tsv(signature, fieldnames=["gene_id"], rows=[{"gene_id": "GENE1"}])
    write_tsv(
        heldout,
        fieldnames=["fold_id", "auc", "effect_concordance"],
        rows=[
            {"fold_id": "1", "auc": "NA", "effect_concordance": ""},
            {"fold_id": "2", "auc": "", "effect_concordance": "nan"},
        ],
    )

    args = Namespace(
        signature=str(signature),
        validation_manifest="",
        results_root="",
        contrast="PRE_RESPONSE",
        indirect_meta="",
        mega_results="",
        mega_concordance="",
        tcga_projection="",
        heldout_evaluation=str(heldout),
        sample_manifest=str(tmp_path / "sample_manifest.tsv"),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    try:
        cmd_validate_run(args)
        assert False, "expected non-numeric heldout metrics to raise RuntimeError"
    except RuntimeError as exc:
        assert "heldout evaluation must provide at least one numeric auc and effect_concordance" in str(exc)


def test_de_run_accepts_capitalized_include_flag(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    out_dir = tmp_path / "de_out"

    cohort_id = "cohort_caps"
    expr_rel = "expr.tsv"
    expr_file = downloads_root / cohort_id / expr_rel
    expr_file.parent.mkdir(parents=True, exist_ok=True)
    expr_file.write_text(
        "\n".join(
            [
                "gene_id\tS1\tS2\tS3\tS4",
                "GENE1\t50\t45\t5\t4",
                "GENE2\t20\t22\t18\t17",
                "GENE3\t1\t2\t30\t29",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "include_flag",
            "timing_category",
            "response_label",
            "input_class",
        ],
        rows=[
            {
                "cohort_id": cohort_id,
                "sample_id": "S1",
                "include_flag": "True",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "input_class": "processed_matrix",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S2",
                "include_flag": "True",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "input_class": "processed_matrix",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S3",
                "include_flag": "True",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "input_class": "processed_matrix",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S4",
                "include_flag": "True",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "input_class": "processed_matrix",
            },
        ],
    )
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": cohort_id, "primary_expression_file": expr_rel}],
    )

    args = Namespace(
        contrast="PRE_RESPONSE",
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
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_de_run(args) == 0

    de_out = out_dir / "PRE_RESPONSE" / f"{cohort_id}.tsv"
    rows = read_tsv(de_out)
    assert len(rows) > 0
