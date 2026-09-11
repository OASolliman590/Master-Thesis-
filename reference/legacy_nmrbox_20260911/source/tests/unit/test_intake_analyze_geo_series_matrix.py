from __future__ import annotations

import csv
import gzip
from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_intake_analyze_geo_series_matrix
from src.pipeline.common.io import read_tsv, write_tsv


def test_intake_analyze_geo_series_matrix_emits_csv_and_anchor_summary(tmp_path: Path) -> None:
    discovery_manifest = tmp_path / "discovery.tsv"
    downloads_root = tmp_path / "downloads"
    curation_sheet = tmp_path / "curation.tsv"
    out_dir = tmp_path / "out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        discovery_manifest,
        fieldnames=["cohort_id", "accession"],
        rows=[
            {"cohort_id": "c1", "accession": "GSE100001"},
            {"cohort_id": "c2", "accession": "GSE200002"},
        ],
    )
    write_tsv(
        curation_sheet,
        fieldnames=["cohort_id", "suggested_analysis_track", "manual_review_status", "pmid_candidates"],
        rows=[
            {
                "cohort_id": "c1",
                "suggested_analysis_track": "NSCLC_MULTIOMICS_COMPARATIVE",
                "manual_review_status": "pending_manual_review",
                "pmid_candidates": "12345678",
            }
        ],
    )

    c1_matrix = downloads_root / "c1" / "GSE100001" / "matrix" / "GSE100001_series_matrix.txt.gz"
    c1_matrix.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(c1_matrix, "wt", encoding="utf-8") as fh:
        fh.write('!Series_title\t"Study one"\n')
        fh.write('!Sample_title\t"PD1_01"\t"PD1_02"\n')
        fh.write('!Sample_geo_accession\t"GSM1"\t"GSM2"\n')
        fh.write('!Sample_source_name_ch1\t"Tumor tissue"\t"Tumor tissue"\n')
        fh.write('!Sample_characteristics_ch1\t"treatment: anti-PD1"\t"treatment: anti-PD1"\n')
        fh.write('!series_matrix_table_begin\n')
        fh.write("ID_REF\tGSM1\tGSM2\n")

    c2_matrix = downloads_root / "c2" / "GSE200002" / "matrix" / "GSE200002_series_matrix.txt.gz"
    c2_matrix.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(c2_matrix, "wt", encoding="utf-8") as fh:
        fh.write('!Series_title\t"Study two"\n')
        fh.write('!Sample_title\t"CT1"\t"CP1"\n')
        fh.write('!Sample_geo_accession\t"GSM3"\t"GSM4"\n')
        fh.write('!Sample_source_name_ch1\t"Tumor"\t"Nontumor"\n')
        fh.write('!Sample_characteristics_ch1\t"tissue: Tumor"\t"tissue: Nontumor"\n')
        fh.write('!series_matrix_table_begin\n')
        fh.write("ID_REF\tGSM3\tGSM4\n")

    args = Namespace(
        discovery_manifest=str(discovery_manifest),
        downloads_root=str(downloads_root),
        out=str(out_dir),
        curation_sheet=str(curation_sheet),
        run_manifest=str(run_manifest),
    )
    assert cmd_intake_analyze_geo_series_matrix(args) == 0

    summary_rows = {
        (row["cohort_id"], row["gse_id"]): row
        for row in read_tsv(out_dir / "matrix_annotation_summary.tsv")
    }
    assert summary_rows[("c1", "GSE100001")]["scientific_anchor_inferred"] == "treatment_exposed_unstratified"
    assert summary_rows[("c1", "GSE100001")]["scientific_anchor_final"] == "comparative_multiomics_nsclc"
    assert summary_rows[("c2", "GSE200002")]["scientific_anchor_final"] == "tumor_vs_adjacent_primary"

    with (out_dir / "c2" / "gse200002_series_matrix_txt" / "sample_annotations.csv").open(
        "r", encoding="utf-8", newline=""
    ) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["tissue"] == "Tumor"
    assert rows[1]["tissue"] == "Nontumor"
