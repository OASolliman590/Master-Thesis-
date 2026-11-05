from __future__ import annotations

import csv
from types import SimpleNamespace

import pytest

from tools.a_meta.features import build_feature_table
from tools.r_bridge import RScriptError


@pytest.mark.requires_r
def test_singscore_r_scores_tiny_synthetic_matrix_and_gene_set(tmp_path):
    expression_path = tmp_path / "expression.tsv"
    with expression_path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", "0", "1", "2"])
        writer.writerow(["GENE_SYNTH_A", 1, 5, 3])
        writer.writerow(["GENE_SYNTH_B", 4, 2, 3])
        writer.writerow(["GENE_SYNTH_C", 3, 4, 5])
        writer.writerow(["GENE_SYNTH_D", 2, 3, 4])
    gene_sets_path = tmp_path / "tiny.gmt"
    gene_sets_path.write_text("TOY_SET\tSynthetic test\tGENE_SYNTH_A\tGENE_SYNTH_B\n", encoding="utf-8")
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
        test_only_gene_sets=True,
        r_out_dir=tmp_path / "r-singscore",
    )

    assert table.unit_family == "test_only_pathway"
    assert table.metadata["method_id_by_unit"]["TOY_SET"] == "SINGSCORE_TEST_ONLY_GENE_SETS"
    assert table.metadata["test_only_gene_sets"] is True
    assert table.coverage["TOY_SET"]["complete"] is True
    assert len(table.values_by_unit["TOY_SET"]) == 3
    assert all(value is not None for value in table.values_by_unit["TOY_SET"])


@pytest.mark.requires_r
def test_pathway_coverage90_uses_a_fixed_subset_and_na_for_a_missing_patient_gene(tmp_path):
    expression_path = tmp_path / "expression-coverage.tsv"
    members = [f"GENE_SYNTH_PATHWAY_{index:02d}" for index in range(10)]
    with expression_path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", "0", "1"])
        for index, gene in enumerate(members[:9]):
            writer.writerow([gene, 0 if index == 0 else 1, "NA" if index == 1 else 2])
        writer.writerow(["GENE_SYNTH_BACKGROUND", 3, 4])
    gene_sets_path = tmp_path / "synthetic-coverage.gmt"
    gene_sets_path.write_text("SET_SYNTH\tfixture\t" + "\t".join(members) + "\n", encoding="utf-8")
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
        clinical_rows=[{}, {}],
    )

    table = build_feature_table(
        view,
        "pathway_coverage90",
        gene_sets=gene_sets_path,
        test_only_gene_sets=True,
        r_out_dir=tmp_path / "r-singscore-coverage",
    )

    coverage = table.coverage["SET_SYNTH"]
    assert coverage["n_found"] == 9
    assert coverage["complete"] is True
    assert coverage["fixed_subset"] == members[:9]
    assert table.values_by_unit["SET_SYNTH"][0] is not None
    assert table.values_by_unit["SET_SYNTH"][1] is None


@pytest.mark.requires_r
def test_test_only_gene_sets_are_refused_for_a_registered_cohort(tmp_path):
    from types import SimpleNamespace

    from tools.a_meta.features import build_feature_table

    expression_path = tmp_path / "expression.tsv"
    expression_path.write_text("gene\t0\nGENE_SYNTH_A\t1\n", encoding="utf-8")
    gene_sets_path = tmp_path / "tiny.gmt"
    gene_sets_path.write_text("SET_SYNTH\tfixture\tGENE_SYNTH_A\n", encoding="utf-8")
    cohort_id = "liu2019"
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id=cohort_id,
            representation=SimpleNamespace(
                platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"
            ),
        ),
        expression_path=expression_path,
        clinical_rows=[{}],
    )

    with pytest.raises(ValueError, match="test_only_gene_sets is restricted"):
        build_feature_table(
            view,
            "pathway",
            gene_sets=gene_sets_path,
            test_only_gene_sets=True,
            r_out_dir=tmp_path / "r-singscore",
        )

    assert not (tmp_path / "r-singscore").exists()


@pytest.mark.requires_r
def test_singscore_refuses_nonfinite_nonmember_in_fixed_background(tmp_path):
    from types import SimpleNamespace

    expression_path = tmp_path / "expression-background.tsv"
    expression_path.write_text(
        "gene\t0\t1\nGENE_SYNTH_MEMBER\t1\t2\nGENE_SYNTH_BACKGROUND\t3\tNA\n",
        encoding="utf-8",
    )
    gene_sets_path = tmp_path / "background.gmt"
    gene_sets_path.write_text(
        "SET_SYNTH\tfixture\tGENE_SYNTH_MEMBER\n", encoding="utf-8"
    )
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            representation=SimpleNamespace(
                platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"
            ),
        ),
        expression_path=expression_path,
        clinical_rows=[{}, {}],
    )

    with pytest.raises(RScriptError, match="non-member gene to be finite"):
        build_feature_table(
            view,
            "pathway",
            gene_sets=gene_sets_path,
            test_only_gene_sets=True,
            r_out_dir=tmp_path / "r-singscore-background",
        )

