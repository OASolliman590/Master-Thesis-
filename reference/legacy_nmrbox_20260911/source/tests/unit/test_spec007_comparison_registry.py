from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import _comparison_definition, _comparison_id, cmd_de_run
from src.pipeline.common.io import read_tsv, write_tsv


def _write_de_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    cohort_id = "cohort_registry"
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
            "cancer_type",
            "therapy_class",
            "therapy_agent",
        ],
        rows=[
            {
                "cohort_id": cohort_id,
                "sample_id": "S1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S3",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
            {
                "cohort_id": cohort_id,
                "sample_id": "S4",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
            },
        ],
    )
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": cohort_id, "primary_expression_file": "expr.tsv"}],
    )
    return sample_manifest, expression_manifest, downloads_root, tmp_path / "de_out"


def test_comparison_id_is_stable_and_sample_order_independent() -> None:
    definition_a = _comparison_definition(
        "PRE_RESPONSE",
        ["S2", "S1"],
        ["S4", "S3"],
        case_label="responder",
        control_label="non_responder",
    )
    definition_b = _comparison_definition(
        "PRE_RESPONSE",
        ["S1", "S2"],
        ["S3", "S4"],
        case_label="responder",
        control_label="non_responder",
    )

    assert definition_a == definition_b
    assert _comparison_id("cohort_registry", "PRE_RESPONSE", definition_a) == _comparison_id(
        "cohort_registry",
        "PRE_RESPONSE",
        definition_b,
    )


def test_de_run_writes_comparison_registry_and_comparison_id_column(tmp_path: Path) -> None:
    sample_manifest, expression_manifest, downloads_root, out_dir = _write_de_fixture(tmp_path)
    registry_path = tmp_path / "spec_007" / "comparison_registry.tsv"
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
        comparison_registry=str(registry_path),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )

    assert cmd_de_run(args) == 0

    registry_rows = read_tsv(registry_path)
    assert len(registry_rows) == 1
    registry = registry_rows[0]
    assert registry["analysis_type"] == "PRE_RESPONSE"
    assert registry["cohort_id"] == "cohort_registry"
    assert registry["drug_class"] == "PD1"
    assert registry["n_group_A"] == "2"
    assert registry["n_group_B"] == "2"
    assert registry["n_genes_tested"] == "3"

    de_rows = read_tsv(out_dir / "PRE_RESPONSE" / "cohort_registry.tsv")
    assert len(de_rows) == 3
    assert {row["comparison_id"] for row in de_rows} == {registry["comparison_id"]}
    assert registry["comparison_id"].startswith("cmp_")
