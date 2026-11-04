from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.requires_r
def test_lin_two_layer_seurat_pseudobulk_preserves_missing_genes(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    result = run_r(
        ROOT / "r/scripts/sc_lin_synthetic_selftest.R",
        {},
        {"expected_outputs": ["synthetic_seurat.qs2", "metadata.rds", "cohort_map.tsv", "compartment_map.tsv", "panel_membership.tsv", "checks.json"]},
        tmp_path / "lin_two_layer_fixture",
    )
    checks = json.loads(result.outputs["checks.json"].read_text())
    assert checks["two_count_layers"] is True
    assert checks["weighted_layer_markers"] is True
    assert checks["cross_layer_patient_profile"] is True

    compartments = ("t_nk", "b_plasma", "myeloid", "fibroblast_stromal", "endothelial", "malignant_epithelial")
    expected_outputs = [
        *[f"expression__{slug}.tsv" for slug in compartments],
        *[f"clinical__{slug}.tsv" for slug in compartments],
        "compartment_qc.tsv", "gene_coverage.tsv", "data_quality.tsv", "compartment_expression.tsv",
        "pcahawley_per_patient_expression.tsv", "labels_markers.tsv",
        "labels_dotplot.png", "compartment_dotplot.png",
    ]
    source_path = result.outputs["synthetic_seurat.qs2"]
    metadata_path = result.outputs["metadata.rds"]
    analysis = run_r(
        ROOT / "r/scripts/sc_lin_pseudobulk.R",
        {
            "seurat": result.outputs["synthetic_seurat.qs2"],
            "metadata": result.outputs["metadata.rds"],
            "cohort_map": result.outputs["cohort_map.tsv"],
            "compartment_map": result.outputs["compartment_map.tsv"],
            "panels": result.outputs["panel_membership.tsv"],
        },
        {"expected_outputs": expected_outputs, "mode": "pseudobulk", "minimum_cells": 15,
         "minimum_umis": 5_000, "minimum_donors_to_show": 5,
         "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
         "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest()},
        tmp_path / "lin_pseudobulk_result",
    )
    assert analysis.outputs["expression__t_nk.tsv"].is_file()
    with analysis.outputs["clinical__t_nk.tsv"].open(newline="") as stream:
        clinical = {row["patient_id"]: row for row in csv.DictReader(stream, delimiter="\t")}
    with analysis.outputs["expression__t_nk.tsv"].open(newline="") as stream:
        expression = {row["gene"]: row for row in csv.DictReader(stream, delimiter="\t")}
    with analysis.outputs["labels_markers.tsv"].open(newline="") as stream:
        marker_rows = list(csv.DictReader(stream, delimiter="\t"))

    eligible = clinical["synthetic_a"]["profile_id"]
    below_threshold = clinical["synthetic_b"]["profile_id"]
    other_layer = clinical["synthetic_c"]["profile_id"]
    invalid_raw_counts = clinical["synthetic_bad"]["profile_id"]
    merged_layers = clinical["synthetic_merge"]["profile_id"]
    assert expression["GENEA"][eligible] == "3750"
    assert expression["GENEB"][eligible] == "3750"
    assert expression["GENEA"][below_threshold] == "NA"
    assert expression["GENEB"][below_threshold] == "NA"
    assert expression["GENEC"][eligible] == "NA"
    assert expression["GENEA"][other_layer] == "NA"
    assert expression["GENEB"][invalid_raw_counts] == "NA"
    assert expression["GENEC"][invalid_raw_counts] == "NA"
    assert clinical["synthetic_b"]["status"] == "below_umi_threshold"
    assert clinical["synthetic_bad"]["status"] == "invalid_raw_counts"
    assert clinical["synthetic_bad"]["reason"] == "non_integer_or_invalid_raw_counts"
    assert clinical["synthetic_merge"]["n_cells"] == "16"
    assert clinical["synthetic_merge"]["total_umis"] == "8160"
    assert clinical["synthetic_merge"]["status"] == "eligible"
    assert expression["GENEB"][merged_layers] == "4000"
    assert expression["GENEA"][merged_layers] == "NA"
    assert expression["GENEC"][merged_layers] == "NA"
    assert clinical["synthetic_a"]["fraction_cells_total"] == "0.5"
    with analysis.outputs["gene_coverage.tsv"].open(newline="") as stream:
        coverage = list(csv.DictReader(stream, delimiter="\t"))
    assert any(row["gene"] == "GENEA" and row["present"] == "FALSE" for row in coverage)
    with analysis.outputs["data_quality.tsv"].open(newline="") as stream:
        quality = list(csv.DictReader(stream, delimiter="\t"))
    assert all(row["fractional_values"] == "0" for row in quality)
    cd3d = [row for row in marker_rows if row["author_label"] == "CD8+T" and row["gene"] == "CD3D"]
    assert len(cd3d) == 1
    assert cd3d[0]["n_cells"] == "76"
    assert cd3d[0]["percent_cells_detected"] == "100"

    with analysis.outputs["pcahawley_per_patient_expression.tsv"].open(newline="") as stream:
        patient_rows = list(csv.DictReader(stream, delimiter="\t"))
    assert {row["patient_id"] for row in patient_rows} == {
        "synthetic_a", "synthetic_b", "synthetic_c", "synthetic_bad", "synthetic_merge"
    }
    assert "median_log2_cpm_plus1" not in patient_rows[0]
    assert all(row["detection_limit_tag"] in {
        "below_scRNA_detection_limit", "measured_at_or_above_detection_limit", "not_assessed"
    } for row in patient_rows)
