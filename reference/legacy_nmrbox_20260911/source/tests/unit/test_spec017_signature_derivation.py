from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_signature_derive
from src.pipeline.common.io import read_tsv, write_tsv


META_FIELDS = [
    "analysis_id",
    "gene_id",
    "original_gene_id",
    "gene_symbol",
    "meta_effect_random",
    "meta_se_random",
    "meta_fdr",
    "heterogeneity_i2",
    "tau_squared",
    "n_cohorts_contributed",
    "n_patients_contributed",
    "direction_consistency",
    "effect_scale",
    "effect_scale_status",
]


def _args(tmp_path: Path, meta_path: Path, out_dir: Path, **overrides: object) -> Namespace:
    values = {
        "analysis_id": "PRE_RESPONSE",
        "contrast": "",
        "run_root": "",
        "meta_dir": str(meta_path),
        "composition_adjusted_meta_dir": "",
        "comparison_registry": "",
        "thresholds": "configs/signature_thresholds.yaml",
        "module_rules": "configs/signature_module_rules.tsv",
        "out": str(out_dir),
        "min_meta_cohorts": 2,
        "allow_empty_signature": False,
        "run_manifest": str(tmp_path / "logs/run_manifest.yaml"),
    }
    values.update(overrides)
    return Namespace(**values)


def test_signature_derive_blocks_when_common_scale_provenance_missing(tmp_path: Path) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    write_tsv(
        meta_dir / "meta_effects.tsv",
        fieldnames=[f for f in META_FIELDS if f not in {"effect_scale", "effect_scale_status"}],
        rows=[
            {
                "analysis_id": "PRE_RESPONSE",
                "gene_id": "CXCL9",
                "original_gene_id": "CXCL9",
                "gene_symbol": "CXCL9",
                "meta_effect_random": "1.5",
                "meta_se_random": "0.2",
                "meta_fdr": "0.01",
                "heterogeneity_i2": "20",
                "tau_squared": "0.01",
                "n_cohorts_contributed": "3",
                "n_patients_contributed": "90",
                "direction_consistency": "1.0",
            }
        ],
    )

    out_dir = tmp_path / "signature"
    assert cmd_signature_derive(_args(tmp_path, meta_dir, out_dir)) == 0

    audit = read_tsv(out_dir / "signature_derivation_audit.tsv")
    assert audit[0]["status"] == "blocked"
    assert audit[0]["reason"] == "missing_common_scale_provenance"
    assert read_tsv(out_dir / "signature_registry.tsv") == []
    assert (out_dir / "signature_thresholds.yaml").exists()


def test_signature_derive_writes_registry_tiers_modules_and_legacy_bridge(tmp_path: Path) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    write_tsv(
        meta_dir / "meta_effects.tsv",
        fieldnames=META_FIELDS,
        rows=[
            {
                "analysis_id": "PRE_RESPONSE",
                "gene_id": "CXCL9",
                "original_gene_id": "CXCL9",
                "gene_symbol": "CXCL9",
                "meta_effect_random": "1.5",
                "meta_se_random": "0.2",
                "meta_fdr": "0.01",
                "heterogeneity_i2": "20",
                "tau_squared": "0.01",
                "n_cohorts_contributed": "3",
                "n_patients_contributed": "90",
                "direction_consistency": "1.0",
                "effect_scale": "common_log2_response_logfc",
                "effect_scale_status": "common_scale",
            },
            {
                "analysis_id": "PRE_RESPONSE",
                "gene_id": "EZH2",
                "original_gene_id": "EZH2",
                "gene_symbol": "EZH2",
                "meta_effect_random": "-0.7",
                "meta_se_random": "0.3",
                "meta_fdr": "0.10",
                "heterogeneity_i2": "50",
                "tau_squared": "0.02",
                "n_cohorts_contributed": "4",
                "n_patients_contributed": "120",
                "direction_consistency": "0.8",
                "effect_scale": "common_log2_response_logfc",
                "effect_scale_status": "common_scale",
            },
            {
                "analysis_id": "PRE_RESPONSE",
                "gene_id": "NOISE1",
                "original_gene_id": "NOISE1",
                "gene_symbol": "NOISE1",
                "meta_effect_random": "0.9",
                "meta_se_random": "0.4",
                "meta_fdr": "0.60",
                "heterogeneity_i2": "90",
                "tau_squared": "0.9",
                "n_cohorts_contributed": "4",
                "n_patients_contributed": "120",
                "direction_consistency": "0.8",
                "effect_scale": "common_log2_response_logfc",
                "effect_scale_status": "common_scale",
            },
        ],
    )

    out_dir = tmp_path / "signature"
    assert cmd_signature_derive(_args(tmp_path, meta_dir, out_dir)) == 0

    registry = read_tsv(out_dir / "signature_registry.tsv")
    by_gene = {row["gene_id"]: row for row in registry}
    assert set(by_gene) == {"CXCL9", "EZH2"}
    assert by_gene["CXCL9"]["evidence_tier"] == "tier_1"
    assert by_gene["CXCL9"]["module_id"] == "chemokine_recruitment"
    assert by_gene["CXCL9"]["analysis_id"] == "PRE_RESPONSE"
    assert by_gene["CXCL9"]["analysis_family"] == "PRE_RESPONSE"
    assert by_gene["CXCL9"]["timing_label"] == "pre-treatment"
    assert by_gene["CXCL9"]["n_cohorts_contributed"] == "3"
    assert by_gene["EZH2"]["evidence_tier"] == "tier_2"
    assert by_gene["EZH2"]["module_id"] == "epigenetic_repression"

    core = read_tsv(out_dir / "responder_signature_core.tsv")
    assert [row["gene_id"] for row in core] == ["CXCL9"]
    tiered = read_tsv(out_dir / "responder_signature_tiered.tsv")
    assert len(tiered) == 2
    legacy = read_tsv(out_dir / "pre_response_signature_v1.tsv")
    assert {row["signature_variant"] for row in legacy} == {"composition_unadjusted_primary"}

    audit = read_tsv(out_dir / "signature_derivation_audit.tsv")
    assert audit[0]["status"] == "completed"
    assert audit[0]["n_selected_core"] == "1"
    assert audit[0]["n_selected_tiered"] == "2"
    assert (out_dir / "reproducibility" / "checksums.sha256").exists()


def test_signature_derive_emits_loco_manifest_from_comparison_registry(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    meta_dir = run_root / "meta" / "PRE_RESPONSE"
    meta_dir.mkdir(parents=True)
    write_tsv(
        meta_dir / "meta_effects.tsv",
        fieldnames=META_FIELDS,
        rows=[
            {
                "analysis_id": "PRE_RESPONSE",
                "gene_id": "HLA-A",
                "original_gene_id": "HLA-A",
                "gene_symbol": "HLA-A",
                "meta_effect_random": "1.2",
                "meta_se_random": "0.2",
                "meta_fdr": "0.02",
                "heterogeneity_i2": "20",
                "tau_squared": "0.01",
                "n_cohorts_contributed": "2",
                "n_patients_contributed": "60",
                "direction_consistency": "1.0",
                "effect_scale": "common_log2_response_logfc",
                "effect_scale_status": "common_scale",
            }
        ],
    )
    write_tsv(
        run_root / "comparison_registry.tsv",
        fieldnames=["analysis_id", "cohort_id"],
        rows=[
            {"analysis_id": "PRE_RESPONSE", "cohort_id": "cohort_a"},
            {"analysis_id": "PRE_RESPONSE", "cohort_id": "cohort_b"},
        ],
    )

    out_dir = tmp_path / "signature"
    args = _args(
        tmp_path,
        meta_dir,
        out_dir,
        analysis_id="PRE_RESPONSE",
        meta_dir="",
        run_root=str(run_root),
    )
    assert cmd_signature_derive(args) == 0

    loco = read_tsv(out_dir / "signature_loco_derivation_manifest.tsv")
    assert {row["holdout_cohort_id"] for row in loco} == {"cohort_a", "cohort_b"}
    assert {row["status"] for row in loco} == {"planned"}
    assert {row["reason"] for row in loco} == {"leave_one_cohort_out_derivation_plan"}
    assert "external" not in "\t".join("\t".join(row.values()).lower() for row in loco)
