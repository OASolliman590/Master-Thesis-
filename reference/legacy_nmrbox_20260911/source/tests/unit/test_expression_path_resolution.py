from __future__ import annotations

from pathlib import Path

from src.pipeline.common.expression import resolve_primary_expression_path
from src.pipeline.common.io import write_tsv


def test_resolve_primary_expression_path_uses_downloads_folder_when_present(tmp_path: Path) -> None:
    manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"

    write_tsv(
        manifest,
        fieldnames=["cohort_id", "downloads_folder", "primary_expression_file"],
        rows=[
            {
                "cohort_id": "gse126044_srp183455_nsclc_pd1",
                "downloads_folder": "gse126044_non_small_cell_lung_cancer_anti_pd_1_n7_catA",
                "primary_expression_file": "GSE126044/suppl/GSE126044_counts.txt.gz",
            }
        ],
    )

    path = resolve_primary_expression_path(
        "gse126044_srp183455_nsclc_pd1",
        manifest,
        downloads_root,
    )
    assert path == (
        downloads_root
        / "gse126044_non_small_cell_lung_cancer_anti_pd_1_n7_catA"
        / "GSE126044/suppl/GSE126044_counts.txt.gz"
    )


def test_resolve_primary_expression_path_falls_back_to_cohort_id(tmp_path: Path) -> None:
    manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"

    write_tsv(
        manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[
            {
                "cohort_id": "cohort_a",
                "primary_expression_file": "expr.tsv",
            }
        ],
    )

    path = resolve_primary_expression_path("cohort_a", manifest, downloads_root)
    assert path == downloads_root / "cohort_a" / "expr.tsv"


def test_resolve_primary_expression_path_falls_back_to_downloads_root_relative_path(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"
    expected = downloads_root / "GSE202069/matrix/GSE202069_series_matrix.txt.gz"
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.write_text("dummy", encoding="utf-8")

    write_tsv(
        manifest,
        fieldnames=["cohort_id", "downloads_folder", "primary_expression_file"],
        rows=[
            {
                "cohort_id": "gse202069_hcc_anti_pd1",
                "downloads_folder": "stale_or_renamed_folder",
                "primary_expression_file": "GSE202069/matrix/GSE202069_series_matrix.txt.gz",
            }
        ],
    )

    path = resolve_primary_expression_path("gse202069_hcc_anti_pd1", manifest, downloads_root)
    assert path == expected


def test_resolve_primary_expression_path_falls_back_to_unique_basename_match(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"
    expected = (
        downloads_root
        / "gse202069_hepatocellular_carcinoma_anti_pd_1_n41_catB/GSE202069/matrix/GSE202069_series_matrix.txt.gz"
    )
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.write_text("dummy", encoding="utf-8")

    write_tsv(
        manifest,
        fieldnames=["cohort_id", "downloads_folder", "primary_expression_file"],
        rows=[
            {
                "cohort_id": "gse202069_hcc_anti_pd1",
                "downloads_folder": "incorrect_folder",
                "primary_expression_file": "missing/path/GSE202069_series_matrix.txt.gz",
            }
        ],
    )

    path = resolve_primary_expression_path("gse202069_hcc_anti_pd1", manifest, downloads_root)
    assert path == expected
