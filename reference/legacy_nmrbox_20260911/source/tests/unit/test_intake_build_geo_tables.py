from __future__ import annotations

from argparse import Namespace
import gzip
from pathlib import Path

from src.pipeline.cli import cmd_intake_build_geo_tables
from src.pipeline.common.io import read_tsv, write_tsv


def _write_series_matrix(path: Path, *, with_expression: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "!Sample_geo_accession\tS1\tS2\n",
        "!series_matrix_table_begin\n",
    ]
    if with_expression:
        lines.extend(
            [
                "ID_REF\tS1\tS2\n",
                "GENE1\t1.0\t2.0\n",
                "GENE2\t3.0\t4.0\n",
            ]
        )
    lines.append("!series_matrix_table_end\n")
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.writelines(lines)


def test_intake_build_geo_tables_creates_unified_tables(tmp_path: Path) -> None:
    discovery_manifest = tmp_path / "discovery.tsv"
    routing_manifest = tmp_path / "routing.tsv"
    downloads_root = tmp_path / "downloads"
    out_root = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_manifest,
        fieldnames=["cohort_id", "accession", "cancer_type", "therapy_agent"],
        rows=[
            {
                "cohort_id": "c_raw",
                "accession": "GSE100001",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
            },
            {
                "cohort_id": "c_proc",
                "accession": "GSE200002",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-CTLA4",
            },
        ],
    )
    write_tsv(
        routing_manifest,
        fieldnames=["cohort_id", "recommended_input_route"],
        rows=[
            {"cohort_id": "c_raw", "recommended_input_route": "raw_counts_or_fastq_path"},
            {"cohort_id": "c_proc", "recommended_input_route": "processed_matrix"},
        ],
    )

    c_raw = downloads_root / "c_raw"
    c_proc = downloads_root / "c_proc"
    c_raw.mkdir(parents=True, exist_ok=True)
    c_proc.mkdir(parents=True, exist_ok=True)
    (c_raw / "GSE100001_family.soft.gz").write_text("dummy", encoding="utf-8")
    (c_proc / "GSE200002_family.soft.gz").write_text("dummy", encoding="utf-8")
    (c_raw / "GSE100001" / "suppl").mkdir(parents=True, exist_ok=True)
    (c_proc / "GSE200002" / "matrix").mkdir(parents=True, exist_ok=True)
    with gzip.open(c_raw / "GSE100001" / "suppl" / "GSE100001_raw_count.tsv.gz", "wt", encoding="utf-8") as handle:
        handle.write("gene\ts1\nGENE1\t10\nGENE2\t20\n")
    _write_series_matrix(
        c_proc / "GSE200002" / "matrix" / "GSE200002_series_matrix.txt.gz",
        with_expression=True,
    )

    args = Namespace(
        discovery_manifest=str(discovery_manifest),
        downloads_root=str(downloads_root),
        out=str(out_root),
        routing_manifest=str(routing_manifest),
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_tables(args) == 0

    all_rows = read_tsv(out_root / "cohort_input_table_all.tsv")
    assert len(all_rows) == 2
    by_cohort = {row["cohort_id"]: row for row in all_rows}
    assert by_cohort["c_raw"]["source_type_selected"] == "raw_counts"
    assert "raw_count" in by_cohort["c_raw"]["primary_expression_file"]
    assert by_cohort["c_proc"]["source_type_selected"] == "processed_matrix"
    assert "series_matrix" in by_cohort["c_proc"]["primary_expression_file"]


def test_intake_build_geo_tables_prefers_real_supplement_over_empty_series_matrix(
    tmp_path: Path,
) -> None:
    discovery_manifest = tmp_path / "discovery.tsv"
    routing_manifest = tmp_path / "routing.tsv"
    downloads_root = tmp_path / "downloads"
    out_root = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_manifest,
        fieldnames=["cohort_id", "accession", "cancer_type", "therapy_agent"],
        rows=[
            {
                "cohort_id": "gse91061",
                "accession": "GSE91061",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
            },
            {
                "cohort_id": "microarray_like",
                "accession": "GSE200002",
                "cancer_type": "Melanoma",
                "therapy_agent": "anti-PD1",
            },
            {
                "cohort_id": "fallback_proc",
                "accession": "GSE300003",
                "cancer_type": "NSCLC",
                "therapy_agent": "anti-PD1",
            },
        ],
    )
    write_tsv(
        routing_manifest,
        fieldnames=["cohort_id", "recommended_input_route"],
        rows=[
            {"cohort_id": "gse91061", "recommended_input_route": "processed_matrix"},
            {"cohort_id": "microarray_like", "recommended_input_route": "processed_matrix"},
            {"cohort_id": "fallback_proc", "recommended_input_route": "processed_matrix"},
        ],
    )

    rnaseq = downloads_root / "gse91061"
    rnaseq.mkdir(parents=True)
    (rnaseq / "GSE91061_family.soft.gz").write_text("dummy", encoding="utf-8")
    _write_series_matrix(
        rnaseq / "GSE91061" / "matrix" / "GSE91061_series_matrix.txt.gz",
        with_expression=False,
    )
    suppl = rnaseq / "GSE91061" / "suppl"
    suppl.mkdir(parents=True)
    with gzip.open(suppl / "GSE91061_hg19KnownGene.fpkm.csv.gz", "wt", encoding="utf-8") as handle:
        handle.write("gene,S1,S2\nCXCL11,4.1,7.2\nCXCR3,2.0,5.3\n")

    microarray = downloads_root / "microarray_like"
    microarray.mkdir(parents=True)
    (microarray / "GSE200002_family.soft.gz").write_text("dummy", encoding="utf-8")
    _write_series_matrix(
        microarray / "GSE200002" / "matrix" / "GSE200002_series_matrix.txt.gz",
        with_expression=True,
    )
    micro_suppl = microarray / "GSE200002" / "suppl"
    micro_suppl.mkdir(parents=True)
    with gzip.open(micro_suppl / "GSE200002_metadata_notes.txt.gz", "wt", encoding="utf-8") as handle:
        handle.write("sample\tnote\nS1\tbaseline\nS2\tbaseline\n")

    fallback = downloads_root / "fallback_proc"
    fallback.mkdir(parents=True)
    (fallback / "GSE300003_family.soft.gz").write_text("dummy", encoding="utf-8")
    _write_series_matrix(
        fallback / "GSE300003" / "matrix" / "GSE300003_series_matrix.txt.gz",
        with_expression=False,
    )
    fallback_suppl = fallback / "GSE300003" / "suppl"
    fallback_suppl.mkdir(parents=True)
    with gzip.open(fallback_suppl / "GSE300003_expression_table.csv.gz", "wt", encoding="utf-8") as handle:
        handle.write("gene,S1,S2\nGENE1,1.2,2.4\nGENE2,3.6,4.8\n")

    args = Namespace(
        discovery_manifest=str(discovery_manifest),
        downloads_root=str(downloads_root),
        out=str(out_root),
        routing_manifest=str(routing_manifest),
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_build_geo_tables(args) == 0

    rows = {row["cohort_id"]: row for row in read_tsv(out_root / "geo_tables_summary.tsv")}
    assert rows["gse91061"]["primary_expression_file"].endswith(
        "GSE91061/suppl/GSE91061_hg19KnownGene.fpkm.csv.gz"
    )
    assert rows["microarray_like"]["primary_expression_file"].endswith(
        "GSE200002/matrix/GSE200002_series_matrix.txt.gz"
    )
    assert rows["fallback_proc"]["primary_expression_file"].endswith(
        "GSE300003/suppl/GSE300003_expression_table.csv.gz"
    )

    candidates = read_tsv(out_root / "gse91061" / "expression_file_manifest.tsv")
    by_name = {row["file_name"]: row for row in candidates}
    assert by_name["GSE91061_hg19KnownGene.fpkm.csv.gz"]["load_validation_status"] == "loadable"

    fallback_candidates = read_tsv(out_root / "fallback_proc" / "expression_file_manifest.tsv")
    fallback_by_name = {row["file_name"]: row for row in fallback_candidates}
    assert fallback_by_name["GSE300003_series_matrix.txt.gz"]["load_validation_status"] == "empty_or_unreadable"
    assert fallback_by_name["GSE300003_expression_table.csv.gz"]["load_validation_status"] == "loadable"
