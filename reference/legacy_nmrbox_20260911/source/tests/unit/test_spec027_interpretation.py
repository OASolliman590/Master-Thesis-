from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from src.pipeline.cli import main
from src.pipeline.common.io import read_tsv, write_tsv


contracts = importlib.import_module("src.pipeline.modules.10_interpretation.contracts")


def _fixture_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "run_root"
    meta_dir = root / "meta" / "PRE_RESPONSE"
    sig_dir = root / "signature" / "PRE_RESPONSE"
    immune_dir = root / "immune_state"
    patient_dir = root / "patient_manifest"
    meta_dir.mkdir(parents=True)
    sig_dir.mkdir(parents=True)
    immune_dir.mkdir(parents=True)
    patient_dir.mkdir(parents=True)
    write_tsv(
        meta_dir / "meta_effects.tsv",
        [
            "analysis_id",
            "gene_symbol",
            "meta_effect_random",
            "meta_se_random",
            "meta_fdr",
            "n_cohorts_contributed",
        ],
        [
            {"analysis_id": "PRE_RESPONSE", "gene_symbol": "GENEA", "meta_effect_random": "1.2", "meta_se_random": "0.2", "meta_fdr": "0.01", "n_cohorts_contributed": "3"},
            {"analysis_id": "PRE_RESPONSE", "gene_symbol": "GENEB", "meta_effect_random": "0.8", "meta_se_random": "0.3", "meta_fdr": "0.02", "n_cohorts_contributed": "3"},
            {"analysis_id": "PRE_RESPONSE", "gene_symbol": "GENEC", "meta_effect_random": "-1.1", "meta_se_random": "0.2", "meta_fdr": "0.03", "n_cohorts_contributed": "3"},
            {"analysis_id": "PRE_RESPONSE", "gene_symbol": "GENED", "meta_effect_random": "-0.7", "meta_se_random": "0.4", "meta_fdr": "0.04", "n_cohorts_contributed": "3"},
        ],
    )
    write_tsv(
        sig_dir / "responder_signature_tiered.tsv",
        ["analysis_id", "gene_symbol", "signature_direction", "effect", "meta_fdr", "blocked_flag"],
        [
            {"analysis_id": "PRE_RESPONSE", "gene_symbol": "GENEA", "signature_direction": "up", "effect": "1.2", "meta_fdr": "0.01", "blocked_flag": "false"},
            {"analysis_id": "PRE_RESPONSE", "gene_symbol": "GENEC", "signature_direction": "down", "effect": "-1.1", "meta_fdr": "0.03", "blocked_flag": "false"},
        ],
    )
    write_tsv(
        immune_dir / "ssgsea_scores.tsv",
        [
            "cohort_id",
            "sample_id",
            "patient_uid",
            "T_CELL_INFLAMED_GEP_18",
            "HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI",
            "EPIGENETIC_CHECKPOINT_REGULATION",
            "EPIGENETIC_IMMUNE_PRIMING",
            "PRC2_IMMUNE_TARGETS",
            "HOPE_18",
        ],
        [
            {"cohort_id": "cohort1", "sample_id": "S1", "patient_uid": "P1", "T_CELL_INFLAMED_GEP_18": "2.0", "HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI": "1.5", "EPIGENETIC_CHECKPOINT_REGULATION": "1.1", "EPIGENETIC_IMMUNE_PRIMING": "0.8", "PRC2_IMMUNE_TARGETS": "0.2", "HOPE_18": "1.7"},
            {"cohort_id": "cohort1", "sample_id": "S2", "patient_uid": "P2", "T_CELL_INFLAMED_GEP_18": "1.7", "HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI": "1.2", "EPIGENETIC_CHECKPOINT_REGULATION": "1.0", "EPIGENETIC_IMMUNE_PRIMING": "0.7", "PRC2_IMMUNE_TARGETS": "0.3", "HOPE_18": "1.5"},
            {"cohort_id": "cohort1", "sample_id": "S3", "patient_uid": "P3", "T_CELL_INFLAMED_GEP_18": "-0.5", "HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI": "-0.2", "EPIGENETIC_CHECKPOINT_REGULATION": "-0.4", "EPIGENETIC_IMMUNE_PRIMING": "-0.6", "PRC2_IMMUNE_TARGETS": "-0.1", "HOPE_18": "-0.3"},
            {"cohort_id": "cohort1", "sample_id": "S4", "patient_uid": "P4", "T_CELL_INFLAMED_GEP_18": "-0.7", "HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI": "-0.4", "EPIGENETIC_CHECKPOINT_REGULATION": "-0.5", "EPIGENETIC_IMMUNE_PRIMING": "-0.7", "PRC2_IMMUNE_TARGETS": "-0.2", "HOPE_18": "-0.6"},
        ],
    )
    write_tsv(
        patient_dir / "patient_manifest.tsv",
        ["patient_uid", "cohort_id", "response_label", "pre_sample_ids"],
        [
            {"patient_uid": "P1", "cohort_id": "cohort1", "response_label": "responder", "pre_sample_ids": "S1"},
            {"patient_uid": "P2", "cohort_id": "cohort1", "response_label": "responder", "pre_sample_ids": "S2"},
            {"patient_uid": "P3", "cohort_id": "cohort1", "response_label": "non_responder", "pre_sample_ids": "S3"},
            {"patient_uid": "P4", "cohort_id": "cohort1", "response_label": "non_responder", "pre_sample_ids": "S4"},
        ],
    )
    gmt = tmp_path / "sets.gmt"
    gmt.write_text("PATHWAY_A\tdesc\tGENEA\tGENEB\nPATHWAY_B\tdesc\tGENEC\tGENED\n", encoding="utf-8")
    registry = tmp_path / "gene_sets.tsv"
    write_tsv(
        registry,
        ["gene_set_id", "gene_set_layer", "gene_set_name", "gmt_path", "source", "enabled", "notes"],
        [{"gene_set_id": "TEST", "gene_set_layer": "TEST_LAYER", "gene_set_name": "test", "gmt_path": str(gmt), "source": "fixture", "enabled": "true", "notes": ""}],
    )
    return root, registry


def test_interpretation_path_guard_rejects_non_interpretation_output(tmp_path: Path) -> None:
    root, _ = _fixture_root(tmp_path)
    with pytest.raises(ValueError):
        contracts.interpretation_root(root, tmp_path / "elsewhere")


def test_interpret_enrich_uses_ranked_statistic_and_claim_class(tmp_path: Path) -> None:
    root, registry = _fixture_root(tmp_path)
    out = root / "interpretation"
    assert main(["interpret", "enrich", "--results-root", str(root), "--analysis-id", "PRE_RESPONSE", "--collections", str(registry), "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0
    rows = read_tsv(out / "enrichment" / "PRE_RESPONSE" / "gsea.tsv")
    assert rows
    assert {r["statistic"] for r in rows} == {"meta_effect_random"}
    assert {r["claim_class"] for r in rows} == {"mechanism_hypothesis"}


def test_interpret_enrich_blocks_header_only_meta_without_crashing(tmp_path: Path) -> None:
    root, registry = _fixture_root(tmp_path)
    analysis_id = "EMPTY_META"
    empty_meta_dir = root / "meta" / analysis_id
    empty_sig_dir = root / "signature" / analysis_id
    empty_meta_dir.mkdir(parents=True)
    empty_sig_dir.mkdir(parents=True)
    write_tsv(
        empty_meta_dir / "meta_effects.tsv",
        [
            "analysis_id",
            "gene_symbol",
            "meta_effect_random",
            "meta_se_random",
            "meta_fdr",
            "n_cohorts_contributed",
        ],
        [],
    )
    write_tsv(
        empty_sig_dir / "responder_signature_tiered.tsv",
        ["analysis_id", "gene_symbol", "signature_direction", "effect", "meta_fdr", "blocked_flag"],
        [],
    )

    out = root / "interpretation"
    assert main(["interpret", "enrich", "--results-root", str(root), "--analysis-id", analysis_id, "--collections", str(registry), "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0

    gsea = read_tsv(out / "enrichment" / analysis_id / "gsea.tsv")
    ora = read_tsv(out / "enrichment" / analysis_id / "ora.tsv")
    dotplot = read_tsv(out / "enrichment" / analysis_id / "dotplot_data.tsv")
    provenance = (out / "enrichment" / analysis_id / "provenance.md").read_text(encoding="utf-8")

    assert gsea[0]["status"].startswith("blocked:no_ranked_meta_effect_random")
    assert ora[0]["status"].startswith("blocked:no_ranked_meta_effect_random")
    assert gsea[0]["claim_class"] == "mechanism_hypothesis"
    assert dotplot == []
    assert "blocked_no_ranked_meta_effect_random" in provenance


def test_interpret_network_gates_thin_signal_and_preserves_signature_checksum(tmp_path: Path) -> None:
    root, _ = _fixture_root(tmp_path)
    signature = root / "signature" / "PRE_RESPONSE" / "responder_signature_tiered.tsv"
    before = contracts.file_sha256(signature)
    out = root / "interpretation"
    assert main(["interpret", "network", "--results-root", str(root), "--analysis-id", "PRE_RESPONSE", "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0
    after = contracts.file_sha256(signature)
    assert before == after
    hubs = read_tsv(out / "network" / "PRE_RESPONSE" / "hub_genes.tsv")
    assert hubs[0]["status"] == "insufficient_signal"
    assert "permutation_fdr" in hubs[0]


def test_interpret_hub_meta_preserves_insufficient_signal_status(tmp_path: Path) -> None:
    root, _ = _fixture_root(tmp_path)
    out = root / "interpretation"
    assert main(["interpret", "network", "--results-root", str(root), "--analysis-id", "PRE_RESPONSE", "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0
    assert main(["interpret", "hub-meta", "--results-root", str(root), "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0
    rows = read_tsv(out / "hub_meta" / "cross_cancer_hub_meta.tsv")
    assert rows[0]["status"] == "insufficient_signal"
    assert rows[0]["moderator_status"] == "cancer_as_low_dimension_moderator_only"


def test_interpret_immunophenotype_scores_rna_and_skips_non_rna_hope(tmp_path: Path) -> None:
    root, _ = _fixture_root(tmp_path)
    criteria = tmp_path / "criteria.tsv"
    write_tsv(
        criteria,
        ["criteria_id", "hope_group", "rna_derivable", "data_type", "genes_or_signature", "method", "response_direction_hypothesis", "claim_note"],
        [
            {"criteria_id": "hope_tcell_inflamed_gep", "hope_group": "hot_cold", "rna_derivable": "yes", "data_type": "rna_signature", "genes_or_signature": "NA", "method": "ssgsea_or_mean", "response_direction_hypothesis": "hot_favors_response", "claim_note": ""},
            {"criteria_id": "hope_composite_rna", "hope_group": "composite", "rna_derivable": "yes", "data_type": "derived", "genes_or_signature": "NA", "method": "weighted_zscore_composite", "response_direction_hypothesis": "higher_favors_response", "claim_note": ""},
            {"criteria_id": "tmb", "hope_group": "predictive_biomarker", "rna_derivable": "no", "data_type": "dna_wes", "genes_or_signature": "NA", "method": "requires_matched_wes", "response_direction_hypothesis": "high_tmb_favors_response", "claim_note": ""},
        ],
    )
    out = root / "interpretation"
    assert main(["interpret", "immunophenotype", "--results-root", str(root), "--criteria-registry", str(criteria), "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0
    assoc = read_tsv(out / "immunophenotype" / "phenotype_response_assoc.tsv")
    skipped = read_tsv(out / "immunophenotype" / "hope_skipped_criteria.tsv")
    assert {row["claim_class"] for row in assoc} == {"mechanism_hypothesis"}
    assert skipped[0]["criteria_id"] == "tmb"
    assert skipped[0]["route_to_spec"] == "spec020"


def test_interpret_epi_infer_emits_proxy_scores_and_associations(tmp_path: Path) -> None:
    root, _ = _fixture_root(tmp_path)
    out = root / "interpretation"
    assert main(["interpret", "epi-infer", "--results-root", str(root), "--out", str(out), "--run-manifest", str(tmp_path / "run.yaml")]) == 0
    scores = read_tsv(out / "epigenetic" / "inferred_scores.tsv")
    assoc = read_tsv(out / "epigenetic" / "epi_response_assoc.tsv")
    assert scores
    assert assoc
    assert {row["method"] for row in scores} == {"ssgsea_epigenetic_layer_proxy"}
    assert {row["claim_class"] for row in scores} == {"mechanism_hypothesis"}
