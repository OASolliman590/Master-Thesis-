#!/usr/bin/env python3
"""Build a local Phase 3 readiness dashboard without running the pipeline.

This checker is intentionally conservative. It inspects the Phase 1
interpretation layer, Phase 2 launch/audit wrappers, and the current reviewed
root outputs, then writes a TSV and Markdown report. It does not SSH, submit
jobs, rsync files, or execute the full analysis-id pipeline.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REVIEWED_ROOT_DEFAULT = Path("results/analysis_id_runs_t7_20260607_stage07_scale_provenance")
ALLOWED_CLAIMS = {"discovery", "mechanism_hypothesis"}
REQUIRED_SPEC027_FILES = ["spec.md", "plan.md", "research.md", "tasks.md", "quickstart.md", "benchmarks.md"]
REQUIRED_INTERPRETATION_MODULES = [
    "__init__.py",
    "contracts.py",
    "enrich.py",
    "network.py",
    "hub_meta.py",
    "immunophenotype.py",
    "epi_infer.py",
]
REQUIRED_HOPE_NON_RNA = {"tmb", "pdl1_ihc_tps_cps", "ecog_performance_status", "irecist_pseudoprogression"}
REQUIRED_HOPE_RNA = {
    "hope_checkpoint_expression",
    "hope_msi_dmmr_proxy",
    "hope_tcell_inflamed_gep",
    "hope_cytolytic_activity",
    "hope_ifng_signature",
    "hope_composite_rna",
}
REQUIRED_QUICKSTART_ANALYSIS_IDS = {
    "PRE_RESPONSE",
    "PAN_ICB_RESPONSE__PRE_TREATMENT",
    "ICI_COMBINATION_RESPONSE__PRE_TREATMENT",
}
REQUIRED_PHASE2_SCRIPTS = [
    "scripts/run_analysis_id_pipeline.sh",
    "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
    "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh",
    "scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh",
    "scripts/audit_analysis_id_pipeline_run.py",
]
REQUIRED_PHASE2_SHELL_SCRIPTS = [
    "scripts/run_analysis_id_pipeline.sh",
    "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
    "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh",
    "scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh",
]
IGNORED_TRACK_B_GSE = {"GSE160638", "GSE284400", "GSE289743"}
IGNORED_TRACK_B_ALIASES = {
    "GSE160638",
    "GSE284400",
    "GSE289743",
    "PRJNA1198945",
    "PRJNA1224435",
    "PRJNA673835",
    "SRP290810",
}


@dataclass
class Check:
    section: str
    check: str
    status: str
    path: str
    detail: str


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def nonempty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def has_payload(path: Path) -> bool:
    if path.is_file():
        return path.stat().st_size > 0
    if path.is_dir():
        return any(child.is_file() and child.stat().st_size > 0 for child in path.rglob("*"))
    return False


def add(rows: list[Check], section: str, check: str, status: str, path: Path | str, detail: str) -> None:
    rows.append(Check(section, check, status, str(path), detail))


def check_file(rows: list[Check], section: str, check: str, path: Path, *, executable: bool = False) -> None:
    if not nonempty(path):
        add(rows, section, check, "fail", path, "missing or empty")
        return
    if executable and not (path.stat().st_mode & 0o111):
        add(rows, section, check, "fail", path, "present but not executable")
        return
    add(rows, section, check, "pass", path, "present")


def check_text_contains(rows: list[Check], section: str, check: str, path: Path, needles: list[str]) -> None:
    if not nonempty(path):
        add(rows, section, check, "fail", path, "missing or empty")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [needle for needle in needles if needle not in text]
    add(
        rows,
        section,
        check,
        "pass" if not missing else "fail",
        path,
        "contains required markers" if not missing else "missing markers: " + ", ".join(missing),
    )


def check_shell_syntax(rows: list[Check], repo_root: Path, rel_paths: list[str]) -> None:
    for rel in rel_paths:
        path = repo_root / rel
        check_name = f"shell_syntax:{rel}"
        if not nonempty(path):
            add(rows, "phase2_orchestration", check_name, "fail", path, "missing or empty")
            continue
        try:
            result = subprocess.run(
                ["bash", "-n", str(path)],
                cwd=repo_root,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            add(rows, "phase2_orchestration", check_name, "fail", path, f"bash -n could not complete: {exc}")
            continue
        detail = "bash -n passed" if result.returncode == 0 else (result.stderr.strip() or result.stdout.strip() or "bash -n failed")
        add(rows, "phase2_orchestration", check_name, "pass" if result.returncode == 0 else "fail", path, detail)


def check_claim_classes(rows: list[Check], interp_root: Path) -> None:
    if not interp_root.exists():
        add(rows, "phase1_interpretation_outputs", "claim_class_scan", "fail", interp_root, "interpretation directory missing")
        return
    checked = 0
    bad: list[str] = []
    for path in sorted(interp_root.rglob("*.tsv")):
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
        disallowed = sorted(claims - ALLOWED_CLAIMS)
        if disallowed:
            rendered = ",".join(value if value else "<blank>" for value in disallowed)
            bad.append(f"{path}: {rendered}")
    if bad:
        add(rows, "phase1_interpretation_outputs", "claim_class_scan", "fail", interp_root, "; ".join(bad[:10]))
    else:
        add(rows, "phase1_interpretation_outputs", "claim_class_scan", "pass", interp_root, f"checked {checked} claim-class table(s)")


def check_registry(rows: list[Check], registry: Path) -> None:
    if not nonempty(registry):
        add(rows, "phase1_contracts", "hope_registry", "fail", registry, "missing or empty")
        return
    table = read_tsv(registry)
    ids = {row.get("criteria_id", "") for row in table}
    missing_rna = sorted(REQUIRED_HOPE_RNA - ids)
    missing_non_rna = sorted(REQUIRED_HOPE_NON_RNA - ids)
    bad_derivable = [
        row.get("criteria_id", "")
        for row in table
        if row.get("rna_derivable") not in {"yes", "no"}
    ]
    if missing_rna or missing_non_rna or bad_derivable:
        detail = []
        if missing_rna:
            detail.append("missing RNA rows=" + ",".join(missing_rna))
        if missing_non_rna:
            detail.append("missing non-RNA rows=" + ",".join(missing_non_rna))
        if bad_derivable:
            detail.append("bad rna_derivable values=" + ",".join(bad_derivable))
        add(rows, "phase1_contracts", "hope_registry", "fail", registry, "; ".join(detail))
    else:
        add(rows, "phase1_contracts", "hope_registry", "pass", registry, "HOPE RNA rows plus non-RNA handoff rows present")


def check_enrichment(rows: list[Check], interp_root: Path) -> None:
    enrichment_root = interp_root / "enrichment"
    if not enrichment_root.exists():
        add(rows, "phase1_interpretation_outputs", "enrichment_outputs", "fail", enrichment_root, "missing")
        return
    analysis_dirs = sorted(path for path in enrichment_root.iterdir() if path.is_dir())
    if not analysis_dirs:
        add(rows, "phase1_interpretation_outputs", "enrichment_outputs", "fail", enrichment_root, "no analysis_id folders")
        return
    failures: list[str] = []
    present_ids = {path.name for path in analysis_dirs}
    missing_quickstart_ids = sorted(REQUIRED_QUICKSTART_ANALYSIS_IDS - present_ids)
    if missing_quickstart_ids:
        failures.append("missing quickstart analysis_id folders=" + ",".join(missing_quickstart_ids))
    for analysis_dir in analysis_dirs:
        for name in ["gsea.tsv", "ora.tsv", "dotplot_data.tsv"]:
            path = analysis_dir / name
            if not nonempty(path):
                failures.append(f"{analysis_dir.name}/{name}")
        gsea = analysis_dir / "gsea.tsv"
        if nonempty(gsea):
            table = read_tsv(gsea)
            stats = {row.get("statistic", "").strip() for row in table if row.get("statistic", "").strip()}
            if stats != {"meta_effect_random"}:
                failures.append(f"{analysis_dir.name}/gsea.tsv statistic!=meta_effect_random")
        repro = analysis_dir / "reproducibility"
        for name in ["commands.sh", "environment.yml", "checksums.sha256"]:
            if not nonempty(repro / name):
                failures.append(f"{analysis_dir.name}/reproducibility/{name}")
    add(
        rows,
        "phase1_interpretation_outputs",
        "enrichment_outputs",
        "pass" if not failures else "fail",
        enrichment_root,
        f"{len(analysis_dirs)} analysis_id folder(s); quickstart IDs present"
        if not failures
        else "missing: " + "; ".join(failures[:10]),
    )


def check_reproducibility(rows: list[Check], interp_root: Path) -> None:
    targets = [
        interp_root / "network" / "PRE_RESPONSE" / "reproducibility",
        interp_root / "hub_meta" / "reproducibility",
        interp_root / "immunophenotype" / "reproducibility",
        interp_root / "epigenetic" / "reproducibility",
    ]
    missing: list[str] = []
    for target in targets:
        for name in ["commands.sh", "environment.yml", "checksums.sha256"]:
            if not nonempty(target / name):
                missing.append(str(target / name))
    add(
        rows,
        "phase1_interpretation_outputs",
        "reproducibility_bundles",
        "pass" if not missing else "fail",
        interp_root,
        "module reproducibility bundles present" if not missing else "missing: " + "; ".join(missing[:10]),
    )


def check_network(rows: list[Check], interp_root: Path) -> None:
    hub_path = interp_root / "network" / "PRE_RESPONSE" / "hub_genes.tsv"
    if not nonempty(hub_path):
        add(rows, "phase1_interpretation_outputs", "network_hub_guard", "fail", hub_path, "missing or empty")
        return
    table = read_tsv(hub_path)
    header = set(table[0].keys()) if table else set()
    if "permutation_fdr" not in header or "status" not in header:
        add(rows, "phase1_interpretation_outputs", "network_hub_guard", "fail", hub_path, "missing permutation_fdr/status columns")
        return
    statuses = {row.get("status", "") for row in table}
    if "insufficient_signal" in statuses:
        add(rows, "phase1_interpretation_outputs", "network_hub_guard", "pass", hub_path, "thin signal correctly reports insufficient_signal")
    else:
        add(rows, "phase1_interpretation_outputs", "network_hub_guard", "pass", hub_path, "hub table present with permutation_fdr")


def check_hub_meta(rows: list[Check], interp_root: Path) -> None:
    path = interp_root / "hub_meta" / "cross_cancer_hub_meta.tsv"
    if not nonempty(path):
        add(rows, "phase1_interpretation_outputs", "hub_meta", "fail", path, "missing or empty")
        return
    table = read_tsv(path)
    statuses = {row.get("status", "") for row in table}
    moderator = {row.get("moderator_status", "") for row in table}
    if "insufficient_signal" in statuses or "cancer_as_low_dimension_moderator_only" in moderator:
        add(rows, "phase1_interpretation_outputs", "hub_meta", "pass", path, "cancer retained as moderator and thin signal propagated")
    else:
        add(rows, "phase1_interpretation_outputs", "hub_meta", "pass", path, "hub meta table present")


def check_immunophenotype(rows: list[Check], interp_root: Path, registry: Path) -> None:
    root = interp_root / "immunophenotype"
    required = ["sample_phenotype.tsv", "phenotype_response_assoc.tsv", "hope_skipped_criteria.tsv", "immunophenotype_input_audit.tsv"]
    missing = [name for name in required if not nonempty(root / name)]
    skipped_rows: dict[str, dict[str, str]] = {}
    if nonempty(root / "hope_skipped_criteria.tsv"):
        skipped_rows = {row.get("criteria_id", ""): row for row in read_tsv(root / "hope_skipped_criteria.tsv")}
    missing_skips = sorted(REQUIRED_HOPE_NON_RNA - set(skipped_rows))
    bad_handoffs: list[str] = []
    for criteria_id in ["tmb", "pdl1_ihc_tps_cps", "ecog_performance_status"]:
        row = skipped_rows.get(criteria_id, {})
        if row and row.get("route_to_spec") != "spec020":
            bad_handoffs.append(f"{criteria_id}:route_to_spec={row.get('route_to_spec', '<blank>')}")
        if row and not row.get("skip_reason", "").strip():
            bad_handoffs.append(f"{criteria_id}:missing skip_reason")
    irecist = skipped_rows.get("irecist_pseudoprogression", {})
    if irecist and irecist.get("route_to_spec") != "spec010":
        bad_handoffs.append(f"irecist_pseudoprogression:route_to_spec={irecist.get('route_to_spec', '<blank>')}")

    scored_ids: set[str] = set()
    if nonempty(root / "sample_phenotype.tsv"):
        scored_ids = {row.get("criteria_id", "") for row in read_tsv(root / "sample_phenotype.tsv")}
    audited_ids: set[str] = set()
    if nonempty(root / "immunophenotype_input_audit.tsv"):
        audited_ids = {
            row.get("input_name", "")
            for row in read_tsv(root / "immunophenotype_input_audit.tsv")
            if row.get("status", "").strip() not in {"", "ok"}
        }
    registry_rna_ids = set(REQUIRED_HOPE_RNA)
    if nonempty(registry):
        registry_rna_ids = {
            row.get("criteria_id", "")
            for row in read_tsv(registry)
            if row.get("rna_derivable") == "yes" and row.get("criteria_id", "")
        }
    unresolved_rna = sorted(registry_rna_ids - scored_ids - audited_ids)

    if missing or missing_skips or bad_handoffs or unresolved_rna:
        detail = []
        if missing:
            detail.append("missing files=" + ",".join(missing))
        if missing_skips:
            detail.append("missing skipped non-RNA criteria=" + ",".join(missing_skips))
        if bad_handoffs:
            detail.append("bad handoff rows=" + ",".join(bad_handoffs))
        if unresolved_rna:
            detail.append("RNA criteria neither scored nor audited=" + ",".join(unresolved_rna))
        add(rows, "phase1_interpretation_outputs", "immunophenotype_hope", "fail", root, "; ".join(detail))
    else:
        add(
            rows,
            "phase1_interpretation_outputs",
            "immunophenotype_hope",
            "pass",
            root,
            "HOPE RNA criteria are scored or audited; non-RNA rows skipped with routes",
        )


def check_epigenetic(rows: list[Check], interp_root: Path) -> None:
    root = interp_root / "epigenetic"
    required = ["inferred_scores.tsv", "epi_response_assoc.tsv", "epi_input_audit.tsv"]
    missing = [name for name in required if not nonempty(root / name)]
    add(
        rows,
        "phase1_interpretation_outputs",
        "epigenetic_proxy",
        "pass" if not missing else "fail",
        root,
        "RNA-inferred epigenetic proxy outputs present" if not missing else "missing: " + ",".join(missing),
    )


def check_interpret_quickstart_manifest(rows: list[Check], interp_root: Path) -> None:
    check_text_contains(
        rows,
        "phase1_interpretation_outputs",
        "interpret_quickstart_manifest",
        interp_root / "interpret_run_manifest.yaml",
        [
            "interpret enrich",
            "PRE_RESPONSE",
            "PAN_ICB_RESPONSE__PRE_TREATMENT",
            "ICI_COMBINATION_RESPONSE__PRE_TREATMENT",
            "interpret network",
            "interpret hub-meta",
            "interpret immunophenotype",
            "interpret epi-infer",
        ],
    )


def check_phase2_scripts(rows: list[Check], repo_root: Path) -> None:
    for rel in REQUIRED_PHASE2_SCRIPTS:
        check_file(rows, "phase2_orchestration", rel, repo_root / rel, executable=True)
    check_shell_syntax(rows, repo_root, REQUIRED_PHASE2_SHELL_SCRIPTS)
    check_text_contains(
        rows,
        "phase2_orchestration",
        "local_execute_gate",
        repo_root / "scripts/run_analysis_id_pipeline.sh",
        ["ALLOW_ANALYSIS_ID_PIPELINE_RUN", "--execute", "--preflight"],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "execution_decision_manifest",
        repo_root / "scripts/run_analysis_id_pipeline.sh",
        [
            "phase3_execution_decision_manifest.tsv",
            "analysis_scope_mode",
            "tcga_behavior",
            "claim_boundary",
            "track_boundary",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "analysis_id_orchestration_chain",
        repo_root / "scripts/run_analysis_id_pipeline.sh",
        [
            "design build",
            "design plan-runs",
            "de run",
            "meta run",
            "signature derive",
            "immune score",
            "immune effects",
            "validate run",
            "tcga project",
            "tcga_skip",
            "interpret enrich",
            "interpret network",
            "interpret hub-meta",
            "interpret immunophenotype",
            "interpret epi-infer",
            "report build",
            "postrun_audit",
            "audit_analysis_id_pipeline_run.py",
            "--run-manifest",
            "logs/run_manifest.yaml",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_submit_gate",
        repo_root / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        ["ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE", "--submit", "--preflight"],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_submission_preview_manifest",
        repo_root / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        [
            "bibalex_analysis_id_submission_preview_manifest.tsv",
            "network_action_preflight",
            "submission_preview_manifest",
            "out_root_remote",
            "downloads_root_remote",
            "portable_r_conda_prefix",
            "execution_gate",
            "inner_execution_gate",
            "claim_boundary",
            "track_boundary",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_single_job_portable_r_path",
        repo_root / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        [
            "export PORTABLE_R_CONDA_PREFIX=",
            'if [[ -n "\\${PORTABLE_R_CONDA_PREFIX:-}" && -x "\\${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then',
            'export PATH="\\${PORTABLE_R_CONDA_PREFIX}/bin:\\${PATH}"',
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_single_job_env_parity",
        repo_root / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        [
            "export SAMPLE_MANIFEST=",
            "export EXPRESSION_MANIFEST=",
            "export GENE_ID_MAPPING=",
            "export GENE_SET_REGISTRY=",
            "export CRITERIA_REGISTRY=",
            "export COUNT_METHOD=",
            'export RUN_MANIFEST="\\${OUT_ROOT}/logs/run_manifest.yaml"',
            "export ALLOW_EMPTY_SIGNATURE=",
            "export ALLOW_WEAK_GENE_MAPPING=",
            "export ALLOW_WELCH_FALLBACK=",
            "sample_manifest",
            "expression_manifest",
            "gene_id_mapping",
            "gene_set_registry",
            "criteria_registry",
            "count_method",
            "allow_weak_gene_mapping",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_single_job_final_audit_delegate",
        repo_root / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        [
            "bibalex_singlejob_submission_manifest.tsv",
            "export ALLOW_ANALYSIS_ID_PIPELINE_RUN=1",
            "bash scripts/run_analysis_id_pipeline.sh --execute",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_multijob_dependency_preview",
        repo_root / "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh",
        [
            "ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB",
            "--submit-multijob",
            "--preflight",
            "bibalex_analysis_id_multijob_submission_preview_manifest.tsv",
            "multi_job_strategy",
            "dependency_fanout",
            "sbatch --parsable",
            "--dependency=afterok",
            "analysis_execution_plan.tsv",
            "analysis_id_pipeline_plan.tsv",
            "comparison_registry_by_analysis",
            "comparison_registry_merge",
            "comparison_registry_strategy",
            "job_manifests",
            "run_manifest_merge",
            "run_manifest_strategy",
            "logs/run_manifest.yaml",
            "--run-manifest",
            "remote_analysis_script",
            "remote_immune_script",
            "remote_finalize_script",
            "postrun_audit",
            "audit_analysis_id_pipeline_run.py",
            "claim_boundary",
            "track_boundary",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "bibalex_pull_gate",
        repo_root / "scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh",
        ["ALLOW_BIBALEX_PULL_ANALYSIS_ID_RESULTS", "--pull", "--preflight"],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "postrun_audit_contracts",
        repo_root / "scripts/audit_analysis_id_pipeline_run.py",
        [
            "def resolve_planned_path",
            "run_root.name",
            "resolve_planned_path(out_raw, cwd, run_root)",
            "planned_stage_output",
            "interpretation_claim_classes",
            "blocked/skipped TCGA rows must include a reason",
            "comparison_registry_merge_inputs",
            "run_manifest_merge_inputs",
            "bibalex_multijob_submission_manifest",
            "bibalex_singlejob_submission_manifest",
            "nmrbox_condor_submission_manifest",
            "nmrbox_condor_single_job",
            "r_libs_user must record the NMRbox R package library path",
            "portable_r_conda_prefix must record the Spec 094 runtime prefix",
            "immune_effects_contract",
            "non-empty ssGSEA scores require cohort-level feature_source=gsva_ssgsea",
            "interpretation_enrichment_contract",
            "interpretation_network_contract",
            "interpretation_hub_meta_contract",
            "interpretation_immunophenotype_contract",
            "interpretation_epigenetic_contract",
            "statistic=meta_effect_random",
            "HOPE RNA criteria scored or audited; non-RNA criteria skipped with routes",
        ],
    )


def check_phase2_spec_links(rows: list[Check], repo_root: Path) -> None:
    comp_root = repo_root.parent
    spec093 = comp_root / "specs/093-bibalex-hpc-execution-backend"
    spec094 = comp_root / "specs/094-portable-r-runtime-gsva-deseq2"
    check_text_contains(
        rows,
        "phase2_orchestration",
        "spec093_analysis_id_backend",
        spec093 / "quickstart.md",
        [
            "Analysis-ID Phase 3 Launcher",
            "run_analysis_id_pipeline_multijob.sh --preflight",
            "run_analysis_id_pipeline.sh --preflight",
            "ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB=1",
            "run_analysis_id_pipeline_multijob.sh --submit-multijob",
            "no SSH, no",
            "no full pipeline execution",
            "never target the reviewed root",
            "TCGA output as prognostic context only",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "spec093_tasks_analysis_id_backend",
        spec093 / "tasks.md",
        ["[x] T023", "[x] T024", "Spec 026 analysis-id full-run launcher", "multi-job Slurm preview"],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "spec094_portable_r_launcher_integration",
        spec094 / "quickstart.md",
        [
            "Use With Analysis-ID Phase 3 Launcher",
            "PORTABLE_R_CONDA_PREFIX",
            "BIBALEX_PORTABLE_R_CONDA_PREFIX",
            "configs/bibalex_hpc_profile.env",
            "run_analysis_id_pipeline_multijob.sh --preflight",
            "portable_r_conda_prefix",
            "before any",
            "full-run approval or Slurm submission",
        ],
    )
    check_text_contains(
        rows,
        "phase2_orchestration",
        "spec094_tasks_runtime_gate",
        spec094 / "tasks.md",
        ["[x] T015", "[x] T017", "no full pipeline rerun", "committed `results/` mutation"],
    )


def check_docs(rows: list[Check], repo_root: Path) -> None:
    comp_root = repo_root.parent
    check_text_contains(
        rows,
        "context_and_runbooks",
        "handover_finalized_sequence",
        comp_root / "docs/ici_investigation_handover_2026-06-30.md",
        ["FINALIZED SEQUENCE", "GSE289743", "GSE284400", "GSE160638", "Do NOT run the full pipeline"],
    )
    for rel in [
        "docs/runbooks/phase1_phase2_completion_audit_2026-07-03.md",
        "docs/runbooks/phase1_phase2_phase3_status_audit_2026-07-04.md",
        "docs/runbooks/phase3_full_run_approval_packet_2026-07-03.md",
        "docs/runbooks/phase3_preapproval_packet_2026-07-04.md",
        "docs/runbooks/phase3_readiness_contract_map_2026-07-04.md",
        "docs/runbooks/analysis_id_pipeline_orchestration.md",
        "docs/runbooks/stage_10_interpretation.md",
    ]:
        check_file(rows, "context_and_runbooks", rel, repo_root / rel)
    check_text_contains(
        rows,
        "context_and_runbooks",
        "phase3_readiness_contract_map",
        repo_root / "docs/runbooks/phase3_readiness_contract_map_2026-07-04.md",
        [
            "ready_pending_approval",
            "No full pipeline run, SSH, Slurm submission, or rsync",
            "Phase 1 -> Phase 2 -> Phase 3",
            "Track A signature-building data and Track B external-testing candidates remain separate",
            "TCGA remains prognostic context only",
            "post-run auditor",
            "explicit Phase 3 approval",
        ],
    )
    check_text_contains(
        rows,
        "context_and_runbooks",
        "phase3_approval_wording",
        repo_root / "docs/runbooks/phase3_full_run_approval_packet_2026-07-03.md",
        ["I approve the Phase 3 full run", "Without one of those explicit approvals, do not execute Phase 3"],
    )
    check_text_contains(
        rows,
        "context_and_runbooks",
        "phase3_preapproval_boundary",
        repo_root / "docs/runbooks/phase3_preapproval_packet_2026-07-04.md",
        [
            "No full pipeline run, SSH, Slurm submission, or rsync",
            "I approve the Phase 3 full run on local/T7",
            "I approve the Phase 3 full run on BibaLex with RUN_TAG",
            "I approve the Phase 3 full run on BibaLex multi-job",
            "current dry-run plan with final audit",
            "BibaLex durable single-job preview with final audit",
            "BibaLex durable single-job manifest with final audit",
            "BibaLex durable single-job script with final audit",
            "runtime_audits/bibalex_analysis_id_singlejob_current_preflight_20260704_postrun_audit",
            "BibaLex durable multi-job preview with final audit",
            "postrun_audit",
            "analysis_id_pipeline_postrun_audit.tsv",
            "`ready_pending_approval`",
        ],
    )


def check_track_b_boundary(rows: list[Check], repo_root: Path) -> None:
    comp_root = repo_root.parent
    discovery = comp_root / "specs/080-external-ici-treated-validation/discovery"
    shortlist = discovery / "ici_external_validation_shortlist.tsv"
    triaged = discovery / "ici_external_candidates_triaged.tsv"
    decision = discovery / "ignored_studies_decision_20260703.md"

    check_text_contains(
        rows,
        "track_b_boundary",
        "ignored_studies_decision",
        decision,
        [
            "GSE289743",
            "GSE284400",
            "GSE160638",
            "provenance only",
            "unless the user explicitly reopens",
            "PRJNA1198945",
            "PRJNA1224435",
            "PRJNA673835",
            "SRP290810",
        ],
    )

    if not nonempty(shortlist):
        add(rows, "track_b_boundary", "ignored_shortlist_roles", "fail", shortlist, "missing or empty")
    else:
        table = read_tsv(shortlist)
        by_accession = {row.get("accession", ""): row for row in table}
        missing = sorted(IGNORED_TRACK_B_GSE - set(by_accession))
        problems: list[str] = []
        for accession in sorted(IGNORED_TRACK_B_GSE & set(by_accession)):
            row = by_accession[accession]
            role = row.get("use_role", "")
            status = row.get("status", "")
            notes = row.get("notes", "").lower()
            if role != "ignored_by_user":
                problems.append(f"{accession} use_role={role}")
            if not status.startswith("user_ignored"):
                problems.append(f"{accession} status={status}")
            if "user decision" not in notes or "provenance" not in notes:
                problems.append(f"{accession} notes missing user decision/provenance")
        if missing:
            problems.append("missing accessions=" + ",".join(missing))
        add(
            rows,
            "track_b_boundary",
            "ignored_shortlist_roles",
            "pass" if not problems else "fail",
            shortlist,
            f"{len(IGNORED_TRACK_B_GSE)} ignored shortlist studies remain inactive"
            if not problems
            else "; ".join(problems),
        )

    if not nonempty(triaged):
        add(rows, "track_b_boundary", "ignored_triage_aliases", "fail", triaged, "missing or empty")
    else:
        table = read_tsv(triaged)
        by_accession = {row.get("accession", ""): row for row in table}
        missing = sorted(IGNORED_TRACK_B_ALIASES - set(by_accession))
        reactivated = sorted(
            accession
            for accession in IGNORED_TRACK_B_ALIASES & set(by_accession)
            if by_accession[accession].get("triage_state", "") != "ignored_by_user"
        )
        problems = []
        if missing:
            problems.append("missing ignored aliases=" + ",".join(missing))
        if reactivated:
            rendered = ",".join(
                f"{accession}:{by_accession[accession].get('triage_state', '')}"
                for accession in reactivated
            )
            problems.append("reactivated aliases=" + rendered)
        add(
            rows,
            "track_b_boundary",
            "ignored_triage_aliases",
            "pass" if not problems else "fail",
            triaged,
            f"{len(IGNORED_TRACK_B_ALIASES)} ignored GEO/SRA aliases remain ignored_by_user"
            if not problems
            else "; ".join(problems),
        )


def check_spec027(rows: list[Check], repo_root: Path) -> None:
    spec_root = repo_root / "specs/027-downstream-biological-interpretation"
    for name in REQUIRED_SPEC027_FILES:
        check_file(rows, "phase1_contracts", f"spec027_{name}", spec_root / name)
    check_text_contains(
        rows,
        "phase1_contracts",
        "spec027_quickstart_contract",
        spec_root / "quickstart.md",
        [
            'PYTHON="${PYTHON:-python3.13}"',
            "export PYTHONPYCACHEPREFIX=/private/tmp/epigenetic_thesis_pycache",
            '"${PYTHON}" -m src.pipeline.cli interpret enrich',
            '"${PYTHON}" -m src.pipeline.cli interpret network',
            '"${PYTHON}" -m src.pipeline.cli interpret hub-meta',
            '"${PYTHON}" -m src.pipeline.cli interpret immunophenotype',
            '"${PYTHON}" -m src.pipeline.cli interpret epi-infer',
            "routine readiness verification",
            "without rewriting the reviewed root",
            "phase3_readiness_dashboard.py --out-dir runtime_audits/phase3_readiness_20260704_smoke",
        ],
    )
    check_text_contains(
        rows,
        "phase1_contracts",
        "spec027_tasks_complete",
        spec_root / "tasks.md",
        ["[x] T001", "[x] T061", "[x] T064", "python3.13 -m pytest tests -k interpretation -q"],
    )
    check_text_contains(
        rows,
        "phase1_contracts",
        "spec027_benchmark_baseline",
        spec_root / "benchmarks.md",
        [
            "First reviewed-root output baseline",
            "3 analysis IDs",
            "3,412 sample-phenotype rows",
            "7,677 inferred-score rows",
            "runtime and memory baselines are still pending",
        ],
    )
    module_root = repo_root / "src/pipeline/modules/10_interpretation"
    for name in REQUIRED_INTERPRETATION_MODULES:
        check_file(rows, "phase1_contracts", f"module_{name}", module_root / name)
    check_text_contains(
        rows,
        "phase1_contracts",
        "interpretation_write_scope_guard",
        module_root / "contracts.py",
        ["def interpretation_root", "target.relative_to(expected)", "Interpretation outputs must be written under", "def file_sha256"],
    )
    check_text_contains(
        rows,
        "phase1_contracts",
        "sc006_checksum_test",
        repo_root / "tests/unit/test_spec027_interpretation.py",
        [
            "test_interpretation_path_guard_rejects_non_interpretation_output",
            "test_interpret_network_gates_thin_signal_and_preserves_signature_checksum",
            "file_sha256",
            "before == after",
        ],
    )
    check_text_contains(rows, "phase1_contracts", "cli_interpret_group", repo_root / "src/pipeline/cli.py", ["interpret", "interpret enrich"])
    check_registry(rows, repo_root / "configs/immunophenotype_criteria_registry.tsv")


def run_dashboard(repo_root: Path, reviewed_root: Path, out_dir: Path) -> tuple[int, list[Check], Path, Path]:
    rows: list[Check] = []
    repo_root = repo_root.resolve()
    reviewed_root = reviewed_root if reviewed_root.is_absolute() else repo_root / reviewed_root
    reviewed_root = reviewed_root.resolve()

    check_docs(rows, repo_root)
    check_track_b_boundary(rows, repo_root)
    check_spec027(rows, repo_root)

    add(
        rows,
        "phase1_interpretation_outputs",
        "reviewed_root_exists",
        "pass" if reviewed_root.exists() and reviewed_root.is_dir() else "fail",
        reviewed_root,
        "reviewed root present" if reviewed_root.exists() else "reviewed root missing",
    )
    interp_root = reviewed_root / "interpretation"
    add(
        rows,
        "phase1_interpretation_outputs",
        "interpretation_payload",
        "pass" if has_payload(interp_root) else "fail",
        interp_root,
        "payload present" if has_payload(interp_root) else "missing or empty",
    )
    if interp_root.exists():
        check_enrichment(rows, interp_root)
        check_network(rows, interp_root)
        check_hub_meta(rows, interp_root)
        check_immunophenotype(rows, interp_root, repo_root / "configs/immunophenotype_criteria_registry.tsv")
        check_epigenetic(rows, interp_root)
        check_reproducibility(rows, interp_root)
        check_claim_classes(rows, interp_root)
        check_interpret_quickstart_manifest(rows, interp_root)

    check_phase2_scripts(rows, repo_root)
    check_phase2_spec_links(rows, repo_root)
    add(
        rows,
        "phase3_gate",
        "explicit_user_approval",
        "warn",
        "not_applicable",
        "Phase 3 full run is intentionally pending explicit user approval; this dashboard did not execute it",
    )

    exit_code = 0 if all(row.status != "fail" for row in rows) else 1
    out_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = out_dir / "phase3_readiness_dashboard.tsv"
    md_path = out_dir / "phase3_readiness_dashboard.md"
    write_tsv(tsv_path, rows)
    write_markdown(md_path, repo_root, reviewed_root, rows, exit_code)
    return exit_code, rows, tsv_path, md_path


def write_tsv(path: Path, rows: list[Check]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["section", "check", "status", "path", "detail"], delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_markdown(path: Path, repo_root: Path, reviewed_root: Path, rows: list[Check], exit_code: int) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    failures = [row for row in rows if row.status == "fail"]
    warnings = [row for row in rows if row.status == "warn"]
    phase1_fail = any(row.status == "fail" and row.section.startswith("phase1") for row in rows)
    phase2_fail = any(row.status == "fail" and row.section.startswith("phase2") for row in rows)
    lines = [
        "# Phase 3 Readiness Dashboard",
        "",
        f"- repo_root: `{repo_root}`",
        f"- reviewed_root: `{reviewed_root}`",
        f"- status: `{'ready_pending_approval' if exit_code == 0 else 'not_ready'}`",
        "- network_or_hpc_action: `none`",
        "- full_pipeline_run: `not_started`",
        "",
        "## Phase Status",
        "",
        "| phase | status | detail |",
        "|---|---|---|",
        f"| Phase 1 interpretation | {'pass' if not phase1_fail else 'fail'} | spec 027 contracts and reviewed-root outputs checked |",
        f"| Phase 2 orchestration | {'pass' if not phase2_fail else 'fail'} | local launcher, BibaLex single-job/multi-job wrappers, puller, and post-run audit checked |",
        "| Phase 3 full run | pending_approval | explicit approval is still required before local/HPC execution |",
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
        lines.extend(["| section | check | path | detail |", "|---|---|---|---|"])
        for row in failures:
            lines.append(f"| {row.section} | {row.check} | `{row.path}` | {row.detail} |")
    else:
        lines.append("No failing checks.")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(["| section | check | detail |", "|---|---|---|"])
        for row in warnings:
            lines.append(f"| {row.section} | {row.check} | {row.detail} |")
    else:
        lines.append("No warnings.")
    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
            "- Spec 027 interpretation outputs are discovery or mechanism-hypothesis only.",
            "- TCGA remains prognostic context only, not ICB responder validation.",
            "- LOCO remains internal robustness only.",
            "- Track A signature-building data remain separate from Track B external candidates.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--reviewed-root", type=Path, default=REVIEWED_ROOT_DEFAULT)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    out_dir = args.out_dir or Path.cwd() / "runtime_audits" / f"phase3_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    exit_code, _, tsv_path, md_path = run_dashboard(args.repo_root, args.reviewed_root, out_dir)
    print(f"wrote {tsv_path}")
    print(f"wrote {md_path}")
    print("status\t" + ("ready_pending_approval" if exit_code == 0 else "not_ready"))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
