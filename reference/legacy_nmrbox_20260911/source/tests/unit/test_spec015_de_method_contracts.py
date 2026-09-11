from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import numpy as np

from src.pipeline.cli import cmd_de_run, cmd_signature_derive
from src.pipeline.common.io import read_tsv, write_tsv


def _write_treatment_delta_fixture(tmp_path: Path) -> Namespace:
    cohort_id = "cohort_delta"
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / cohort_id
    cohort_dir.mkdir(parents=True, exist_ok=True)
    expr_file = cohort_dir / "expr.tsv"
    expr_file.write_text(
        "\n".join(
            [
                "gene_id\tR1_PRE\tR1_POST\tR2_PRE\tR2_POST\tN1_PRE\tN1_POST\tN2_PRE\tN2_POST",
                "GENE1\t10\t20\t11\t21\t10\t12\t11\t13",
                "GENE2\t5\t7\t6\t8\t5\t5\t6\t6",
                "GENE3\t30\t35\t32\t36\t30\t32\t31\t33",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "pair_id",
            "include_flag",
            "input_class",
            "timing_category",
            "response_label",
            "cancer_type",
            "therapy_agent",
        ],
        rows=[
            {
                "cohort_id": cohort_id,
                "sample_id": "R1_PRE",
                "patient_id": "R1",
                "pair_id": "R1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "R1_POST",
                "patient_id": "R1",
                "pair_id": "R1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "post-treatment",
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "R2_PRE",
                "patient_id": "R2",
                "pair_id": "R2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "R2_POST",
                "patient_id": "R2",
                "pair_id": "R2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "post-treatment",
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "N1_PRE",
                "patient_id": "N1",
                "pair_id": "N1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "N1_POST",
                "patient_id": "N1",
                "pair_id": "N1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "post-treatment",
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "N2_PRE",
                "patient_id": "N2",
                "pair_id": "N2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "N2_POST",
                "patient_id": "N2",
                "pair_id": "N2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "post-treatment",
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            },
        ],
    )
    expression_manifest = tmp_path / "geo.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": cohort_id, "primary_expression_file": "expr.tsv"}],
    )
    return Namespace(
        contrast="TREATMENT_DELTA",
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
        allow_welch_fallback=True,
        comparison_registry=str(tmp_path / "comparison_registry.tsv"),
        out=str(tmp_path / "de_out"),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )


def test_de_treatment_delta_uses_delta_model_class_not_legacy_welch(tmp_path: Path) -> None:
    args = _write_treatment_delta_fixture(tmp_path)
    assert cmd_de_run(args) == 0

    rows = read_tsv(Path(args.out) / "TREATMENT_DELTA" / "cohort_delta.tsv")
    assert rows
    model_classes = {row.get("model_class", "") for row in rows}
    assert "welch_t_test_delta_interaction" not in model_classes
    assert all(mc.endswith("_delta") for mc in model_classes)
    repro_dir = Path(args.out) / "TREATMENT_DELTA" / "reproducibility"
    assert (repro_dir / "commands.sh").exists()
    assert (repro_dir / "environment.yml").exists()
    assert (repro_dir / "checksums.sha256").exists()


def test_signature_derive_marks_primary_unadjusted_and_secondary_adjusted(tmp_path: Path) -> None:
    primary_meta_dir = tmp_path / "meta_primary"
    adjusted_meta_dir = tmp_path / "meta_adjusted"
    primary_meta_dir.mkdir(parents=True, exist_ok=True)
    adjusted_meta_dir.mkdir(parents=True, exist_ok=True)

    write_tsv(
        primary_meta_dir / "meta_effects.tsv",
        fieldnames=[
            "gene_id",
            "original_gene_id",
            "gene_symbol",
            "meta_effect_random",
            "meta_fdr",
            "n_cohorts_contributed",
            "direction_consistency",
            "effect_scale",
            "effect_scale_status",
        ],
        rows=[
            {
                "gene_id": "GENE_PRIMARY",
                "original_gene_id": "GENE_PRIMARY",
                "gene_symbol": "GENE_PRIMARY",
                "meta_effect_random": "1.3",
                "meta_fdr": "0.01",
                "n_cohorts_contributed": "3",
                "direction_consistency": "1.0",
                "effect_scale": "common_log2_response_logfc",
                "effect_scale_status": "common_scale",
            }
        ],
    )
    write_tsv(
        adjusted_meta_dir / "meta_effects.tsv",
        fieldnames=[
            "gene_id",
            "original_gene_id",
            "gene_symbol",
            "meta_effect_random",
            "meta_fdr",
            "n_cohorts_contributed",
            "direction_consistency",
            "effect_scale",
            "effect_scale_status",
        ],
        rows=[
            {
                "gene_id": "GENE_ADJ",
                "original_gene_id": "GENE_ADJ",
                "gene_symbol": "GENE_ADJ",
                "meta_effect_random": "1.1",
                "meta_fdr": "0.03",
                "n_cohorts_contributed": "3",
                "direction_consistency": "0.9",
                "effect_scale": "common_log2_response_logfc",
                "effect_scale_status": "common_scale",
            }
        ],
    )

    out_dir = tmp_path / "signature"
    args = Namespace(
        contrast="PRE_RESPONSE",
        analysis_id="",
        run_root="",
        meta_dir=str(primary_meta_dir),
        composition_adjusted_meta_dir=str(adjusted_meta_dir),
        comparison_registry="",
        thresholds="configs/signature_thresholds.yaml",
        module_rules="configs/signature_module_rules.tsv",
        out=str(out_dir),
        min_meta_cohorts=2,
        allow_empty_signature=False,
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_signature_derive(args) == 0

    primary_rows = read_tsv(out_dir / "pre_response_signature_v1.tsv")
    assert primary_rows
    assert {row["signature_variant"] for row in primary_rows} == {"composition_unadjusted_primary"}

    secondary_rows = read_tsv(
        out_dir / "pre_response_signature_composition_adjusted_secondary.tsv"
    )
    assert secondary_rows
    assert {row["signature_variant"] for row in secondary_rows} == {"composition_adjusted_secondary"}


def test_de_multi_assay_routing_and_uniform_output_contract(tmp_path: Path, monkeypatch) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_specs = {
        "cohort_counts": {
            "assay_type": "raw_counts",
            "expr": [
                "gene_id\tR1\tR2\tN1\tN2",
                "GENE1\t50\t52\t30\t28",
                "GENE2\t80\t78\t40\t42",
            ],
        },
        "cohort_log": {
            "assay_type": "log_normalized",
            "expr": [
                "gene_id\tR1\tR2\tN1\tN2",
                "GENE1\t4.2\t4.1\t3.4\t3.3",
                "GENE2\t5.2\t5.0\t4.0\t4.1",
            ],
        },
        "cohort_micro": {
            "assay_type": "microarray_intensity",
            "expr": [
                "gene_id\tR1\tR2\tN1\tN2",
                "GENE1\t1.2\t1.1\t-0.2\t-0.3",
                "GENE2\t2.0\t2.2\t0.1\t0.0",
            ],
        },
        "cohort_methyl": {
            "assay_type": "methylation_beta",
            "expr": [
                "gene_id\tR1\tR2\tN1\tN2",
                "CG0001\t0.21\t0.19\t0.44\t0.43",
                "CG0002\t0.55\t0.52\t0.61\t0.63",
            ],
        },
        "cohort_unreadable": {
            "assay_type": "unreadable",
            "expr": [
                "gene_id\tR1\tR2\tN1\tN2",
                "X1\t1\t2\t3\t4",
                "X2\t4\t3\t2\t1",
            ],
        },
    }
    manifest_rows = []
    geo_rows = []
    for cohort_id, spec in cohort_specs.items():
        cohort_dir = downloads_root / cohort_id
        cohort_dir.mkdir(parents=True, exist_ok=True)
        (cohort_dir / "expr.tsv").write_text("\n".join(spec["expr"]) + "\n", encoding="utf-8")
        geo_rows.append({"cohort_id": cohort_id, "primary_expression_file": "expr.tsv", "downloads_folder": cohort_id})
        for sid, label in (("R1", "responder"), ("R2", "responder"), ("N1", "non_responder"), ("N2", "non_responder")):
            manifest_rows.append(
                {
                    "cohort_id": cohort_id,
                    "sample_id": sid,
                    "include_flag": "true",
                    "input_class": "raw_counts" if spec["assay_type"] == "raw_counts" else "processed_matrix",
                    "timing_category": "pre-treatment",
                    "response_label": label,
                    "assay_type": spec["assay_type"],
                    "cancer_type": "Melanoma",
                    "therapy_agent": "nivolumab",
                }
            )

    sample_manifest = tmp_path / "sample_manifest.tsv"
    expression_manifest = tmp_path / "expression_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "include_flag",
            "input_class",
            "timing_category",
            "response_label",
            "assay_type",
            "cancer_type",
            "therapy_agent",
        ],
        rows=manifest_rows,
    )
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=geo_rows,
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001, ARG001
        out_path = Path(cmd[cmd.index("--out") + 1])
        write_tsv(
            out_path,
            fieldnames=["gene_id", "log2fc", "se_or_stat", "p_value", "fdr"],
            rows=[
                {"gene_id": "GENE1", "log2fc": "1.0", "se_or_stat": "0.2", "p_value": "0.01", "fdr": "0.02"},
                {"gene_id": "GENE2", "log2fc": "0.5", "se_or_stat": "0.3", "p_value": "0.03", "fdr": "0.04"},
            ],
        )

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("subprocess.run", _fake_run)

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
        allow_welch_fallback=False,
        comparison_registry=str(tmp_path / "comparison_registry.tsv"),
        out=str(tmp_path / "de_out"),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_de_run(args) == 0

    base = Path(args.out) / "PRE_RESPONSE"
    count_rows = read_tsv(base / "cohort_counts.tsv")
    assert count_rows and {r["model_class"] for r in count_rows} == {"deseq2"}
    assert {r["normalization_method"] for r in count_rows} == {"raw_counts"}

    log_rows = read_tsv(base / "cohort_log.tsv")
    micro_rows = read_tsv(base / "cohort_micro.tsv")
    assert log_rows and {r["model_class"] for r in log_rows} == {"limma_trend"}
    assert micro_rows and {r["model_class"] for r in micro_rows} == {"limma_trend"}
    assert {r["normalization_method"] for r in log_rows} == {"as_is_log_scale"}
    assert {r["normalization_method"] for r in micro_rows} == {"as_is_log_scale"}

    for row in count_rows + log_rows + micro_rows:
        assert row["log2fc"] != ""
        assert row["se_or_stat"] != ""
        assert row["model_class"] != ""

    assert read_tsv(base / "cohort_methyl.tsv") == []
    assert read_tsv(base / "cohort_unreadable.tsv") == []


def test_small_n_welch_se_is_less_reliable_than_model_based_oracle_se() -> None:
    rng = np.random.default_rng(42)
    n_sim = 500
    n_case = 2
    n_ctrl = 2
    true_delta = 1.0
    sigma_case = 0.6
    sigma_ctrl = 0.6
    true_se = np.sqrt((sigma_case**2) / n_case + (sigma_ctrl**2) / n_ctrl)

    welch_ses = []
    for _ in range(n_sim):
        case = rng.normal(loc=true_delta, scale=sigma_case, size=n_case)
        ctrl = rng.normal(loc=0.0, scale=sigma_ctrl, size=n_ctrl)
        se = np.sqrt(np.var(case, ddof=1) / n_case + np.var(ctrl, ddof=1) / n_ctrl)
        welch_ses.append(se)
    welch_ses_arr = np.asarray(welch_ses, dtype=float)
    welch_mae = float(np.mean(np.abs(welch_ses_arr - true_se)))

    # "Model-based oracle" approximates moderated/model SE recovery target.
    oracle_ses = np.full(n_sim, true_se, dtype=float)
    oracle_mae = float(np.mean(np.abs(oracle_ses - true_se)))

    assert welch_mae > 0.08
    assert oracle_mae == 0.0
    assert welch_mae > oracle_mae


def test_de_emits_model_migration_report_with_baseline_comparison(tmp_path: Path) -> None:
    args = _write_treatment_delta_fixture(tmp_path)
    baseline_root = tmp_path / "baseline_de"
    baseline_file = baseline_root / "TREATMENT_DELTA" / "cohort_delta.tsv"
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        baseline_file,
        fieldnames=["gene_id", "model_class"],
        rows=[{"gene_id": "GENE1", "model_class": "legacy_model"}],
    )
    args.baseline_de_dir = str(baseline_root)

    assert cmd_de_run(args) == 0

    migration_file = Path(args.out) / "TREATMENT_DELTA" / "de_model_migration.md"
    assert migration_file.exists()
    migration_text = migration_file.read_text(encoding="utf-8")
    assert f"- baseline_output: {baseline_root}" in migration_text
    assert "| cohort_delta | completed |" in migration_text
    assert "| legacy_model | true |" in migration_text

    checksums_text = (
        Path(args.out) / "TREATMENT_DELTA" / "reproducibility" / "checksums.sha256"
    ).read_text(encoding="utf-8")
    assert str(migration_file) in checksums_text


def test_verified_counts_deseq2_output_is_byte_identical_across_baseline_reruns(
    tmp_path: Path, monkeypatch
) -> None:
    cohort_id = "cohort_counts_only"
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / cohort_id
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "expr.tsv").write_text(
        "\n".join(
            [
                "gene_id\tR1\tR2\tN1\tN2",
                "GENE1\t100\t120\t80\t70",
                "GENE2\t200\t190\t120\t110",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "include_flag",
            "input_class",
            "timing_category",
            "response_label",
            "assay_type",
            "cancer_type",
            "therapy_agent",
        ],
        rows=[
            {
                "cohort_id": cohort_id,
                "sample_id": sid,
                "include_flag": "true",
                "input_class": "raw_counts",
                "timing_category": "pre-treatment",
                "response_label": label,
                "assay_type": "raw_counts",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            }
            for sid, label in (
                ("R1", "responder"),
                ("R2", "responder"),
                ("N1", "non_responder"),
                ("N2", "non_responder"),
            )
        ],
    )
    expression_manifest = tmp_path / "expression_manifest.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[
            {
                "cohort_id": cohort_id,
                "primary_expression_file": "expr.tsv",
                "downloads_folder": cohort_id,
            }
        ],
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001, ARG001
        out_path = Path(cmd[cmd.index("--out") + 1])
        write_tsv(
            out_path,
            fieldnames=["gene_id", "log2fc", "se_or_stat", "p_value", "fdr"],
            rows=[
                {
                    "gene_id": "GENE1",
                    "log2fc": "0.9000",
                    "se_or_stat": "0.1200",
                    "p_value": "0.0100",
                    "fdr": "0.0200",
                },
                {
                    "gene_id": "GENE2",
                    "log2fc": "0.6000",
                    "se_or_stat": "0.1500",
                    "p_value": "0.0300",
                    "fdr": "0.0400",
                },
            ],
        )

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("subprocess.run", _fake_run)

    def _build_args(out_dir: Path, registry: Path, run_manifest: Path) -> Namespace:
        return Namespace(
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
            allow_welch_fallback=False,
            comparison_registry=str(registry),
            baseline_de_dir="",
            out=str(out_dir),
            run_manifest=str(run_manifest),
        )

    args_a = _build_args(tmp_path / "de_out_a", tmp_path / "registry_a.tsv", tmp_path / "logs/a.yaml")
    args_b = _build_args(tmp_path / "de_out_b", tmp_path / "registry_b.tsv", tmp_path / "logs/b.yaml")
    assert cmd_de_run(args_a) == 0
    assert cmd_de_run(args_b) == 0

    file_a = Path(args_a.out) / "PRE_RESPONSE" / f"{cohort_id}.tsv"
    file_b = Path(args_b.out) / "PRE_RESPONSE" / f"{cohort_id}.tsv"
    assert file_a.read_bytes() == file_b.read_bytes()
    rows = read_tsv(file_a)
    assert rows and {row["model_class"] for row in rows} == {"deseq2"}
