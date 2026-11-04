from __future__ import annotations

import csv
import gzip
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_meta.features import (
    FeatureTable,
    build_feature_table,
    external_feature_table,
    read_feature_table,
    write_feature_table,
)


def _write_matrix(path: Path, header, rows):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *header])
        writer.writerows(rows)


def _view(path, *, platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol", labels=()):
    return SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            cancer="melanoma",
            representation=SimpleNamespace(
                platform=platform, unit=unit, transform=transform, feature_id=feature_id
            ),
            endpoint_families=("orr",),
        ),
        expression_path=path,
        clinical_rows=[{"raw_orr": label} for label in labels],
    )


def test_linear_rnaseq_is_log2_tpm_plus_one_without_merging_studies(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(path, ["0", "1"], [["GENE_X", 3, 7]])

    table = build_feature_table(_view(path, labels=["CR", "SD"]), "gene")

    assert table.unit_family == "gene"
    assert table.records == [
        {"patient_row": 0, "unit": "GENE_X", "value": 2.0, "unit_family": "gene"},
        {"patient_row": 1, "unit": "GENE_X", "value": 3.0, "unit_family": "gene"},
    ]
    assert table.metadata["scale_rule"] == "log2(TPM+1)"


def test_integer_counts_without_lengths_are_log2_cpm_plus_one(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(path, ["0", "1"], [["GENE_X", 1, 1], ["GENE_Y", 3, 9]])

    table = build_feature_table(
        _view(path, unit="counts", labels=["CR", "SD"]), "gene"
    )
    values = {(row["unit"], row["patient_row"]): row["value"] for row in table.records}

    assert values[("GENE_X", 0)] == pytest.approx(math.log2(250_001))
    assert values[("GENE_X", 1)] == pytest.approx(math.log2(100_001))
    assert table.metadata["scale_rule"] == "log2(CPM+1)"


def test_recount3_counts_with_gtf_lengths_are_converted_to_log2_tpm_plus_one(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(path, ["0", "1"], [["ENSG000001", 10, 10], ["ENSG000002", 10, 30]])
    gtf_path = tmp_path / "tiny.gtf.gz"
    with gzip.open(gtf_path, "wt", encoding="utf-8") as stream:
        stream.write(
            'chr1\t.\tgene\t1\t1000\t1000\t+\t.\tgene_id "ENSG000001"; gene_name "GENE_X";\n'
            'chr1\t.\tgene\t1\t1000\t1000\t+\t.\tgene_id "ENSG000002"; gene_name "GENE_Y";\n'
        )
    view = _view(path, unit="counts", labels=["CR", "SD"])
    view.metadata.representation.feature_id = "ensembl"

    table = build_feature_table(view, "gene", gtf_path=gtf_path)

    values = {(row["unit"], row["patient_row"]): row["value"] for row in table.records}
    assert table.metadata["scale_rule"] == "log2(TPM+1); recount3 GTF gene lengths"
    assert values[("GENE_X", 0)] == pytest.approx(math.log2(500_001))
    assert values[("GENE_X", 1)] == pytest.approx(math.log2(250_001))


def test_probe_collapse_uses_highest_mean_expression_without_labels(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(
        path,
        ["0", "1"],
        [["probe_b", 1, 9], ["probe_a", 4, 5], ["probe_c", 2, 4]],
    )
    (tmp_path / "probe_to_gene.tsv").write_text(
        "probe_id\tgene_symbol\tentrez_id\n"
        "probe_b\tGENE_X\t1\nprobe_a\tGENE_X\t1\nprobe_c\tGENE_Y\t2\n",
        encoding="utf-8",
    )
    view = _view(
        path,
        platform="microarray",
        unit="probe_intensity",
        transform="log2",
        feature_id="probe",
        labels=["CR", "SD"],
    )

    first = build_feature_table(view, "gene")
    view.clinical_rows.reverse()
    second = build_feature_table(view, "gene")

    assert first.metadata["probe_rule"] == "highest mean expression across all samples; ties use probe ID order"
    assert first.metadata["probe_counts"] == {"probes": 3, "mapped_probes": 3, "genes": 2, "collapsed_probes": 1}
    assert first.records == second.records
    assert {(row["unit"], row["patient_row"]): row["value"] for row in first.records}[("GENE_X", 0)] == 1.0


def test_panels_use_complete_coverage_and_the_shared_panel_scorer(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(path, ["0", "1"], [["GENE_X", 2, 4], ["GENE_Y", 6, 8]])

    table = build_feature_table(
        _view(path, labels=["CR", "SD"]),
        "panel",
        panels={"COMPLETE": ("GENE_X", "GENE_Y"), "INCOMPLETE": ("GENE_X", "MISSING")},
    )
    values = {(row["unit"], row["patient_row"]): row["value"] for row in table.records}

    assert values[("COMPLETE", 0)] == pytest.approx((math.log2(3) + math.log2(7)) / 2)
    assert values[("COMPLETE", 1)] == pytest.approx((math.log2(5) + math.log2(9)) / 2)
    assert values[("INCOMPLETE", 0)] is None
    assert table.coverage["COMPLETE"]["complete"] is True
    assert table.coverage["INCOMPLETE"]["complete"] is False


def test_external_patient_table_accepts_fraction_units_without_identifiers():
    table = external_feature_table(
        [
            {"patient_row": 0, "unit": "CD8_T", "value": 0.2},
            {"patient_row": 1, "unit": "CD8_T", "value": 0.4},
        ],
        cohort_id="synthetic",
    )

    assert table.unit_family == "fraction"
    assert table.records[1]["unit_family"] == "fraction"
    with pytest.raises(ValueError, match="identifier"):
        external_feature_table(
            [{"patient_id": "unused", "unit": "CD8_T", "value": 0.2}],
            cohort_id="synthetic",
        )


def test_wide_feature_table_round_trips_without_source_identifiers(tmp_path):
    table = FeatureTable(
        cohort_id="synthetic",
        unit_family="panel",
        values_by_unit={"PANEL_A": [0.1, None], "PANEL_B": [0.4, 0.8]},
        n_patients=2,
        coverage={"PANEL_A": {"n_found": 2, "n_total": 2, "missing": [], "complete": True}},
    )
    path = tmp_path / "features.tsv"
    write_feature_table(table, path)

    restored = read_feature_table(
        path,
        cohort_id="synthetic",
        unit_family="panel",
        n_patients=2,
    )

    assert restored.values_by_unit == table.values_by_unit
    assert "patient_row" in path.read_text(encoding="utf-8").splitlines()[0]
    assert "patient_id" not in path.read_text(encoding="utf-8")

