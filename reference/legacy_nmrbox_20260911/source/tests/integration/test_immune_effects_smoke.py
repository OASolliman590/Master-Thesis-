from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_immune_effects
from src.pipeline.common.io import read_tsv, write_tsv


def test_immune_effects_smoke_run(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "cohort_a"
    cohort_dir.mkdir(parents=True, exist_ok=True)

    expr_path = cohort_dir / "expr.tsv"
    expr_path.write_text(
        "\n".join(
            [
                "gene_id\ts1\ts2\ts3\ts4",
                "CD8A\t10\t12\t4\t3",
                "IFNG\t9\t11\t2\t2",
                "CXCL9\t8\t10\t1\t1",
                "CD274\t7\t9\t3\t2",
                "GENE_X\t5\t6\t4\t4",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": "cohort_a", "primary_expression_file": "expr.tsv"}],
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
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "s1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s3",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s4",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
            },
        ],
    )

    immune_dir = tmp_path / "immune_state"
    immune_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        immune_dir / "estimate_scores.tsv",
        fieldnames=[
            "cohort_id",
            "sample_id",
            "immune_score",
            "estimate_score",
        ],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "s1", "immune_score": "0.9", "estimate_score": "0.8"},
            {"cohort_id": "cohort_a", "sample_id": "s2", "immune_score": "0.7", "estimate_score": "0.6"},
            {"cohort_id": "cohort_a", "sample_id": "s3", "immune_score": "0.2", "estimate_score": "0.3"},
            {"cohort_id": "cohort_a", "sample_id": "s4", "immune_score": "0.1", "estimate_score": "0.2"},
        ],
    )

    out_dir = tmp_path / "immune_effects_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    args = Namespace(
        sample_manifest=str(sample_manifest),
        immune_dir=str(immune_dir),
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.60,
        max_unmapped_ensembl_fraction=0.20,
        max_duplicate_collapse_fraction=0.25,
        allow_weak_gene_mapping=False,
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_immune_effects(args) == 0

    marker_file = out_dir / "marker_correlations.tsv"
    effects_file = out_dir / "cohort_level_effects.tsv"
    assert marker_file.exists()
    assert effects_file.exists()
    assert len(read_tsv(marker_file)) > 0
    assert len(read_tsv(effects_file)) > 0


def test_immune_effects_emit_score_associations_when_expression_missing(tmp_path: Path) -> None:
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[
            {
                "cohort_id": "cohort_a",
                "primary_expression_file": "missing_expr.tsv",
                "downloads_folder": "cohort_a",
            }
        ],
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
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "s1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s3",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s4",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
            },
        ],
    )

    immune_dir = tmp_path / "immune_state"
    immune_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        immune_dir / "estimate_scores.tsv",
        fieldnames=["cohort_id", "sample_id", "immune_score", "estimate_score"],
        rows=[
            {"cohort_id": "cohort_a", "sample_id": "s1", "immune_score": "0.9", "estimate_score": "0.8"},
            {"cohort_id": "cohort_a", "sample_id": "s2", "immune_score": "0.7", "estimate_score": "0.6"},
            {"cohort_id": "cohort_a", "sample_id": "s3", "immune_score": "0.2", "estimate_score": "0.3"},
            {"cohort_id": "cohort_a", "sample_id": "s4", "immune_score": "0.1", "estimate_score": "0.2"},
        ],
    )
    write_tsv(
        immune_dir / "ssgsea_scores_long.tsv",
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_uid",
            "gene_set_id",
            "gene_set_name",
            "ssgsea_score",
            "gene_set_layer",
            "method",
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "s1",
                "patient_uid": "s1",
                "gene_set_id": "T_CELL_INFLAMED_GEP_18",
                "gene_set_name": "T_CELL_INFLAMED_GEP_18",
                "ssgsea_score": "0.8",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "method": "gsva_ssgsea_r",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s2",
                "patient_uid": "s2",
                "gene_set_id": "T_CELL_INFLAMED_GEP_18",
                "gene_set_name": "T_CELL_INFLAMED_GEP_18",
                "ssgsea_score": "0.7",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "method": "gsva_ssgsea_r",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s3",
                "patient_uid": "s3",
                "gene_set_id": "T_CELL_INFLAMED_GEP_18",
                "gene_set_name": "T_CELL_INFLAMED_GEP_18",
                "ssgsea_score": "0.2",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "method": "gsva_ssgsea_r",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "s4",
                "patient_uid": "s4",
                "gene_set_id": "T_CELL_INFLAMED_GEP_18",
                "gene_set_name": "T_CELL_INFLAMED_GEP_18",
                "ssgsea_score": "0.1",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "method": "gsva_ssgsea_r",
            },
        ],
    )
    write_tsv(
        immune_dir / "layer_summary.tsv",
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_uid",
            "gene_set_layer",
            "n_gene_sets_scored",
            "mean_score",
            "median_score",
            "method",
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": sample_id,
                "patient_uid": sample_id,
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "n_gene_sets_scored": "1",
                "mean_score": score,
                "median_score": score,
                "method": "ssgsea",
            }
            for sample_id, score in [("s1", "0.8"), ("s2", "0.7"), ("s3", "0.2"), ("s4", "0.1")]
        ],
    )

    out_dir = tmp_path / "immune_effects_out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        immune_dir=str(immune_dir),
        expression_manifest=str(expression_manifest),
        downloads_root=str(tmp_path / "missing_downloads"),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.60,
        max_unmapped_ensembl_fraction=0.20,
        max_duplicate_collapse_fraction=0.25,
        allow_weak_gene_mapping=True,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_immune_effects(args) == 0

    assert read_tsv(out_dir / "marker_correlations.tsv") == []
    effects = read_tsv(out_dir / "cohort_level_effects.tsv")
    assert {row["feature_source"] for row in effects} == {
        "estimate",
        "gsva_ssgsea",
        "ssgsea_layer_mean",
    }
    assert any(row["immune_feature"] == "T_CELL_INFLAMED_GEP_18" for row in effects)
    audit = read_tsv(out_dir / "immune_effects_input_audit.tsv")
    assert audit[0]["marker_correlation_status"] == "missing_expression"
