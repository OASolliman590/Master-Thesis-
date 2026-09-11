from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_retrieval_geo_manifest
from src.pipeline.common.io import read_tsv, write_tsv


def test_retrieval_geo_manifest_summarizes_downloaded_types(tmp_path: Path) -> None:
    discovery_manifest = tmp_path / "discovery.tsv"
    downloads_root = tmp_path / "downloads"
    out_file = tmp_path / "geo_data_type_manifest.tsv"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_manifest,
        fieldnames=["cohort_id", "accession"],
        rows=[
            {"cohort_id": "c1", "accession": "GSE100001; SRP100001"},
            {"cohort_id": "c2", "accession": "GSE200002"},
        ],
    )

    c1 = downloads_root / "c1"
    c1.mkdir(parents=True, exist_ok=True)
    (c1 / "GSE100001_family.soft.gz").write_text("soft", encoding="utf-8")
    (c1 / "SRP100001_runinfo.csv").write_text("Run,SampleName", encoding="utf-8")
    matrix_dir = c1 / "GSE100001" / "matrix"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    (matrix_dir / "GSE100001_series_matrix.txt.gz").write_text("matrix", encoding="utf-8")
    suppl_dir = c1 / "GSE100001" / "suppl"
    suppl_dir.mkdir(parents=True, exist_ok=True)
    (suppl_dir / "clinical_metadata.tsv").write_text("sample\tresponse", encoding="utf-8")

    c2 = downloads_root / "c2"
    c2.mkdir(parents=True, exist_ok=True)
    (c2 / "GSE200002_family.soft.gz").write_text("soft", encoding="utf-8")

    args = Namespace(
        discovery_manifest=str(discovery_manifest),
        downloads_root=str(downloads_root),
        out=str(out_file),
        run_manifest=str(run_manifest),
    )
    assert cmd_retrieval_geo_manifest(args) == 0

    rows = {row["cohort_id"]: row for row in read_tsv(out_file)}
    row1 = rows["c1"]
    row2 = rows["c2"]

    assert row1["geo_core_complete"] == "true"
    assert row1["n_soft_files"] == "1"
    assert row1["n_matrix_files"] == "1"
    assert row1["n_suppl_files"] == "1"
    assert row1["n_runinfo_files"] == "1"
    assert row1["inferred_data_mode"] == "processed_matrix_or_normalized_table"
    assert row1["recommended_input_route"] == "processed_matrix"

    assert row2["geo_core_complete"] == "true"
    assert row2["n_matrix_files"] == "0"
    assert row2["n_suppl_files"] == "0"
    assert row2["inferred_data_mode"] == "metadata_only"
    assert row2["recommended_input_route"] == "manual_fetch_additional_files"

