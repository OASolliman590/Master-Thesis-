from __future__ import annotations

import csv
from types import SimpleNamespace

import pytest

from tools.a_meta.features import build_feature_table


@pytest.mark.requires_r
def test_singscore_r_scores_tiny_synthetic_matrix_and_gene_set(tmp_path):
    expression_path = tmp_path / "expression.tsv"
    with expression_path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", "0", "1", "2"])
        writer.writerow(["GENE_A", 1, 5, 3])
        writer.writerow(["GENE_B", 4, 2, 3])
        writer.writerow(["GENE_C", 3, 4, 5])
        writer.writerow(["GENE_D", 2, 3, 4])
    gene_sets_path = tmp_path / "tiny.gmt"
    gene_sets_path.write_text("TOY_SET\tSynthetic test\tGENE_A\tGENE_B\n", encoding="utf-8")
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            cancer="melanoma",
            representation=SimpleNamespace(
                platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"
            ),
            endpoint_families=("orr",),
        ),
        expression_path=expression_path,
        clinical_rows=[{}, {}, {}],
    )

    table = build_feature_table(
        view,
        "pathway",
        gene_sets=gene_sets_path,
        r_out_dir=tmp_path / "r-singscore",
    )

    assert table.unit_family == "pathway"
    assert table.coverage["TOY_SET"]["complete"] is True
    assert len(table.values_by_unit["TOY_SET"]) == 3
    assert all(value is not None for value in table.values_by_unit["TOY_SET"])

