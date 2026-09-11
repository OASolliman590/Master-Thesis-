from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from src.pipeline.cli import cmd_meta_run
from src.pipeline.common.io import read_tsv, write_tsv


def _write_de(path: Path, rows: list[dict[str, str]]) -> None:
    write_tsv(
        path,
        fieldnames=[
            "comparison_id",
            "gene_id",
            "original_gene_id",
            "gene_symbol",
            "log2fc",
            "se_or_stat",
            "p_value",
            "fdr",
            "mean_expression",
            "contrast_family",
            "n_case",
            "n_control",
            "model_class",
            "normalization_method",
        ],
        rows=rows,
    )


def test_meta_run_emits_i2_loco_fields_and_subgroups(tmp_path: Path) -> None:
    de_root = tmp_path / "de"
    contrast_dir = de_root / "PRE_RESPONSE"
    contrast_dir.mkdir(parents=True)
    common_a = {
        "comparison_id": "cmp_a",
        "original_gene_id": "GENE1",
        "gene_symbol": "GENE1",
        "p_value": "0.5",
        "fdr": "0.1",
        "mean_expression": "5",
        "contrast_family": "PRE_RESPONSE",
        "n_case": "2",
        "n_control": "2",
        "model_class": "welch_t_test_log2",
        "normalization_method": "log2",
    }
    common_b = dict(common_a)
    common_b["comparison_id"] = "cmp_b"
    common_c = dict(common_a)
    common_c["comparison_id"] = "cmp_c"
    _write_de(
        contrast_dir / "cohort_a.tsv",
        [
            {**common_a, "gene_id": "GENE1", "log2fc": "0.1", "se_or_stat": "0.5"},
            {**common_a, "gene_id": "GENE2", "original_gene_id": "GENE2", "gene_symbol": "GENE2", "log2fc": "0.2", "se_or_stat": "0.4"},
        ],
    )
    _write_de(
        contrast_dir / "cohort_b.tsv",
        [
            {**common_b, "gene_id": "GENE1", "log2fc": "0.2", "se_or_stat": "0.5"},
            {**common_b, "gene_id": "GENE2", "original_gene_id": "GENE2", "gene_symbol": "GENE2", "log2fc": "0.3", "se_or_stat": "0.4"},
        ],
    )
    _write_de(
        contrast_dir / "cohort_c.tsv",
        [
            {**common_c, "gene_id": "GENE1", "log2fc": "-0.1", "se_or_stat": "0.5"},
            {**common_c, "gene_id": "GENE2", "original_gene_id": "GENE2", "gene_symbol": "GENE2", "log2fc": "0.4", "se_or_stat": "0.4"},
        ],
    )

    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "include_flag",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
        ],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "A1", "patient_id": "PA1", "include_flag": "true", "cancer_type": "Melanoma", "therapy_class": "PD-1", "therapy_agent": "nivolumab"},
            {"cohort_id": "cohort_a", "sample_id": "A2", "patient_id": "PA2", "include_flag": "true", "cancer_type": "Melanoma", "therapy_class": "PD-1", "therapy_agent": "nivolumab"},
            {"cohort_id": "cohort_b", "sample_id": "B1", "patient_id": "PB1", "include_flag": "true", "cancer_type": "Melanoma", "therapy_class": "PD-1", "therapy_agent": "nivolumab"},
            {"cohort_id": "cohort_b", "sample_id": "B2", "patient_id": "PB2", "include_flag": "true", "cancer_type": "Melanoma", "therapy_class": "PD-1", "therapy_agent": "nivolumab"},
            {"cohort_id": "cohort_c", "sample_id": "C1", "patient_id": "PC1", "include_flag": "true", "cancer_type": "NSCLC", "therapy_class": "PD-L1", "therapy_agent": "durvalumab"},
            {"cohort_id": "cohort_c", "sample_id": "C2", "patient_id": "PC2", "include_flag": "true", "cancer_type": "NSCLC", "therapy_class": "PD-L1", "therapy_agent": "durvalumab"},
        ],
    )

    out_dir = tmp_path / "meta"
    args = Namespace(
        contrast="PRE_RESPONSE",
        de_dir=str(de_root),
        sample_manifest=str(sample_manifest),
        comparison_registry="",
        skip_forest_plots=True,
        include_k1_genes=False,
        enable_subgroups=True,
        knapp_hartung=False,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_meta_run(args) == 0

    meta_rows = {row["gene_id"]: row for row in read_tsv(out_dir / "PRE_RESPONSE" / "meta_effects.tsv")}
    assert "i2" in meta_rows["GENE1"]
    assert 0.0 <= float(meta_rows["GENE1"]["i2"]) <= 100.0
    assert meta_rows["GENE1"]["n_patients_contributed"] == "6"
    assert "loco_max_delta_padj" in meta_rows["GENE1"]
    assert meta_rows["GENE1"]["loco_unstable"] in {"true", "false"}
    assert meta_rows["GENE1"]["effect_scale"] == "common_log2_response_logfc"
    assert meta_rows["GENE1"]["effect_scale_status"] == "common_scale"
    assert meta_rows["GENE1"]["effect_unit"] == "log2_fold_change"
    assert meta_rows["GENE1"]["effect_direction_definition"] == "responder_minus_non_responder"
    assert meta_rows["GENE1"]["effect_reference_group"] == "non_responder"
    assert meta_rows["GENE1"]["common_effect_scale"] == "true"

    loo_summary = read_tsv(out_dir / "PRE_RESPONSE" / "meta_leave_one_out_summary.tsv")
    assert any(row["gene_id"] == "GENE1" and row["n_loo_runs"] == "3" for row in loo_summary)
    assert all(row["common_effect_scale"] == "true" for row in loo_summary)

    melanoma = out_dir / "PRE_RESPONSE" / "subgroups" / "by_cancer_type" / "melanoma.tsv"
    pd1 = out_dir / "PRE_RESPONSE" / "subgroups" / "by_drug_class" / "PD1.tsv"
    assert melanoma.exists()
    assert pd1.exists()
    subgroup_row = read_tsv(melanoma)[0]
    assert subgroup_row["subgroup_type"] == "cancer_type"
    assert "i2" in subgroup_row
    assert "n_patients_contributed" in subgroup_row
    assert subgroup_row["effect_scale_status"] == "common_scale"


def test_meta_run_blocks_non_contract_normalization_scale(tmp_path: Path) -> None:
    de_root = tmp_path / "de"
    contrast_dir = de_root / "PRE_RESPONSE"
    contrast_dir.mkdir(parents=True)
    _write_de(
        contrast_dir / "cohort_a.tsv",
        [
            {
                "comparison_id": "cmp_a",
                "gene_id": "GENE1",
                "original_gene_id": "GENE1",
                "gene_symbol": "GENE1",
                "log2fc": "0.3",
                "se_or_stat": "0.2",
                "p_value": "0.01",
                "fdr": "0.05",
                "mean_expression": "5",
                "contrast_family": "PRE_RESPONSE",
                "n_case": "3",
                "n_control": "3",
                "model_class": "limma_trend",
                "normalization_method": "non_log_unknown_scale",
            }
        ],
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "patient_id", "include_flag", "cancer_type", "therapy_agent"],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "A1",
                "patient_id": "PA1",
                "include_flag": "true",
                "cancer_type": "Melanoma",
                "therapy_agent": "nivolumab",
            }
        ],
    )
    args = Namespace(
        contrast="PRE_RESPONSE",
        de_dir=str(de_root),
        sample_manifest=str(sample_manifest),
        comparison_registry="",
        skip_forest_plots=True,
        include_k1_genes=False,
        enable_subgroups=False,
        knapp_hartung=False,
        out=str(tmp_path / "meta"),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    with pytest.raises(RuntimeError, match="common-scale input guard"):
        cmd_meta_run(args)


def test_meta_run_emits_k1_exclusions_file(tmp_path: Path) -> None:
    de_root = tmp_path / "de"
    contrast_dir = de_root / "PRE_RESPONSE"
    contrast_dir.mkdir(parents=True)
    _write_de(
        contrast_dir / "cohort_a.tsv",
        [
            {
                "comparison_id": "cmp_a",
                "gene_id": "GENE_SHARED",
                "original_gene_id": "GENE_SHARED",
                "gene_symbol": "GENE_SHARED",
                "log2fc": "0.3",
                "se_or_stat": "0.2",
                "p_value": "0.05",
                "fdr": "0.1",
                "mean_expression": "5",
                "contrast_family": "PRE_RESPONSE",
                "n_case": "2",
                "n_control": "2",
                "model_class": "limma_trend",
                "normalization_method": "log2(x+1)",
            },
            {
                "comparison_id": "cmp_a",
                "gene_id": "GENE_K1_ONLY",
                "original_gene_id": "GENE_K1_ONLY",
                "gene_symbol": "GENE_K1_ONLY",
                "log2fc": "0.7",
                "se_or_stat": "0.3",
                "p_value": "0.03",
                "fdr": "0.08",
                "mean_expression": "4",
                "contrast_family": "PRE_RESPONSE",
                "n_case": "2",
                "n_control": "2",
                "model_class": "limma_trend",
                "normalization_method": "log2(x+1)",
            },
        ],
    )
    _write_de(
        contrast_dir / "cohort_b.tsv",
        [
            {
                "comparison_id": "cmp_b",
                "gene_id": "GENE_SHARED",
                "original_gene_id": "GENE_SHARED",
                "gene_symbol": "GENE_SHARED",
                "log2fc": "0.4",
                "se_or_stat": "0.2",
                "p_value": "0.04",
                "fdr": "0.09",
                "mean_expression": "5",
                "contrast_family": "PRE_RESPONSE",
                "n_case": "2",
                "n_control": "2",
                "model_class": "limma_trend",
                "normalization_method": "log2(x+1)",
            },
        ],
    )

    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "patient_id", "include_flag", "cancer_type", "therapy_agent"],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "A1", "patient_id": "PA1", "include_flag": "true", "cancer_type": "Melanoma", "therapy_agent": "nivolumab"},
            {"cohort_id": "cohort_b", "sample_id": "B1", "patient_id": "PB1", "include_flag": "true", "cancer_type": "NSCLC", "therapy_agent": "durvalumab"},
        ],
    )
    args = Namespace(
        contrast="PRE_RESPONSE",
        de_dir=str(de_root),
        sample_manifest=str(sample_manifest),
        comparison_registry="",
        skip_forest_plots=True,
        include_k1_genes=False,
        enable_subgroups=False,
        knapp_hartung=False,
        out=str(tmp_path / "meta"),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_meta_run(args) == 0

    pooled_rows = {row["gene_id"] for row in read_tsv(tmp_path / "meta" / "PRE_RESPONSE" / "meta_effects.tsv")}
    assert "GENE_K1_ONLY" not in pooled_rows
    k1_rows = read_tsv(tmp_path / "meta" / "PRE_RESPONSE" / "meta_single_cohort.tsv")
    assert any(
        row["gene_id"] == "GENE_K1_ONLY"
        and row["meta_basis"] == "single_cohort"
        and row["status"] == "excluded_from_pooled_fdr"
        and row["common_effect_scale"] == "true"
        for row in k1_rows
    )
