from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_immune_score
from src.pipeline.common.io import read_tsv, write_tsv


def test_immune_score_emits_wide_ssgsea_and_layer_summary(tmp_path: Path) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "cohort_immune"
    cohort_dir.mkdir(parents=True)
    (cohort_dir / "expr.tsv").write_text(
        "\n".join(
            [
                "gene_id\tS1\tS2\tS3",
                "CD274\t8\t4\t2",
                "CD8A\t7\t3\t1",
                "PDCD1\t6\t2\t1",
                "LAG3\t5\t2\t1",
                "BRD4\t3\t6\t8",
                "EZH2\t2\t5\t7",
                "IFNG\t9\t4\t1",
                "CXCL9\t8\t3\t1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": "cohort_immune", "primary_expression_file": "expr.tsv"}],
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "include_flag",
            "input_class",
            "timing_category",
            "response_label",
        ],
        rows=[
            {
                "cohort_id": "cohort_immune",
                "sample_id": "S1",
                "patient_id": "P1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
            },
            {
                "cohort_id": "cohort_immune",
                "sample_id": "S2",
                "patient_id": "P2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
            },
            {
                "cohort_id": "cohort_immune",
                "sample_id": "S3",
                "patient_id": "P3",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
            },
        ],
    )

    gmt = tmp_path / "test_layers.gmt"
    gmt.write_text(
        "\n".join(
            [
                "ICB_SET\tICB genes\tCD274\tCD8A\tIFNG\tCXCL9",
                "EXHAUSTION_SET\tExhaustion genes\tPDCD1\tLAG3\tCD274",
                "EPIGENETIC_SET\tEpigenetic genes\tBRD4\tEZH2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    registry = tmp_path / "immune_gene_sets_registry.tsv"
    write_tsv(
        registry,
        fieldnames=[
            "gene_set_id",
            "gene_set_layer",
            "gene_set_name",
            "gmt_path",
            "source",
            "enabled",
            "notes",
        ],
        rows=[
            {
                "gene_set_id": "ICB_SET",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "gene_set_name": "ICB set",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            },
            {
                "gene_set_id": "EXHAUSTION_SET",
                "gene_set_layer": "L2_C7_EXHAUSTION",
                "gene_set_name": "Exhaustion set",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            },
            {
                "gene_set_id": "EPIGENETIC_SET",
                "gene_set_layer": "L4_EPIGENETIC",
                "gene_set_name": "Epigenetic set",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            },
        ],
    )

    out_dir = tmp_path / "immune_state"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        ingest_dir="",
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        gene_set_registry=str(registry),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.0,
        max_unmapped_ensembl_fraction=1.0,
        max_duplicate_collapse_fraction=1.0,
        allow_weak_gene_mapping=True,
        skip_backend_check=True,
        legacy_rank_mean=False,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_immune_score(args) == 0

    wide = read_tsv(out_dir / "ssgsea_scores.tsv")
    assert len(wide) == 3
    assert {"cohort_id", "sample_id", "patient_uid", "ICB_SET", "EXHAUSTION_SET", "EPIGENETIC_SET"}.issubset(
        set(wide[0])
    )
    assert float(wide[0]["ICB_SET"]) > float(wide[2]["ICB_SET"])

    long_rows = read_tsv(out_dir / "ssgsea_scores_long.tsv")
    assert any(row["method"] == "gsva_ssgsea_r" for row in long_rows)

    layer_rows = read_tsv(out_dir / "layer_summary.tsv")
    assert any(row["gene_set_layer"] == "L4_EPIGENETIC" for row in layer_rows)
    assert all(row["method"] == "ssgsea" for row in layer_rows)

    estimate_rows = read_tsv(out_dir / "estimate_scores.tsv")
    assert estimate_rows[0]["score_scale"] == "ESTIMATE_real_or_na"
