from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_visualize_run
from src.pipeline.common.io import read_tsv, write_tsv


def test_visualize_run_builds_extended_signature_immune_validation_tcga_panels(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "cohort_a"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "expr.tsv").write_text(
        "\n".join(
            [
                "gene_id\tR1\tR2\tN1\tN2",
                "GENE1\t12\t13\t5\t6",
                "GENE2\t8\t9\t4\t3",
                "GENE3\t20\t18\t12\t11",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "include_flag", "response_label", "timing_category"],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "R1", "include_flag": "true", "response_label": "responder", "timing_category": "pre-treatment"},
            {"cohort_id": "cohort_a", "sample_id": "R2", "include_flag": "true", "response_label": "responder", "timing_category": "pre-treatment"},
            {"cohort_id": "cohort_a", "sample_id": "N1", "include_flag": "true", "response_label": "non_responder", "timing_category": "pre-treatment"},
            {"cohort_id": "cohort_a", "sample_id": "N2", "include_flag": "true", "response_label": "non_responder", "timing_category": "pre-treatment"},
        ],
    )
    expression_manifest = tmp_path / "expression_manifest.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[{"cohort_id": "cohort_a", "primary_expression_file": "expr.tsv", "downloads_folder": "cohort_a"}],
    )

    de_dir = tmp_path / "de"
    (de_dir / "PRE_RESPONSE").mkdir(parents=True, exist_ok=True)
    write_tsv(
        de_dir / "PRE_RESPONSE" / "cohort_a.tsv",
        fieldnames=["gene_id", "log2fc", "p_value"],
        rows=[
            {"gene_id": "GENE1", "log2fc": "1.0", "p_value": "0.01"},
            {"gene_id": "GENE2", "log2fc": "-0.8", "p_value": "0.03"},
        ],
    )

    meta_dir = tmp_path / "meta"
    (meta_dir / "PRE_RESPONSE").mkdir(parents=True, exist_ok=True)
    write_tsv(
        meta_dir / "PRE_RESPONSE" / "meta_effects.tsv",
        fieldnames=["gene_id", "meta_effect", "meta_p_value"],
        rows=[
            {"gene_id": "GENE1", "meta_effect": "0.9", "meta_p_value": "0.02"},
            {"gene_id": "GENE2", "meta_effect": "-0.7", "meta_p_value": "0.04"},
        ],
    )

    immune_dir = tmp_path / "immune"
    immune_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        immune_dir / "ssgsea_scores.tsv",
        fieldnames=["cohort_id", "sample_id", "SET_A", "SET_B"],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "R1", "SET_A": "0.9", "SET_B": "0.4"},
            {"cohort_id": "cohort_a", "sample_id": "R2", "SET_A": "0.8", "SET_B": "0.5"},
            {"cohort_id": "cohort_a", "sample_id": "N1", "SET_A": "0.2", "SET_B": "0.7"},
            {"cohort_id": "cohort_a", "sample_id": "N2", "SET_A": "0.3", "SET_B": "0.6"},
        ],
    )
    write_tsv(
        immune_dir / "ssgsea_scores_long.tsv",
        fieldnames=["cohort_id", "sample_id", "gene_set_name", "gene_set_layer", "ssgsea_score"],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "R1", "gene_set_name": "SET_A", "gene_set_layer": "L1_ICB_PREDICTOR", "ssgsea_score": "0.9"},
            {"cohort_id": "cohort_a", "sample_id": "R2", "gene_set_name": "SET_A", "gene_set_layer": "L1_ICB_PREDICTOR", "ssgsea_score": "0.8"},
            {"cohort_id": "cohort_a", "sample_id": "N1", "gene_set_name": "SET_A", "gene_set_layer": "L1_ICB_PREDICTOR", "ssgsea_score": "0.2"},
            {"cohort_id": "cohort_a", "sample_id": "N2", "gene_set_name": "SET_A", "gene_set_layer": "L1_ICB_PREDICTOR", "ssgsea_score": "0.3"},
        ],
    )

    signature_file = tmp_path / "signature.tsv"
    write_tsv(
        signature_file,
        fieldnames=["gene_id", "signature_direction"],
        rows=[{"gene_id": "GENE1", "signature_direction": "up"}, {"gene_id": "GENE2", "signature_direction": "down"}],
    )

    validation_dir = tmp_path / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        validation_dir / "validation_concordance.tsv",
        fieldnames=["gene_id", "concordance_tier"],
        rows=[
            {"gene_id": "GENE1", "concordance_tier": "GOLD"},
            {"gene_id": "GENE2", "concordance_tier": "SILVER"},
            {"gene_id": "GENE3", "concordance_tier": "BRONZE"},
        ],
    )

    tcga_dir = tmp_path / "tcga_projection"
    tcga_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        tcga_dir / "TCGA-SKCM_survival_stats.tsv",
        fieldnames=["project", "hazard_ratio", "lower_95_ci", "upper_95_ci", "status"],
        rows=[{"project": "TCGA-SKCM", "hazard_ratio": "1.2", "lower_95_ci": "0.9", "upper_95_ci": "1.7", "status": "ok"}],
    )
    layer4_dir = tcga_dir / "thorsson_layer4"
    layer4_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        layer4_dir / "epigenetic_layer_tcga_validation.tsv",
        fieldnames=["gene_set", "tcga_project", "p_value", "fdr", "status"],
        rows=[{"gene_set": "PRC2_IMMUNE_TARGETS", "tcga_project": "TCGA-SKCM", "p_value": "0.001", "fdr": "0.02", "status": "ok"}],
    )

    out_dir = tmp_path / "viz_out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        de_dir=str(de_dir),
        meta_dir=str(meta_dir),
        immune_dir=str(immune_dir),
        signature_file=str(signature_file),
        validation_dir=str(validation_dir),
        tcga_dir=str(tcga_dir),
        ssgsea_heatmap_top_sets=10,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_visualize_run(args) == 0

    assert (out_dir / "signature" / "cohort_a_signature_heatmap.png").exists()
    assert (out_dir / "immune" / "l1_icb_predictor_r_vs_nr_box.png").exists()
    assert (out_dir / "validation" / "concordance_tier_bar.png").exists()
    assert (out_dir / "tcga" / "continuous_cox_hazard_ratios.png").exists()
    assert (out_dir / "tcga" / "thorsson_layer4_association.png").exists()

    index_rows = read_tsv(out_dir / "visualization_index.tsv")
    plot_types = {row.get("plot_type", "") for row in index_rows}
    assert "signature_heatmap" in plot_types
    assert "ssgsea_layer_box" in plot_types
    assert "concordance_tier_bar" in plot_types
    assert "tcga_continuous_cox" in plot_types
    assert "tcga_thorsson_association" in plot_types


def test_visualize_run_ignores_empty_optional_paths_without_reading_cwd(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "cohort_a"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "expr.tsv").write_text(
        "gene_id\tR1\tN1\nGENE1\t12\t5\nGENE2\t8\t4\n",
        encoding="utf-8",
    )

    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "include_flag", "response_label", "timing_category"],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "R1", "include_flag": "true", "response_label": "responder", "timing_category": "pre-treatment"},
            {"cohort_id": "cohort_a", "sample_id": "N1", "include_flag": "true", "response_label": "non_responder", "timing_category": "pre-treatment"},
        ],
    )
    expression_manifest = tmp_path / "expression_manifest.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[{"cohort_id": "cohort_a", "primary_expression_file": "expr.tsv", "downloads_folder": "cohort_a"}],
    )

    de_dir = tmp_path / "de"
    (de_dir / "PRE_RESPONSE").mkdir(parents=True, exist_ok=True)
    write_tsv(
        de_dir / "PRE_RESPONSE" / "cohort_a.tsv",
        fieldnames=["gene_id", "log2fc", "p_value"],
        rows=[{"gene_id": "GENE1", "log2fc": "1.0", "p_value": "0.01"}],
    )

    meta_dir = tmp_path / "meta"
    (meta_dir / "PRE_RESPONSE").mkdir(parents=True, exist_ok=True)
    write_tsv(
        meta_dir / "PRE_RESPONSE" / "meta_effects.tsv",
        fieldnames=["gene_id", "meta_effect", "meta_p_value"],
        rows=[{"gene_id": "GENE1", "meta_effect": "0.9", "meta_p_value": "0.02"}],
    )

    out_dir = tmp_path / "viz_out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        de_dir=str(de_dir),
        meta_dir=str(meta_dir),
        immune_dir="",
        signature_file="",
        validation_dir="",
        tcga_dir="",
        ssgsea_heatmap_top_sets=10,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_visualize_run(args) == 0
    assert (out_dir / "visualization_index.tsv").exists()
