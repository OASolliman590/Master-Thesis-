from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.a_meta import features
from tools.a_meta.frozen import (
    COMMON_GENE_TABLE,
    HALLMARK_GMT,
    IDENTIFIER_PROPOSALS,
    REACTOME_GMT,
    file_sha256,
    read_common_gene_sets,
    read_hallmark_gene_sets,
    read_identifier_proposals,
)


def test_signed_gene_set_and_proposal_hashes_are_checked():
    assert len(read_hallmark_gene_sets()) == 50
    assert len(read_common_gene_sets()) == 50
    assert len(read_identifier_proposals()) == 23
    assert len(file_sha256(HALLMARK_GMT)) == 64
    assert len(file_sha256(REACTOME_GMT)) == 64
    assert file_sha256(COMMON_GENE_TABLE) == "1ce5611a406b98d96016eed697ccaf2642df847ca0907fc7f877da65b9d53e51"
    assert file_sha256(IDENTIFIER_PROPOSALS) == "7f90583f0548cafecd57a3a059c087ea9d3b945867e09262fec3c23e13287d84"


@pytest.mark.parametrize("reader", [read_hallmark_gene_sets, read_common_gene_sets, read_identifier_proposals])
def test_frozen_inputs_refuse_a_hash_mismatch(tmp_path, reader):
    fake_input = tmp_path / "mismatched.tsv"
    fake_input.write_text("SET_SYNTH\tfixture\tGENE_SYNTH_A\tGENE_SYNTH_B\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        reader(fake_input)


def test_hallmark_ifng_is_the_eleventh_custom_panel():
    panel_ids = features.AVAILABLE_PANEL_IDS
    panels = features._panel_definitions(panel_ids)

    assert len(panel_ids) == 11
    assert panel_ids[-1] == "HALLMARK_INTERFERON_GAMMA_RESPONSE"
    assert len(panels[panel_ids[-1]]) == 200
    assert features.PANEL_METHOD_IDS[panel_ids[-1]] == "CUSTOM_MEAN_HALLMARK_INTERFERON_GAMMA_RESPONSE"


def test_m5m6_gene_family_has_21_frozen_units():
    assert len(features._m5m6_gene_units()) == 21


def test_identifier_addendum_contains_every_signed_mapping_without_splitting_rows(tmp_path):
    proposals = {row["source_id"]: row["registry_symbol"] for row in read_identifier_proposals()}
    addendum = features._gene_alias_addendum()
    assert all(addendum[source] == target for source, target in proposals.items())
    assert len(proposals) == 23

    matrix = tmp_path / "synthetic-expression.tsv"
    matrix.write_text(
        "gene\t0\nZZ_SYNTHETIC_ONLY_A,ZZ_SYNTHETIC_ONLY_B\t1\n",
        encoding="utf-8",
    )
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            cancer="melanoma",
            representation=SimpleNamespace(
                platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"
            ),
            endpoint_families=("orr",),
        ),
        expression_path=matrix,
        clinical_rows=[{}],
    )
    table = features.build_feature_table(view, "gene")
    assert tuple(table.values_by_unit) == ("ZZ_SYNTHETIC_ONLY_A,ZZ_SYNTHETIC_ONLY_B",)


def test_signed_alias_addendum_maps_synthetic_hallmark_expression_target(monkeypatch):
    monkeypatch.setattr(
        features,
        "_gene_alias_addendum",
        lambda: {"ENSG_SYNTH_ONLY_A": "GENE_SYNTH_TARGET"},
    )

    mapped = features._source_symbols(
        ["ENSG_SYNTH_ONLY_A"],
        "ensembl",
        custom_map={},
        reference={"by_id": {}, "synonyms": {}, "ensembl": {}},
    )

    assert mapped == ["GENE_SYNTH_TARGET"]


def test_targeted_subset_is_study_local_and_uses_a_fixed_subset(monkeypatch):
    members = ("GENE_SYNTH_A", "GENE_SYNTH_B", "GENE_SYNTH_C")
    genes = features.FeatureTable(
        cohort_id="synthetic",
        unit_family="gene",
        values_by_unit={
            "GENE_SYNTH_A": [0.0, 0.0],
            "GENE_SYNTH_B": [2.0, None],
            "GENE_SYNTH_C": [4.0, 4.0],
        },
        n_patients=2,
        metadata={"scale_rule": "synthetic scale"},
    )
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            representation=SimpleNamespace(platform="targeted_rna"),
        )
    )
    monkeypatch.setattr(features, "TARGETED_SUBSET_STUDIES", {"synthetic"})
    monkeypatch.setattr(features, "read_frozen_aliases", lambda: {})
    monkeypatch.setattr(features, "read_hallmark_gene_sets", lambda **_kwargs: {"SET_SYNTH": members})
    monkeypatch.setattr(features, "_gene_table", lambda *_args, **_kwargs: genes)

    result = features.build_feature_table(view, "targeted_subset")

    assert result.values_by_unit["SET_SYNTH"] == [2.0, None]
    assert result.coverage["SET_SYNTH"]["fixed_subset"] == list(members)
    assert result.metadata["sensitivity_label"] == "sensitivity only; does not support claims alone"


def test_m5m6_gene_family_remains_available_on_targeted_platforms(monkeypatch):
    fake_panels = {
        "M5_CHECKPOINT_CANDIDATES": ("GENE_SYNTH_M5",),
        "M6_EPIGENETIC_REGULATORS": ("GENE_SYNTH_M6",),
    }
    genes = features.FeatureTable(
        cohort_id="synthetic",
        unit_family="gene",
        values_by_unit={"GENE_SYNTH_M5": [0.0], "GENE_SYNTH_M6": [1.0]},
        n_patients=1,
        metadata={"scale_rule": "synthetic scale"},
    )
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            representation=SimpleNamespace(platform="nanostring"),
        )
    )
    monkeypatch.setattr(features.a_scoring.core, "panel_definitions", lambda _ids: fake_panels)
    monkeypatch.setattr(features, "read_frozen_aliases", lambda: {})
    monkeypatch.setattr(features, "_gene_table", lambda *_args, **_kwargs: genes)

    result = features.build_feature_table(view, "m5m6_gene")

    assert result.unit_family == "m5m6_gene"
    assert set(result.values_by_unit) == {"GENE_SYNTH_M5", "GENE_SYNTH_M6"}


def test_pathway_families_refuse_wrong_hash_even_with_a_valid_gmt_shape(tmp_path):
    fake_gmt = tmp_path / "hallmark.gmt"
    fake_gmt.write_text("SET_SYNTH\tfixture\tGENE_SYNTH_A\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        read_hallmark_gene_sets(fake_gmt)


def test_pathway_route_maps_aliases_and_scores_only_resolved_hallmark_targets(tmp_path, monkeypatch):
    aliases = {"GENE_SYNTH_ALIAS": "GENE_SYNTH_TARGET"}
    gene_sets = tmp_path / "synthetic.gmt"
    gene_sets.write_text("SET_SYNTH\tfixture\tGENE_SYNTH_ALIAS\n", encoding="utf-8")
    captured = {}

    def fake_gene_table(_view, *, target_symbols, **_kwargs):
        captured["targets"] = tuple(target_symbols)
        return features.FeatureTable(
            cohort_id="synthetic",
            unit_family="gene",
            values_by_unit={"GENE_SYNTH_TARGET": [2.0]},
            n_patients=1,
            metadata={"scale_rule": "synthetic scale"},
        )

    def fake_r(_script, _inputs, _config, output_dir, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        scores = output_dir / "scores.tsv"
        coverage = output_dir / "coverage.tsv"
        scores.write_text("patient_row\tunit\tvalue\n0\tSET_SYNTH\t0.5\n", encoding="utf-8")
        coverage.write_text(
            "unit\tn_found\tn_total\tcomplete\tmissing_genes\tfixed_subset\tscorable\treason\n"
            "SET_SYNTH\t1\t1\ttrue\t\tGENE_SYNTH_TARGET\ttrue\t\n",
            encoding="utf-8",
        )
        return SimpleNamespace(outputs={"scores.tsv": scores, "coverage.tsv": coverage}, manifest={"synthetic": True})

    monkeypatch.setattr(features, "read_frozen_aliases", lambda: aliases)
    monkeypatch.setattr(features, "_gene_table", fake_gene_table)
    from tools.a_meta import r_manifest

    monkeypatch.setattr(r_manifest, "run_r_sanitised", fake_r)
    view = SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id="synthetic",
            representation=SimpleNamespace(platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"),
        ),
        expression_path=tmp_path / "expression.tsv",
        clinical_rows=[{}],
    )

    result = features.build_feature_table(
        view,
        "pathway",
        gene_sets=gene_sets,
        test_only_gene_sets=True,
        r_out_dir=tmp_path / "R-singscore-pathway",
    )

    assert captured["targets"] == ("GENE_SYNTH_TARGET",)
    assert result.values_by_unit["SET_SYNTH"] == [0.5]
