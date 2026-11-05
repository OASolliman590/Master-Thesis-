from __future__ import annotations

import csv
import gzip
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_meta.features import (
    FeatureTable,
    _collapse_duplicate_genes,
    _source_symbols,
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


def test_gene_features_align_to_cohort_row_identity_not_expression_column_order(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(path, ["row_b", "row_a"], [["GENE_X", 7, 3]])
    view = _view(path, labels=["CR", "SD"])
    view.clinical_rows = [
        {"patient_id": "row_a", "raw_orr": "CR"},
        {"patient_id": "row_b", "raw_orr": "SD"},
    ]

    table = build_feature_table(view, "gene")

    assert table.values_by_unit["GENE_X"] == pytest.approx([2.0, 3.0])


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
        "probe_b\tGENE_X\t999999901\nprobe_a\tGENE_X\t999999901\nprobe_c\tGENE_Y\t999999902\n",
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


def test_old_symbol_probes_use_entrez_identity_before_panel_resolution(tmp_path, monkeypatch):
    from tools.a_meta import features as feature_module

    path = tmp_path / "expression.tsv"
    _write_matrix(
        path,
        ["0", "1"],
        [
            ["probe_cgas_low", 1, 3],
            ["probe_cgas_high", 4, 6],
            ["probe_mavs", 3, 5],
            ["probe_tet3", 2, 4],
            ["probe_kdm6a", 5, 7],
        ],
    )
    (tmp_path / "probe_to_gene.tsv").write_text(
        "probe_id\tgene_symbol\tentrez_id\n"
        "probe_cgas_low\tC6orf150\t115004\n"
        "probe_cgas_high\tMB21D1\t115004\n"
        "probe_mavs\tVISA\t57506\n"
        "probe_tet3\tBEFAHRS\t200424\n"
        "probe_kdm6a\tUTX\t7403\n",
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
    monkeypatch.setattr(
        feature_module,
        "_gene_reference",
        lambda runtime: {
            "by_id": {
                "115004": "CGAS",
                "57506": "MAVS",
                "200424": "TET3",
                "7403": "KDM6A",
            },
            "synonyms": {},
            "ensembl": {},
        },
    )

    table = build_feature_table(
        view,
        "panel",
        panels={"SYNTHETIC_PANEL": ("CGAS", "MAVS", "TET3", "KDM6A")},
    )

    assert table.coverage["SYNTHETIC_PANEL"] == {
        "n_found": 4,
        "n_total": 4,
        "missing": [],
        "complete": True,
    }
    assert table.values_by_unit["SYNTHETIC_PANEL"] == pytest.approx([3.5, 5.5])
    assert table.metadata["source_scale_rule"] == "source_scale"


def test_ensembl_identifiers_resolve_to_panel_symbols(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(
        path,
        ["0", "1"],
        [["ENSG00000164430.3", 2, 4], ["ENSG00000088888.1", 6, 8]],
    )
    view = _view(path, labels=["CR", "SD"])
    view.metadata.representation.feature_id = "ensembl"

    table = build_feature_table(
        view,
        "gene",
        gene_map={"ENSG00000164430": "CGAS", "ENSG00000088888": "MAVS"},
    )

    assert table.values_by_unit["CGAS"] == pytest.approx([math.log2(3), math.log2(5)])
    assert table.values_by_unit["MAVS"] == pytest.approx([math.log2(7), math.log2(9)])


def test_gene_alias_addendum_resolves_the_older_ensembl_identifier():
    source_symbols = _source_symbols(
        ["ENSG00000161570.4", "ENSG_CURRENT"],
        "ensembl",
        custom_map={"ENSG_CURRENT": "CCL5"},
        reference={"by_id": {}, "synonyms": {}, "ensembl": {}},
    )
    assert source_symbols == ["CCL5", "CCL5"]
    features, values, counts, duplicates = _collapse_duplicate_genes(
        source_symbols,
        [[1.0, 2.0], [4.0, 5.0]],
    )
    assert features == ["CCL5"]
    assert values == [[4.0, 5.0]]
    assert counts["duplicate_rows_removed"] == 1
    assert duplicates == ["CCL5"]


def test_gse176307_tpm_keeps_unassayed_patient_row_missing_and_aligned(tmp_path, monkeypatch):
    from tools.a_p2 import build as a_p2_build

    clinical_rows = [
        {"patient_id": "row_0", "sample_id": "sample_0"},
        {"patient_id": "row_1", "sample_id": "sample_1"},
        {"patient_id": "row_2", "sample_id": "sample_2"},
    ]
    monkeypatch.setattr(
        a_p2_build,
        "gse_mapping",
        lambda clinical, inputs, runtime: {"row_0": "assay_0", "row_2": "assay_2"},
    )
    monkeypatch.setattr(a_p2_build, "source", lambda path, inputs, runtime: path)
    monkeypatch.setattr(
        a_p2_build,
        "matrix",
        lambda path, selected, runtime: (["GENE_A"], [[3.0, 7.0]]),
    )
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="gse176307",
            representation=SimpleNamespace(
                platform="rnaseq", unit="normalised_counts", transform="other", feature_id="ensembl"
            ),
        ),
        expression_path=tmp_path / "unused-expression.tsv",
        clinical_rows=clinical_rows,
    )

    table = build_feature_table(
        view,
        "gene",
        runtime=tmp_path,
        panels={"PANEL": ("GENE_A",)},
    )

    assert table.n_patients == 3
    assert table.values_by_unit["GENE_A"] == pytest.approx([2.0, None, 3.0])
    assert table.metadata["scale_rule"] == "log2(TPM+1); official GSE176307 Salmon TPM"
    assert table.metadata["representation"]["unit"] == "tpm"
    assert table.metadata["patients_with_tpm_assay"] == 2
    assert table.metadata["patients_without_tpm_assay"] == 1


def test_symbol_probe_suffix_is_removed_only_for_known_gene_symbols(tmp_path, monkeypatch):
    from tools.a_meta import features as feature_module

    path = tmp_path / "expression.tsv"
    _write_matrix(
        path,
        ["0", "1"],
        [["GZMA_165265", 2, 4], ["PRF1_672778", 6, 8], ["UNKNOWN_123", 1, 1]],
    )
    monkeypatch.setattr(
        feature_module,
        "_gene_reference",
        lambda runtime: {
            "by_id": {"3001": "GZMA", "5551": "PRF1"},
            "synonyms": {},
            "ensembl": {},
        },
    )
    view = _view(path, labels=["CR", "SD"])

    table = build_feature_table(view, "gene")

    assert "GZMA" in table.values_by_unit
    assert "PRF1" in table.values_by_unit
    assert "UNKNOWN_123" in table.values_by_unit


def test_duplicate_gene_rows_keep_one_highest_mean_representative(tmp_path):
    path = tmp_path / "expression.tsv"
    _write_matrix(
        path,
        ["0", "1"],
        [["GENE_X", 1, 2], ["GENE_X", 5, 6], ["GENE_Y", 3, 4]],
    )

    table = build_feature_table(_view(path, labels=["CR", "SD"]), "gene")

    assert table.values_by_unit["GENE_X"] == pytest.approx([math.log2(6), math.log2(7)])
    assert table.metadata["duplicate_gene_rule"] == (
        "highest mean expression across all samples; ties use source row order"
    )
    assert table.metadata["duplicate_gene_counts"] == {
        "input_rows": 3,
        "genes": 2,
        "duplicate_gene_groups": 1,
        "duplicate_rows_removed": 1,
    }


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


def test_panel_coverage90_scores_17_of_18_but_not_7_of_8(tmp_path):
    path = tmp_path / "expression.tsv"
    panel18 = tuple(f"ZZ_SYNTHETIC_ONLY_PANEL18_MEMBER_{chr(65 + index)}" for index in range(18))
    panel8 = tuple(f"ZZ_SYNTHETIC_ONLY_PANEL8_MEMBER_{chr(65 + index)}" for index in range(8))
    available = [*panel18[:17], *panel8[:7]]
    _write_matrix(path, ["0"], [[gene, 3] for gene in available])
    view = _view(path, labels=["CR"])
    panels = {"PANEL_18": panel18, "PANEL_8": panel8}

    main = build_feature_table(view, "panel", panels=panels)
    sensitivity = build_feature_table(view, "panel_coverage90", panels=panels)

    assert main.values_by_unit == {"PANEL_18": [None], "PANEL_8": [None]}
    assert sensitivity.coverage["PANEL_18"]["n_found"] == 17
    assert sensitivity.coverage["PANEL_18"]["n_total"] == 18
    assert sensitivity.coverage["PANEL_18"]["complete"] is True
    assert sensitivity.values_by_unit["PANEL_18"] == pytest.approx([2.0])
    assert sensitivity.coverage["PANEL_8"]["n_found"] == 7
    assert sensitivity.coverage["PANEL_8"]["n_total"] == 8
    assert sensitivity.coverage["PANEL_8"]["complete"] is False
    assert sensitivity.values_by_unit["PANEL_8"] == [None]
    assert sensitivity.metadata["sensitivity_label"] == "sensitivity only; does not support claims alone"


def test_panel_coverage90_fixes_study_subset_and_keeps_main_panel_row_missing():
    from tools.a_meta.features import _panel_coverage90_table, _panel_table

    members = tuple(f"ZZ_SYNTHETIC_ONLY_EIGHT_GENE_MEMBER_{chr(65 + index)}" for index in range(8))
    genes = FeatureTable(
        cohort_id="synthetic",
        unit_family="gene",
        values_by_unit={
            gene: [float(index + 1), float(index + 2), float(index + 3)]
            for index, gene in enumerate(members)
        },
        n_patients=3,
        metadata={"scale_rule": "synthetic fixture scale"},
    )
    genes.values_by_unit[members[-1]][0] = None
    view = SimpleNamespace(metadata=SimpleNamespace(cohort_id="synthetic"))
    panels = {"EIGHT_MEMBER_PANEL": members}

    main = _panel_table(view, genes, panels)
    sensitivity = _panel_coverage90_table(view, genes, panels)

    assert sensitivity.coverage["EIGHT_MEMBER_PANEL"]["n_found"] == 8
    assert sensitivity.coverage["EIGHT_MEMBER_PANEL"]["complete"] is True
    assert sensitivity.values_by_unit["EIGHT_MEMBER_PANEL"] == [None, 5.5, 6.5]
    assert main.coverage["EIGHT_MEMBER_PANEL"]["n_found"] == 8
    assert main.coverage["EIGHT_MEMBER_PANEL"]["complete"] is True
    assert main.values_by_unit["EIGHT_MEMBER_PANEL"] == [None, 5.5, 6.5]


def test_fixed_coverage90_subset_counts_zero_and_missing_patient_gets_na():
    from tools.a_meta.features import _panel_coverage90_table

    members = tuple(f"ZZ_SYNTHETIC_ONLY_FIXED_SUBSET_{index:02d}" for index in range(10))
    values = {gene: [0.0 if index == 0 else 1.0, 1.0] for index, gene in enumerate(members[:9])}
    values[members[1]][1] = None
    values[members[9]] = [None, None]
    genes = FeatureTable(
        cohort_id="synthetic",
        unit_family="gene",
        values_by_unit=values,
        n_patients=2,
        metadata={"scale_rule": "synthetic fixture scale"},
    )
    view = SimpleNamespace(metadata=SimpleNamespace(cohort_id="synthetic"))

    result = _panel_coverage90_table(view, genes, {"SYNTHETIC_FIXED_PANEL": members})

    details = result.coverage["SYNTHETIC_FIXED_PANEL"]
    assert details["n_found"] == 9
    assert details["fixed_subset"] == list(members[:9])
    assert result.values_by_unit["SYNTHETIC_FIXED_PANEL"][0] == pytest.approx(8 / 9)
    assert result.values_by_unit["SYNTHETIC_FIXED_PANEL"][1] is None


@pytest.mark.parametrize("platform", ["targeted_rna", "nanostring"])
def test_gene_and_pathway_families_refuse_targeted_platforms(platform):
    from tools.a_meta.features import _PATHWAY_FAMILIES

    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            representation=SimpleNamespace(platform=platform),
        )
    )
    for family in ("gene", *_PATHWAY_FAMILIES):
        with pytest.raises(ValueError, match="targeted_rna and nanostring"):
            build_feature_table(view, family)


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


def test_feature_reader_keeps_coverage_metadata_by_unit_family(tmp_path):
    values_path = tmp_path / "panels.tsv"
    values_path.write_text("patient_row\tPANEL_A\n0\tNA\n", encoding="utf-8")
    coverage_path = tmp_path / "coverage.tsv"
    coverage_path.write_text(
        "unit_family\tunit\tn_found\tn_total\tcomplete\tmissing\n"
        "panel\tPANEL_A\t17\t18\tfalse\tGENE_Z\n"
        "panel_coverage90\tPANEL_A\t17\t18\ttrue\tGENE_Z\n",
        encoding="utf-8",
    )

    main = read_feature_table(
        values_path,
        cohort_id="synthetic",
        unit_family="panel",
        n_patients=1,
        coverage_path=coverage_path,
    )
    sensitivity = read_feature_table(
        values_path,
        cohort_id="synthetic",
        unit_family="panel_coverage90",
        n_patients=1,
        coverage_path=coverage_path,
    )

    assert main.coverage["PANEL_A"]["complete"] is False
    assert sensitivity.coverage["PANEL_A"]["complete"] is True

