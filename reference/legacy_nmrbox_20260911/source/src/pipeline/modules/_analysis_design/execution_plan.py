from __future__ import annotations

import shlex
from pathlib import Path

from ...common.io import read_tsv, write_tsv


PILOT_ANALYSIS_IDS = {
    "PRE_RESPONSE",
    "PAN_ICB_RESPONSE__PRE_TREATMENT",
    "ICI_COMBINATION_RESPONSE__PRE_TREATMENT",
}

EXECUTION_PLAN_FIELDS = [
    "analysis_id",
    "analysis_family",
    "legacy_contrast_alias",
    "timing_scope",
    "stage",
    "command",
    "output_dir",
    "expected_input_registry",
    "expected_input_membership",
    "n_cohorts_eligible",
    "n_case_samples",
    "n_control_samples",
    "plan_status",
    "notes",
]


def _q(value: str | Path) -> str:
    return shlex.quote(str(value))


def _command(parts: list[str]) -> str:
    return " ".join(_q(part) for part in parts if str(part))


def build_local_execution_plan(
    *,
    registry_path: Path,
    membership_path: Path,
    out_dir: Path,
    execution_root: Path,
    sample_manifest: Path,
    expression_manifest: Path,
    downloads_root: Path,
    gene_id_mapping: Path,
    python_executable: str = "python3.13",
    count_method: str = "deseq2",
    analysis_ids: set[str] | None = None,
    pilot_only: bool = False,
    stages: set[str] | None = None,
    allow_weak_gene_mapping: bool = False,
    allow_welch_fallback: bool = False,
    skip_forest_plots: bool = True,
) -> Path:
    """Write a dry-run local execution plan for feasible Spec 026 analyses."""

    selected_ids = set(analysis_ids or set())
    if pilot_only:
        selected_ids = selected_ids & PILOT_ANALYSIS_IDS if selected_ids else set(PILOT_ANALYSIS_IDS)
    selected_stages = stages or {"stage06_de", "stage07_meta"}

    rows_out: list[dict[str, str]] = []
    registry_rows = read_tsv(registry_path)
    for row in registry_rows:
        if row.get("feasibility_status", "") != "feasible":
            continue
        analysis_id = row.get("analysis_id", "")
        if selected_ids and analysis_id not in selected_ids:
            continue
        contrast = row.get("legacy_contrast_alias", "") or row.get("contrast_type", "")
        family = row.get("analysis_family", "")
        output_de_dir = execution_root / "de"
        output_meta_dir = execution_root / "meta"
        run_manifest = execution_root / "logs" / "run_manifest.yaml"
        comparison_registry = execution_root / "comparison_registry.tsv"

        if "stage06_de" in selected_stages:
            de_parts = [
                python_executable,
                "-m",
                "src.pipeline.cli",
                "de",
                "run",
                "--contrast",
                contrast,
                "--analysis-id",
                analysis_id,
                "--analysis-registry",
                registry_path,
                "--analysis-membership",
                membership_path,
                "--sample-manifest",
                sample_manifest,
                "--expression-manifest",
                expression_manifest,
                "--downloads-root",
                downloads_root,
                "--count-method",
                count_method,
                "--gene-id-mapping",
                gene_id_mapping,
                "--comparison-registry",
                comparison_registry,
                "--out",
                output_de_dir,
                "--run-manifest",
                run_manifest,
            ]
            if allow_weak_gene_mapping:
                de_parts.append("--allow-weak-gene-mapping")
            if allow_welch_fallback:
                de_parts.append("--allow-welch-fallback")
            rows_out.append(
                {
                    "analysis_id": analysis_id,
                    "analysis_family": family,
                    "legacy_contrast_alias": contrast,
                    "timing_scope": row.get("timing_scope", ""),
                    "stage": "stage06_de",
                    "command": _command(de_parts),
                    "output_dir": str(output_de_dir / analysis_id),
                    "expected_input_registry": str(registry_path),
                    "expected_input_membership": str(membership_path),
                    "n_cohorts_eligible": row.get("n_cohorts_eligible", ""),
                    "n_case_samples": row.get("n_case_samples", ""),
                    "n_control_samples": row.get("n_control_samples", ""),
                    "plan_status": "planned_dry_run",
                    "notes": "review command before execution",
                }
            )

        if "stage07_meta" in selected_stages:
            meta_parts = [
                python_executable,
                "-m",
                "src.pipeline.cli",
                "meta",
                "run",
                "--contrast",
                contrast,
                "--analysis-id",
                analysis_id,
                "--de-dir",
                output_de_dir,
                "--sample-manifest",
                sample_manifest,
                "--comparison-registry",
                comparison_registry,
                "--out",
                output_meta_dir,
                "--run-manifest",
                run_manifest,
            ]
            if skip_forest_plots:
                meta_parts.append("--skip-forest-plots")
            rows_out.append(
                {
                    "analysis_id": analysis_id,
                    "analysis_family": family,
                    "legacy_contrast_alias": contrast,
                    "timing_scope": row.get("timing_scope", ""),
                    "stage": "stage07_meta",
                    "command": _command(meta_parts),
                    "output_dir": str(output_meta_dir / analysis_id),
                    "expected_input_registry": str(registry_path),
                    "expected_input_membership": str(membership_path),
                    "n_cohorts_eligible": row.get("n_cohorts_eligible", ""),
                    "n_case_samples": row.get("n_case_samples", ""),
                    "n_control_samples": row.get("n_control_samples", ""),
                    "plan_status": "planned_dry_run",
                    "notes": "requires completed stage06_de for same analysis_id",
                }
            )

    plan_path = out_dir / "analysis_execution_plan.tsv"
    write_tsv(plan_path, fieldnames=EXECUTION_PLAN_FIELDS, rows=rows_out)
    return plan_path
