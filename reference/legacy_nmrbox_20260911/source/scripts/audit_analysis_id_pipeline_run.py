#!/usr/bin/env python3
"""Audit a completed Spec-026 analysis-id pipeline run.

This script is intentionally read-mostly and claim-boundary focused. It does not
run pipeline stages. By default it refuses the committed reviewed pilot root so
Phase 3 audits are performed only on new full-run roots.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

REVIEWED_ROOT_TOKEN = "analysis_id_runs_t7_20260607_stage07_scale_provenance"
ALLOWED_INTERPRETATION_CLAIMS = {"discovery", "mechanism_hypothesis"}
ALLOWED_TCGA_BEHAVIORS = {"missing_tcga_map_status", "prognostic_tcga_projection"}
REQUIRED_HOPE_RNA = {
    "hope_checkpoint_expression",
    "hope_msi_dmmr_proxy",
    "hope_tcell_inflamed_gep",
    "hope_cytolytic_activity",
    "hope_ifng_signature",
    "hope_composite_rna",
}
REQUIRED_HOPE_NON_RNA_SPEC020 = {"tmb", "pdl1_ihc_tps_cps", "ecog_performance_status"}
REQUIRED_HOPE_NON_RNA_SPEC010 = {"irecist_pseudoprogression"}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["check", "scope", "status", "path", "detail"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, run_root: Path, rows: list[dict[str, str]], exit_code: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    failures = [row for row in rows if row["status"] == "fail"]
    warnings = [row for row in rows if row["status"] == "warn"]
    lines = [
        "# Analysis-ID Pipeline Post-Run Audit",
        "",
        f"- run_root: `{run_root}`",
        f"- status: `{'pass' if exit_code == 0 else 'fail'}`",
        f"- total_checks: {len(rows)}",
        "",
        "## Status Counts",
        "",
        "| status | count |",
        "|---|---:|",
    ]
    for status in ["pass", "warn", "fail"]:
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.extend(["", "## Failures", ""])
    if failures:
        lines.extend(["| check | scope | path | detail |", "|---|---|---|---|"])
        for row in failures[:20]:
            lines.append(
                f"| {row['check']} | {row['scope']} | `{row['path']}` | {row['detail']} |"
            )
    else:
        lines.append("No failing checks.")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(["| check | scope | path | detail |", "|---|---|---|---|"])
        for row in warnings[:20]:
            lines.append(
                f"| {row['check']} | {row['scope']} | `{row['path']}` | {row['detail']} |"
            )
    else:
        lines.append("No warnings.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "Spec 027 interpretation outputs must use only `mechanism_hypothesis` or `discovery` claim classes.",
            "TCGA remains prognostic context only, and LOCO remains internal robustness only.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, scope: str, status: str, path: Path | str, detail: str) -> None:
    rows.append(
        {
            "check": check,
            "scope": scope,
            "status": status,
            "path": str(path),
            "detail": detail,
        }
    )


def resolve_planned_path(raw: str, cwd: Path, run_root: Path | None = None) -> Path:
    path = Path(raw)
    if path.is_absolute():
        if path.exists() or run_root is None:
            return path
        parts = path.parts
        matches = [
            idx
            for idx, part in enumerate(parts)
            if part == run_root.name or part.startswith("analysis_id_pipeline_")
        ]
        if matches:
            for idx in reversed(matches):
                suffix = parts[idx + 1 :]
                candidate = run_root.joinpath(*suffix) if suffix else run_root
                if candidate.exists():
                    return candidate
        return path
    if run_root is not None:
        candidate = (run_root / path).resolve()
        if candidate.exists():
            return candidate
    return (cwd / path).resolve()


def has_payload(path: Path) -> bool:
    if path.is_file():
        return path.stat().st_size > 0
    if path.is_dir():
        return any(child.is_file() for child in path.rglob("*"))
    return False


def first_payload(paths: list[Path]) -> Path | None:
    for path in paths:
        if has_payload(path):
            return path
    return None


def resumed_global_stage_payload(stage: str, run_root: Path, audit_out: Path | None = None) -> Path | None:
    """Accept global resume stages only when their concrete outputs exist.

    A failed full run can be resumed after the original plan is written. In that
    case the plan is historical provenance, while these payloads prove the
    resumed global stages were materialized.
    """
    stage_outputs = {
        "interpret_hub_meta": [
            run_root / "interpretation" / "hub_meta" / "cross_cancer_hub_meta.tsv",
        ],
        "interpret_immunophenotype": [
            run_root / "interpretation" / "immunophenotype" / "sample_phenotype.tsv",
            run_root / "interpretation" / "immunophenotype" / "phenotype_response_assoc.tsv",
            run_root / "interpretation" / "immunophenotype" / "hope_skipped_criteria.tsv",
            run_root / "interpretation" / "immunophenotype" / "immunophenotype_input_audit.tsv",
        ],
        "interpret_epi_infer": [
            run_root / "interpretation" / "epigenetic" / "inferred_scores.tsv",
            run_root / "interpretation" / "epigenetic" / "epi_response_assoc.tsv",
            run_root / "interpretation" / "epigenetic" / "epi_input_audit.tsv",
        ],
        "report": [
            run_root / "reports" / "pipeline_summary.md",
            run_root / "reports" / "report.md",
        ],
        "postrun_audit": [
            run_root / "orchestration" / "postrun_audit.tsv",
            run_root / "orchestration" / "analysis_id_pipeline_postrun_audit.tsv",
        ],
    }
    candidates = stage_outputs.get(stage, [])
    if stage == "postrun_audit" and audit_out is not None:
        candidates = [audit_out, *candidates]
    return first_payload(candidates)


def planned_stages(plan_path: Path) -> list[dict[str, str]]:
    if not plan_path.exists():
        return []
    return read_tsv(plan_path)


def read_key_value_manifest(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if reader.fieldnames != ["key", "value"]:
            raise ValueError("expected columns key,value")
        return {row.get("key", ""): row.get("value", "") for row in reader if row.get("key")}


def derive_analysis_ids(plan_rows: list[dict[str, str]], run_root: Path) -> list[str]:
    ids = {
        row.get("analysis_id", "")
        for row in plan_rows
        if row.get("analysis_id") and row.get("analysis_id") != "ALL"
    }
    meta_root = run_root / "meta"
    if meta_root.exists():
        ids.update(p.name for p in meta_root.iterdir() if p.is_dir())
    return sorted(ids)


def audit_execution_decision_manifest(rows: list[dict[str, str]], run_root: Path) -> None:
    path = run_root / "orchestration" / "phase3_execution_decision_manifest.tsv"
    if not path.exists() or path.stat().st_size == 0:
        add(rows, "execution_decision_manifest", "orchestration", "fail", path, "missing or empty")
        return
    try:
        manifest = read_key_value_manifest(path)
    except (OSError, csv.Error, UnicodeDecodeError, ValueError) as exc:
        add(rows, "execution_decision_manifest", "orchestration", "fail", path, f"unreadable decision manifest: {exc}")
        return

    required = {
        "analysis_scope_mode",
        "tcga_behavior",
        "execution_gate",
        "reviewed_root_guard",
        "claim_boundary",
        "track_boundary",
    }
    missing = sorted(key for key in required if not manifest.get(key, "").strip())
    problems: list[str] = []
    if missing:
        problems.append("missing keys=" + ",".join(missing))

    tcga_behavior = manifest.get("tcga_behavior", "").strip()
    if tcga_behavior and tcga_behavior not in ALLOWED_TCGA_BEHAVIORS:
        problems.append(f"tcga_behavior must be one of {','.join(sorted(ALLOWED_TCGA_BEHAVIORS))}; observed={tcga_behavior}")

    execution_gate = manifest.get("execution_gate", "")
    if "ALLOW_ANALYSIS_ID_PIPELINE_RUN=1" not in execution_gate:
        problems.append("execution_gate must document ALLOW_ANALYSIS_ID_PIPELINE_RUN=1")

    reviewed_root_guard = manifest.get("reviewed_root_guard", "")
    if REVIEWED_ROOT_TOKEN not in reviewed_root_guard:
        problems.append("reviewed_root_guard must document the frozen reviewed root token")

    claim_boundary = manifest.get("claim_boundary", "")
    for phrase in ["discovery/mechanism_hypothesis", "TCGA prognostic only", "LOCO internal only"]:
        if phrase not in claim_boundary:
            problems.append(f"claim_boundary missing phrase={phrase}")

    track_boundary = manifest.get("track_boundary", "")
    if "Track A" not in track_boundary or "Track B" not in track_boundary:
        problems.append("track_boundary must mention Track A and Track B")

    if problems:
        add(rows, "execution_decision_manifest", "orchestration", "fail", path, "; ".join(problems))
    else:
        scope = manifest.get("analysis_scope_mode", "")
        add(rows, "execution_decision_manifest", "orchestration", "pass", path, f"scope={scope}; tcga_behavior={tcga_behavior}")


def audit_interpretation_claims(rows: list[dict[str, str]], run_root: Path) -> None:
    interp = run_root / "interpretation"
    if not interp.exists():
        add(rows, "interpretation_claim_classes", "interpretation", "fail", interp, "interpretation directory missing")
        return
    checked = 0
    bad: list[str] = []
    for path in sorted(interp.rglob("*.tsv")):
        try:
            with path.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                fieldnames = reader.fieldnames or []
                table = list(reader)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            bad.append(f"{path}: unreadable TSV: {exc}")
            continue
        if "claim_class" not in fieldnames:
            bad.append(f"{path}: missing claim_class column")
            continue
        checked += 1
        claims = {(row.get("claim_class") or "").strip() for row in table}
        disallowed = sorted(claims - ALLOWED_INTERPRETATION_CLAIMS)
        if disallowed:
            rendered = ",".join(value if value else "<blank>" for value in disallowed)
            bad.append(f"{path}: disallowed claim_class={rendered}")
    if bad:
        add(rows, "interpretation_claim_classes", "interpretation", "fail", interp, "; ".join(bad[:10]))
    else:
        add(rows, "interpretation_claim_classes", "interpretation", "pass", interp, f"checked {checked} claim-class table(s); no missing/disallowed claims")


def interpretation_analysis_ids(plan_rows: list[dict[str, str]], stage: str, run_root: Path, subdir: str) -> list[str]:
    planned = sorted(
        {
            row.get("analysis_id", "")
            for row in plan_rows
            if row.get("stage", "") == stage and row.get("analysis_id", "") not in {"", "ALL"}
        }
    )
    if planned:
        return planned
    root = run_root / "interpretation" / subdir
    if root.exists():
        return sorted(path.name for path in root.iterdir() if path.is_dir())
    return []


def audit_interpretation_enrichment(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
) -> None:
    analysis_ids = interpretation_analysis_ids(plan_rows, "interpret_enrich", run_root, "enrichment")
    if not analysis_ids:
        add(rows, "interpretation_enrichment_contract", "interpretation", "fail", run_root / "interpretation" / "enrichment", "no enrichment analysis IDs found")
        return
    failures: list[str] = []
    for analysis_id in analysis_ids:
        out_dir = run_root / "interpretation" / "enrichment" / analysis_id
        for name in ["gsea.tsv", "ora.tsv", "dotplot_data.tsv"]:
            path = out_dir / name
            if not path.exists() or path.stat().st_size == 0:
                failures.append(f"{analysis_id}/{name}: missing or empty")
        gsea_path = out_dir / "gsea.tsv"
        if gsea_path.exists() and gsea_path.stat().st_size > 0:
            try:
                gsea_rows = read_tsv(gsea_path)
            except (OSError, csv.Error, UnicodeDecodeError) as exc:
                failures.append(f"{analysis_id}/gsea.tsv: unreadable: {exc}")
                continue
            if not gsea_rows:
                failures.append(f"{analysis_id}/gsea.tsv: no rows")
            elif "statistic" not in gsea_rows[0]:
                failures.append(f"{analysis_id}/gsea.tsv: missing statistic column")
            else:
                stats = {row.get("statistic", "").strip() for row in gsea_rows if row.get("statistic", "").strip()}
                if stats != {"meta_effect_random"}:
                    rendered = ",".join(sorted(stats)) if stats else "<blank>"
                    failures.append(f"{analysis_id}/gsea.tsv: statistic={rendered}")
    if failures:
        add(rows, "interpretation_enrichment_contract", "interpretation", "fail", run_root / "interpretation" / "enrichment", "; ".join(failures[:10]))
    else:
        add(rows, "interpretation_enrichment_contract", "interpretation", "pass", run_root / "interpretation" / "enrichment", f"checked {len(analysis_ids)} enrichment analysis_id(s); statistic=meta_effect_random")


def audit_interpretation_network(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
) -> None:
    analysis_ids = interpretation_analysis_ids(plan_rows, "interpret_network", run_root, "network")
    if not analysis_ids:
        add(rows, "interpretation_network_contract", "interpretation", "fail", run_root / "interpretation" / "network", "no network analysis IDs found")
        return
    failures: list[str] = []
    insufficient = 0
    for analysis_id in analysis_ids:
        hub_path = run_root / "interpretation" / "network" / analysis_id / "hub_genes.tsv"
        if not hub_path.exists() or hub_path.stat().st_size == 0:
            failures.append(f"{analysis_id}/hub_genes.tsv: missing or empty")
            continue
        try:
            hub_rows = read_tsv(hub_path)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            failures.append(f"{analysis_id}/hub_genes.tsv: unreadable: {exc}")
            continue
        header = set(hub_rows[0]) if hub_rows else set()
        missing = sorted({"permutation_fdr", "status"} - header)
        if missing:
            failures.append(f"{analysis_id}/hub_genes.tsv: missing columns={','.join(missing)}")
            continue
        statuses = {row.get("status", "").strip() for row in hub_rows if row.get("status", "").strip()}
        if "insufficient_signal" in statuses:
            insufficient += 1
    if failures:
        add(rows, "interpretation_network_contract", "interpretation", "fail", run_root / "interpretation" / "network", "; ".join(failures[:10]))
    else:
        add(rows, "interpretation_network_contract", "interpretation", "pass", run_root / "interpretation" / "network", f"checked {len(analysis_ids)} network analysis_id(s); insufficient_signal={insufficient}")


def audit_interpretation_hub_meta(rows: list[dict[str, str]], run_root: Path, plan_rows: list[dict[str, str]]) -> None:
    planned = any(row.get("stage", "") == "interpret_hub_meta" for row in plan_rows)
    hub_path = run_root / "interpretation" / "hub_meta" / "cross_cancer_hub_meta.tsv"
    if not planned and not hub_path.exists():
        return
    if not hub_path.exists() or hub_path.stat().st_size == 0:
        add(rows, "interpretation_hub_meta_contract", "interpretation", "fail", hub_path, "missing or empty")
        return
    try:
        hub_rows = read_tsv(hub_path)
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        add(rows, "interpretation_hub_meta_contract", "interpretation", "fail", hub_path, f"unreadable: {exc}")
        return
    header = set(hub_rows[0]) if hub_rows else set()
    missing = sorted({"moderator_status", "status"} - header)
    if missing:
        add(rows, "interpretation_hub_meta_contract", "interpretation", "fail", hub_path, "missing columns=" + ",".join(missing))
        return
    moderator_values = {row.get("moderator_status", "").strip() for row in hub_rows}
    if "cancer_as_low_dimension_moderator_only" not in moderator_values:
        add(rows, "interpretation_hub_meta_contract", "interpretation", "fail", hub_path, "missing cancer_as_low_dimension_moderator_only moderator status")
    else:
        add(rows, "interpretation_hub_meta_contract", "interpretation", "pass", hub_path, "cancer retained as low-dimensional moderator")


def audit_interpretation_immunophenotype(rows: list[dict[str, str]], run_root: Path, plan_rows: list[dict[str, str]]) -> None:
    planned = any(row.get("stage", "") == "interpret_immunophenotype" for row in plan_rows)
    root = run_root / "interpretation" / "immunophenotype"
    if not planned and not root.exists():
        return
    required = ["sample_phenotype.tsv", "phenotype_response_assoc.tsv", "hope_skipped_criteria.tsv", "immunophenotype_input_audit.tsv"]
    failures = [f"{name}: missing or empty" for name in required if not (root / name).exists() or (root / name).stat().st_size == 0]
    if failures:
        add(rows, "interpretation_immunophenotype_contract", "interpretation", "fail", root, "; ".join(failures))
        return

    try:
        sample_rows = read_tsv(root / "sample_phenotype.tsv")
        skipped_rows = read_tsv(root / "hope_skipped_criteria.tsv")
        audit_rows = read_tsv(root / "immunophenotype_input_audit.tsv")
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        add(rows, "interpretation_immunophenotype_contract", "interpretation", "fail", root, f"unreadable TSV: {exc}")
        return

    scored_ids = {row.get("criteria_id", "").strip() for row in sample_rows if row.get("criteria_id", "").strip()}
    audited_ids = {
        row.get("input_name", "").strip()
        for row in audit_rows
        if row.get("input_name", "").strip() and row.get("status", "").strip() not in {"", "ok"}
    }
    unresolved_rna = sorted(REQUIRED_HOPE_RNA - scored_ids - audited_ids)

    skipped_by_id = {row.get("criteria_id", "").strip(): row for row in skipped_rows if row.get("criteria_id", "").strip()}
    missing_non_rna = sorted((REQUIRED_HOPE_NON_RNA_SPEC020 | REQUIRED_HOPE_NON_RNA_SPEC010) - set(skipped_by_id))
    bad_routes: list[str] = []
    for criteria_id in sorted(REQUIRED_HOPE_NON_RNA_SPEC020):
        row = skipped_by_id.get(criteria_id, {})
        if row and row.get("route_to_spec", "").strip() != "spec020":
            bad_routes.append(f"{criteria_id}:route_to_spec={row.get('route_to_spec', '<blank>')}")
        if row and not row.get("skip_reason", "").strip():
            bad_routes.append(f"{criteria_id}:missing skip_reason")
    for criteria_id in sorted(REQUIRED_HOPE_NON_RNA_SPEC010):
        row = skipped_by_id.get(criteria_id, {})
        if row and row.get("route_to_spec", "").strip() != "spec010":
            bad_routes.append(f"{criteria_id}:route_to_spec={row.get('route_to_spec', '<blank>')}")
        if row and not row.get("skip_reason", "").strip():
            bad_routes.append(f"{criteria_id}:missing skip_reason")

    problems: list[str] = []
    if unresolved_rna:
        problems.append("RNA criteria neither scored nor audited=" + ",".join(unresolved_rna))
    if missing_non_rna:
        problems.append("missing skipped non-RNA criteria=" + ",".join(missing_non_rna))
    if bad_routes:
        problems.append("bad non-RNA handoff rows=" + ",".join(bad_routes))
    if problems:
        add(rows, "interpretation_immunophenotype_contract", "interpretation", "fail", root, "; ".join(problems))
    else:
        add(rows, "interpretation_immunophenotype_contract", "interpretation", "pass", root, "HOPE RNA criteria scored or audited; non-RNA criteria skipped with routes")


def audit_interpretation_epigenetic(rows: list[dict[str, str]], run_root: Path, plan_rows: list[dict[str, str]]) -> None:
    planned = any(row.get("stage", "") == "interpret_epi_infer" for row in plan_rows)
    root = run_root / "interpretation" / "epigenetic"
    if not planned and not root.exists():
        return
    required = ["inferred_scores.tsv", "epi_response_assoc.tsv", "epi_input_audit.tsv"]
    missing = [name for name in required if not (root / name).exists() or (root / name).stat().st_size == 0]
    if missing:
        add(rows, "interpretation_epigenetic_contract", "interpretation", "fail", root, "missing files=" + ",".join(missing))
    else:
        add(rows, "interpretation_epigenetic_contract", "interpretation", "pass", root, "RNA-inferred epigenetic proxy outputs present")


def audit_interpretation_contracts(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
) -> None:
    audit_interpretation_enrichment(rows, run_root, plan_rows)
    audit_interpretation_network(rows, run_root, plan_rows)
    audit_interpretation_hub_meta(rows, run_root, plan_rows)
    audit_interpretation_immunophenotype(rows, run_root, plan_rows)
    audit_interpretation_epigenetic(rows, run_root, plan_rows)


def audit_tcga_outcome(rows: list[dict[str, str]], run_root: Path, analysis_id: str) -> None:
    tcga_dir = run_root / "tcga_projection" / analysis_id
    status_file = tcga_dir / "tcga_projection_status.tsv"
    if status_file.exists() and status_file.stat().st_size > 0:
        try:
            with status_file.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                fieldnames = set(reader.fieldnames or [])
                status_rows = list(reader)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            add(rows, "tcga_outcome", analysis_id, "fail", status_file, f"unreadable status TSV: {exc}")
            return
        missing = sorted({"stage", "status"} - fieldnames)
        if missing:
            add(rows, "tcga_outcome", analysis_id, "fail", status_file, "missing columns=" + ",".join(missing))
            return
        blocked_without_reason = [
            row
            for row in status_rows
            if row.get("status", "").strip().lower() in {"blocked", "skipped"}
            and not row.get("reason", "").strip()
        ]
        if blocked_without_reason:
            add(rows, "tcga_outcome", analysis_id, "fail", status_file, "blocked/skipped TCGA rows must include a reason")
            return
        statuses = sorted({row.get("status", "").strip() for row in status_rows if row.get("status", "").strip()})
        reasons = sorted({row.get("reason", "").strip() for row in status_rows if row.get("reason", "").strip()})
        detail = "status_file present"
        if statuses:
            detail += "; statuses=" + ",".join(statuses)
        if reasons:
            detail += "; reasons=" + ",".join(reasons)
        add(rows, "tcga_outcome", analysis_id, "pass", status_file, detail)
        return

    survival_stats = sorted(tcga_dir.glob("*_survival_stats.tsv")) if tcga_dir.exists() else []
    if survival_stats:
        add(rows, "tcga_outcome", analysis_id, "pass", survival_stats[0], f"survival stats present; n_files={len(survival_stats)}")
    else:
        add(rows, "tcga_outcome", analysis_id, "fail", status_file, "missing tcga_projection_status.tsv or survival stats")


def audit_immune_effects_contract(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
) -> None:
    planned = any(row.get("stage", "") == "immune_effects" for row in plan_rows)
    root = run_root / "immune_state"
    effects_path = root / "cohort_level_effects.tsv"
    if not planned and not effects_path.exists():
        return

    required_files = {
        "cohort_level_effects.tsv": effects_path,
        "immune_effects_input_audit.tsv": root / "immune_effects_input_audit.tsv",
        "marker_correlations.tsv": root / "marker_correlations.tsv",
    }
    missing_files = [
        name
        for name, path in required_files.items()
        if not path.exists() or path.stat().st_size == 0
    ]
    if missing_files:
        add(rows, "immune_effects_contract", "immune_state", "fail", root, "missing or empty files=" + ",".join(missing_files))
        return

    try:
        effect_rows = read_tsv(effects_path)
        audit_rows = read_tsv(root / "immune_effects_input_audit.tsv")
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        add(rows, "immune_effects_contract", "immune_state", "fail", root, f"unreadable TSV: {exc}")
        return

    problems: list[str] = []
    effect_header = set(effect_rows[0]) if effect_rows else set()
    required_effect_cols = {
        "cohort_id",
        "contrast_family",
        "immune_feature",
        "feature_source",
        "effect_type",
        "effect_size",
        "p_value",
        "fdr",
        "model_class",
        "analysis_mode",
        "n_responders",
        "n_non_responders",
    }
    missing_cols = sorted(required_effect_cols - effect_header)
    if missing_cols:
        problems.append("cohort_level_effects.tsv missing columns=" + ",".join(missing_cols))
    if not effect_rows:
        problems.append("cohort_level_effects.tsv has no association rows")

    audit_header = set(audit_rows[0]) if audit_rows else set()
    required_audit_cols = {"cohort_id", "marker_correlation_status", "marker_correlations_emitted", "note"}
    missing_audit_cols = sorted(required_audit_cols - audit_header)
    if missing_audit_cols:
        problems.append("immune_effects_input_audit.tsv missing columns=" + ",".join(missing_audit_cols))
    if not audit_rows:
        problems.append("immune_effects_input_audit.tsv has no cohort audit rows")

    ssgsea_long_path = root / "ssgsea_scores_long.tsv"
    if ssgsea_long_path.exists() and ssgsea_long_path.stat().st_size > 0:
        try:
            ssgsea_rows = read_tsv(ssgsea_long_path)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            problems.append(f"ssgsea_scores_long.tsv unreadable: {exc}")
            ssgsea_rows = []
        if ssgsea_rows:
            sources = {row.get("feature_source", "").strip() for row in effect_rows}
            if "gsva_ssgsea" not in sources:
                problems.append("non-empty ssGSEA scores require cohort-level feature_source=gsva_ssgsea")

    if problems:
        add(rows, "immune_effects_contract", "immune_state", "fail", root, "; ".join(problems))
    else:
        sources = sorted({row.get("feature_source", "").strip() for row in effect_rows if row.get("feature_source", "").strip()})
        add(
            rows,
            "immune_effects_contract",
            "immune_state",
            "pass",
            root,
            f"checked {len(effect_rows)} immune-effect association row(s); feature_sources={','.join(sources)}",
        )


def audit_comparison_registry_merge(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
    analysis_ids: list[str],
) -> None:
    merge_planned = any(row.get("stage", "") == "comparison_registry_merge" for row in plan_rows)
    registry_dir = run_root / "comparison_registry_by_analysis"
    if not merge_planned and not registry_dir.exists():
        return

    registry_out = run_root / "comparison_registry.tsv"
    if not registry_dir.exists():
        add(rows, "comparison_registry_merge_inputs", "ALL", "fail", registry_dir, "missing per-analysis registry directory")
        return

    missing_inputs = [
        analysis_id
        for analysis_id in analysis_ids
        if not (registry_dir / f"{analysis_id}.tsv").exists()
        or (registry_dir / f"{analysis_id}.tsv").stat().st_size == 0
    ]
    if missing_inputs:
        add(
            rows,
            "comparison_registry_merge_inputs",
            "ALL",
            "fail",
            registry_dir,
            "missing or empty per-analysis registries=" + ",".join(missing_inputs),
        )
    else:
        add(
            rows,
            "comparison_registry_merge_inputs",
            "ALL",
            "pass",
            registry_dir,
            f"per-analysis registries present for {len(analysis_ids)} analysis_id(s)",
        )

    try:
        merged_rows = read_tsv(registry_out)
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        add(rows, "comparison_registry_merge_output", "ALL", "fail", registry_out, f"unreadable merged registry: {exc}")
        return

    if not merged_rows:
        add(rows, "comparison_registry_merge_output", "ALL", "fail", registry_out, "merged comparison registry has no rows")
        return
    if "analysis_id" not in merged_rows[0]:
        add(rows, "comparison_registry_merge_output", "ALL", "fail", registry_out, "merged registry missing analysis_id column")
        return
    observed = {row.get("analysis_id", "") for row in merged_rows if row.get("analysis_id", "")}
    missing_merged = sorted(set(analysis_ids) - observed)
    if missing_merged:
        add(
            rows,
            "comparison_registry_merge_output",
            "ALL",
            "fail",
            registry_out,
            "merged registry missing analysis IDs=" + ",".join(missing_merged),
        )
    else:
        add(
            rows,
            "comparison_registry_merge_output",
            "ALL",
            "pass",
            registry_out,
            f"merged registry contains {len(observed)} analysis_id(s)",
        )


def audit_run_manifest_merge(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
    analysis_ids: list[str],
) -> None:
    merge_planned = any(row.get("stage", "") == "run_manifest_merge" for row in plan_rows)
    manifest_dir = run_root / "logs" / "job_manifests"
    if not merge_planned and not manifest_dir.exists():
        return

    canonical = run_root / "logs" / "run_manifest.yaml"
    if not manifest_dir.exists():
        add(rows, "run_manifest_merge_inputs", "ALL", "fail", manifest_dir, "missing per-job run-manifest directory")
        return

    expected = [manifest_dir / "design.jsonl", manifest_dir / "immune.jsonl", manifest_dir / "finalize.jsonl"]
    expected.extend(manifest_dir / f"analysis_{analysis_id}.jsonl" for analysis_id in analysis_ids)
    missing = [path.name for path in expected if not path.exists() or path.stat().st_size == 0]
    if missing:
        add(
            rows,
            "run_manifest_merge_inputs",
            "ALL",
            "fail",
            manifest_dir,
            "missing or empty run-manifest shards=" + ",".join(missing),
        )
        return
    add(
        rows,
        "run_manifest_merge_inputs",
        "ALL",
        "pass",
        manifest_dir,
        f"run-manifest shards present for {len(analysis_ids)} analysis_id(s)",
    )

    try:
        canonical_text = canonical.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        add(rows, "run_manifest_merge_output", "ALL", "fail", canonical, f"unreadable merged run manifest: {exc}")
        return
    if not canonical_text.strip():
        add(rows, "run_manifest_merge_output", "ALL", "fail", canonical, "merged run manifest is empty")
        return

    missing_lines: list[str] = []
    for shard in expected:
        try:
            shard_lines = [line for line in shard.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, UnicodeDecodeError) as exc:
            add(rows, "run_manifest_merge_output", "ALL", "fail", shard, f"unreadable run-manifest shard: {exc}")
            return
        for line in shard_lines:
            if line not in canonical_text:
                missing_lines.append(shard.name)
                break
    if missing_lines:
        add(
            rows,
            "run_manifest_merge_output",
            "ALL",
            "fail",
            canonical,
            "merged run manifest missing shard content=" + ",".join(missing_lines),
        )
    else:
        add(
            rows,
            "run_manifest_merge_output",
            "ALL",
            "pass",
            canonical,
            f"merged run manifest includes {len(expected)} shard(s)",
        )


def audit_bibalex_multijob_manifest(
    rows: list[dict[str, str]],
    run_root: Path,
    plan_rows: list[dict[str, str]],
    analysis_ids: list[str],
) -> None:
    multi_job_planned = any(
        row.get("stage", "") in {"comparison_registry_merge", "run_manifest_merge"}
        for row in plan_rows
    )
    manifest_path = run_root / "orchestration" / "bibalex_multijob_submission_manifest.tsv"
    if not multi_job_planned and not manifest_path.exists():
        return
    if not manifest_path.exists() or manifest_path.stat().st_size == 0:
        add(rows, "bibalex_multijob_submission_manifest", "orchestration", "fail", manifest_path, "missing or empty")
        return
    try:
        manifest = read_key_value_manifest(manifest_path)
    except (OSError, csv.Error, UnicodeDecodeError, ValueError) as exc:
        add(rows, "bibalex_multijob_submission_manifest", "orchestration", "fail", manifest_path, f"unreadable manifest: {exc}")
        return

    required = {
        "design_job_id",
        "immune_job_id",
        "analysis_job_ids",
        "final_job_id",
        "analysis_ids",
        "comparison_registry_strategy",
        "run_manifest_strategy",
        "claim_boundary",
        "track_boundary",
    }
    problems: list[str] = []
    missing = sorted(key for key in required if not manifest.get(key, "").strip())
    if missing:
        problems.append("missing keys=" + ",".join(missing))
    if manifest.get("comparison_registry_strategy", "") != "per_analysis_shards_final_merge":
        problems.append("comparison_registry_strategy must be per_analysis_shards_final_merge")
    if manifest.get("run_manifest_strategy", "") != "per_job_shards_final_merge":
        problems.append("run_manifest_strategy must be per_job_shards_final_merge")
    recorded_analysis_ids = set(manifest.get("analysis_ids", "").replace(",", " ").split())
    missing_analysis_ids = sorted(set(analysis_ids) - recorded_analysis_ids)
    if missing_analysis_ids:
        problems.append("analysis_ids missing audited IDs=" + ",".join(missing_analysis_ids))
    claim_boundary = manifest.get("claim_boundary", "")
    for phrase in ["discovery/mechanism_hypothesis", "TCGA prognostic only", "LOCO internal only"]:
        if phrase not in claim_boundary:
            problems.append(f"claim_boundary missing phrase={phrase}")
    track_boundary = manifest.get("track_boundary", "")
    if "Track A" not in track_boundary or "Track B" not in track_boundary:
        problems.append("track_boundary must mention Track A and Track B")

    if problems:
        add(rows, "bibalex_multijob_submission_manifest", "orchestration", "fail", manifest_path, "; ".join(problems))
    else:
        add(
            rows,
            "bibalex_multijob_submission_manifest",
            "orchestration",
            "pass",
            manifest_path,
            f"job provenance present for {len(analysis_ids)} analysis_id(s)",
        )


def audit_bibalex_singlejob_manifest(rows: list[dict[str, str]], run_root: Path) -> None:
    manifest_path = run_root / "orchestration" / "bibalex_singlejob_submission_manifest.tsv"
    if not manifest_path.exists():
        return
    if manifest_path.stat().st_size == 0:
        add(rows, "bibalex_singlejob_submission_manifest", "orchestration", "fail", manifest_path, "missing or empty")
        return
    try:
        manifest = read_key_value_manifest(manifest_path)
    except (OSError, csv.Error, UnicodeDecodeError, ValueError) as exc:
        add(rows, "bibalex_singlejob_submission_manifest", "orchestration", "fail", manifest_path, f"unreadable manifest: {exc}")
        return

    required = {
        "backend",
        "slurm_job_id",
        "job_name",
        "run_tag",
        "out_root",
        "downloads_root",
        "portable_r_conda_prefix",
        "sample_manifest",
        "expression_manifest",
        "gene_id_mapping",
        "gene_set_registry",
        "criteria_registry",
        "count_method",
        "allow_empty_signature",
        "allow_weak_gene_mapping",
        "allow_welch_fallback",
        "execution_gate",
        "claim_boundary",
        "track_boundary",
    }
    problems: list[str] = []
    missing = sorted(key for key in required if not manifest.get(key, "").strip())
    if missing:
        problems.append("missing keys=" + ",".join(missing))
    if manifest.get("backend", "") != "bibalex_single_job":
        problems.append("backend must be bibalex_single_job")
    execution_gate = manifest.get("execution_gate", "")
    if "ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1" not in execution_gate or "ALLOW_ANALYSIS_ID_PIPELINE_RUN=1" not in execution_gate:
        problems.append("execution_gate must document both BibaLex outer and local inner gates")
    claim_boundary = manifest.get("claim_boundary", "")
    for phrase in ["discovery/mechanism_hypothesis", "TCGA prognostic only", "LOCO internal only"]:
        if phrase not in claim_boundary:
            problems.append(f"claim_boundary missing phrase={phrase}")
    track_boundary = manifest.get("track_boundary", "")
    if "Track A" not in track_boundary or "Track B" not in track_boundary:
        problems.append("track_boundary must mention Track A and Track B")
    if manifest.get("portable_r_conda_prefix", "") == "<unset>":
        problems.append("portable_r_conda_prefix must record the Spec 094 runtime prefix for BibaLex single-job runs")

    if problems:
        add(rows, "bibalex_singlejob_submission_manifest", "orchestration", "fail", manifest_path, "; ".join(problems))
    else:
        add(rows, "bibalex_singlejob_submission_manifest", "orchestration", "pass", manifest_path, f"single-job provenance present for run_tag={manifest.get('run_tag', '')}")


def audit_nmrbox_condor_manifest(rows: list[dict[str, str]], run_root: Path) -> None:
    manifest_path = run_root / "orchestration" / "nmrbox_condor_submission_manifest.tsv"
    if not manifest_path.exists():
        return
    if manifest_path.stat().st_size == 0:
        add(rows, "nmrbox_condor_submission_manifest", "orchestration", "fail", manifest_path, "missing or empty")
        return
    try:
        manifest = read_key_value_manifest(manifest_path)
    except (OSError, csv.Error, UnicodeDecodeError, ValueError) as exc:
        add(rows, "nmrbox_condor_submission_manifest", "orchestration", "fail", manifest_path, f"unreadable manifest: {exc}")
        return

    required = {
        "backend",
        "condor_cluster_id",
        "condor_process_id",
        "job_name",
        "run_tag",
        "out_root",
        "remote_job_dir",
        "downloads_root",
        "portable_r_conda_prefix",
        "r_libs_user",
        "sample_manifest",
        "expression_manifest",
        "gene_id_mapping",
        "gene_set_registry",
        "criteria_registry",
        "count_method",
        "request_cpus",
        "request_memory",
        "request_disk",
        "execution_gate",
        "claim_boundary",
        "track_boundary",
    }
    problems: list[str] = []
    missing = sorted(key for key in required if not manifest.get(key, "").strip())
    if missing:
        problems.append("missing keys=" + ",".join(missing))
    if manifest.get("backend", "") != "nmrbox_condor_single_job":
        problems.append("backend must be nmrbox_condor_single_job")
    execution_gate = manifest.get("execution_gate", "")
    if "ALLOW_NMRBOX_ANALYSIS_ID_PIPELINE=1" not in execution_gate or "ALLOW_ANALYSIS_ID_PIPELINE_RUN=1" not in execution_gate:
        problems.append("execution_gate must document both NMRbox outer and local inner gates")
    claim_boundary = manifest.get("claim_boundary", "")
    for phrase in ["discovery/mechanism_hypothesis", "TCGA prognostic only", "LOCO internal only"]:
        if phrase not in claim_boundary:
            problems.append(f"claim_boundary missing phrase={phrase}")
    track_boundary = manifest.get("track_boundary", "")
    if "Track A" not in track_boundary or "Track B" not in track_boundary:
        problems.append("track_boundary must mention Track A and Track B")
    if manifest.get("r_libs_user", "") == "<unset>":
        problems.append("r_libs_user must record the NMRbox R package library path")

    if problems:
        add(rows, "nmrbox_condor_submission_manifest", "orchestration", "fail", manifest_path, "; ".join(problems))
    else:
        add(rows, "nmrbox_condor_submission_manifest", "orchestration", "pass", manifest_path, f"NMRbox Condor provenance present for run_tag={manifest.get('run_tag', '')}")


def audit_run(args: argparse.Namespace) -> tuple[int, list[dict[str, str]]]:
    run_root = Path(args.run_root).resolve()
    cwd = Path.cwd().resolve()
    rows: list[dict[str, str]] = []

    if REVIEWED_ROOT_TOKEN in str(run_root) and not args.allow_reviewed_root:
        add(rows, "reviewed_root_guard", "run_root", "fail", run_root, "refusing to audit/mutate the committed reviewed root")
        return 1, rows

    if run_root.exists() and run_root.is_dir():
        add(rows, "run_root_exists", "run_root", "pass", run_root, "run root exists")
    else:
        add(rows, "run_root_exists", "run_root", "fail", run_root, "run root missing")
        return 1, rows

    required_files = [
        ("run_manifest", run_root / "logs" / "run_manifest.yaml"),
        ("orchestration_plan", run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"),
        ("design_sample_manifest", run_root / "design" / "analysis_sample_manifest.tsv"),
        ("design_contrast_registry", run_root / "design" / "analysis_contrast_registry.tsv"),
        ("design_membership", run_root / "design" / "analysis_contrast_membership.tsv"),
        ("design_audit", run_root / "design" / "analysis_design_audit.md"),
        ("comparison_registry", run_root / "comparison_registry.tsv"),
    ]
    for check, path in required_files:
        add(rows, check, "required_file", "pass" if path.exists() and path.stat().st_size > 0 else "fail", path, "present" if path.exists() else "missing")

    audit_execution_decision_manifest(rows, run_root)

    plan_path = run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    plan_rows = planned_stages(plan_path)
    if plan_rows:
        observed_stages = {row.get("stage", "") for row in plan_rows}
        expected = {
            "design_build",
            "design_plan",
            "stage06_de",
            "stage07_meta",
            "signature",
            "immune_score",
            "immune_effects",
            "validate",
            "interpret_enrich",
            "interpret_network",
            "interpret_hub_meta",
            "interpret_immunophenotype",
            "interpret_epi_infer",
            "report",
            "postrun_audit",
        }
        payload_backed_resume = {
            stage: payload
            for stage in sorted(expected - observed_stages)
            if (payload := resumed_global_stage_payload(stage, run_root, args.out))
        }
        missing = sorted((expected - observed_stages) - set(payload_backed_resume))
        if not ({"tcga", "tcga_skip"} & observed_stages):
            missing.append("tcga_or_tcga_skip")
        detail = f"missing={','.join(missing) if missing else 'none'}"
        if payload_backed_resume:
            resumed = ",".join(f"{stage}:{path}" for stage, path in payload_backed_resume.items())
            detail += f"; resumed_payload={resumed}"
        add(
            rows,
            "planned_stage_coverage",
            "orchestration",
            "pass" if not missing else "fail",
            plan_path,
            detail,
        )
        for row in plan_rows:
            stage = row.get("stage", "")
            out_raw = row.get("output_dir", "")
            if not stage or not out_raw:
                continue
            if stage in {"design_plan", "postrun_audit"}:
                continue
            out_path = resolve_planned_path(out_raw, cwd, run_root)
            status = "pass" if has_payload(out_path) else "fail"
            add(rows, "planned_stage_output", stage, status, out_path, "payload present" if status == "pass" else "missing or empty")
    else:
        add(rows, "planned_stage_coverage", "orchestration", "fail", plan_path, "plan missing or empty")

    analysis_ids = args.analysis_id or derive_analysis_ids(plan_rows, run_root)
    if analysis_ids:
        add(rows, "analysis_ids", "run_root", "pass", run_root, ",".join(analysis_ids))
    else:
        add(rows, "analysis_ids", "run_root", "fail", run_root, "no analysis IDs found")

    audit_comparison_registry_merge(rows, run_root, plan_rows, analysis_ids)
    audit_run_manifest_merge(rows, run_root, plan_rows, analysis_ids)
    audit_bibalex_multijob_manifest(rows, run_root, plan_rows, analysis_ids)
    audit_bibalex_singlejob_manifest(rows, run_root)
    audit_nmrbox_condor_manifest(rows, run_root)

    for analysis_id in analysis_ids:
        expected_files = [
            ("stage07_meta_effects", run_root / "meta" / analysis_id / "meta_effects.tsv"),
            ("stage08_signature", run_root / "signature" / analysis_id / "responder_signature_tiered.tsv"),
        ]
        for check, path in expected_files:
            add(rows, check, analysis_id, "pass" if path.exists() and path.stat().st_size > 0 else "fail", path, "present" if path.exists() else "missing")
        validation_candidates = [
            run_root / "validation" / analysis_id / "validation_readiness_status.tsv",
            run_root / "validation" / analysis_id / "validation_summary.md",
            run_root / "validation" / analysis_id / "external_validation_summary.tsv",
        ]
        validation_payload = first_payload(validation_candidates)
        add(
            rows,
            "validation_outputs",
            analysis_id,
            "pass" if validation_payload else "fail",
            validation_payload or validation_candidates[0],
            "present" if validation_payload else "missing validation_readiness_status.tsv/validation_summary.md",
        )
        audit_tcga_outcome(rows, run_root, analysis_id)

    shared_dirs = [
        ("immune_state", run_root / "immune_state"),
        ("interpretation", run_root / "interpretation"),
        ("reports", run_root / "reports"),
    ]
    for check, path in shared_dirs:
        add(rows, check, "shared", "pass" if has_payload(path) else "fail", path, "payload present" if has_payload(path) else "missing or empty")

    audit_immune_effects_contract(rows, run_root, plan_rows)
    audit_interpretation_contracts(rows, run_root, plan_rows)
    audit_interpretation_claims(rows, run_root)
    exit_code = 0 if all(row["status"] in {"pass", "warn"} for row in rows) else 1
    return exit_code, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--analysis-id", action="append", default=[])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--summary-out", type=Path, default=None)
    parser.add_argument("--allow-reviewed-root", action="store_true")
    args = parser.parse_args(argv)

    exit_code, rows = audit_run(args)
    out_path = args.out or (Path(args.run_root) / "orchestration" / "analysis_id_pipeline_postrun_audit.tsv")
    summary_path = args.summary_out or out_path.with_suffix(".md")
    write_tsv(out_path, rows)
    write_markdown(summary_path, Path(args.run_root).resolve(), rows, exit_code)
    print(f"wrote {out_path}")
    print(f"wrote {summary_path}")
    print("status\t" + ("pass" if exit_code == 0 else "fail"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
