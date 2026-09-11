from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o755)


def _write_repro(root: Path) -> None:
    _write(root / "commands.sh", "# commands\n")
    _write(root / "environment.yml", "name: fixture\n")
    _write(root / "checksums.sha256", "fixture  file\n")


def _fixture_repo(tmp_path: Path, claim_class: str = "mechanism_hypothesis") -> Path:
    comp_root = tmp_path / "Computation Arm"
    repo = comp_root / "06_analysis_pipeline_repo"

    _write(
        comp_root / "docs/ici_investigation_handover_2026-06-30.md",
        "FINALIZED SEQUENCE\nGSE289743\nGSE284400\nGSE160638\nDo NOT run the full pipeline\n",
    )
    discovery = comp_root / "specs/080-external-ici-treated-validation/discovery"
    _write(
        discovery / "ignored_studies_decision_20260703.md",
        "\n".join(
            [
                "# Ignored External-Validation Studies Decision",
                "GSE289743",
                "GSE284400",
                "GSE160638",
                "provenance only",
                "unless the user explicitly reopens",
                "PRJNA1198945",
                "PRJNA1224435",
                "PRJNA673835",
                "SRP290810",
                "",
            ]
        ),
    )
    spec093 = comp_root / "specs/093-bibalex-hpc-execution-backend"
    _write(
        spec093 / "quickstart.md",
        "\n".join(
            [
                "# Quickstart: BibaLex HPC Execution Backend",
                "## Analysis-ID Phase 3 Launcher",
                "run_analysis_id_pipeline_multijob.sh --preflight",
                "run_analysis_id_pipeline.sh --preflight",
                "ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB=1",
                "run_analysis_id_pipeline_multijob.sh --submit-multijob",
                "no SSH, no scp, no sbatch",
                "no full pipeline execution",
                "never target the reviewed root",
                "TCGA output as prognostic context only",
                "",
            ]
        ),
    )
    _write(
        spec093 / "tasks.md",
        "\n".join(
            [
                "[x] T023 Add gated Spec 026 analysis-id full-run launcher",
                "[x] T024 Add gated Spec 026 analysis-id multi-job Slurm preview",
                "",
            ]
        ),
    )
    spec094 = comp_root / "specs/094-portable-r-runtime-gsva-deseq2"
    _write(
        spec094 / "quickstart.md",
        "\n".join(
            [
                "# Quickstart: Portable R Runtime",
                "## Use With Analysis-ID Phase 3 Launcher",
                "PORTABLE_R_CONDA_PREFIX",
                "BIBALEX_PORTABLE_R_CONDA_PREFIX",
                "configs/bibalex_hpc_profile.env",
                "run_analysis_id_pipeline_multijob.sh --preflight",
                "portable_r_conda_prefix",
                "before any",
                "full-run approval or Slurm submission",
                "",
            ]
        ),
    )
    _write(
        spec094 / "tasks.md",
        "\n".join(
            [
                "[x] T015 Run BibaLex portable R smoke test successfully.",
                "[x] T017 Confirm no full pipeline rerun or committed `results/` mutation occurred.",
                "",
            ]
        ),
    )
    _write(
        discovery / "ici_external_validation_shortlist.tsv",
        "\n".join(
            [
                "rank\taccession\tcancer_type\tn_samples\tdrug_class\tassay_track\tlabel_source\tuse_role\tstatus\tnotes",
                "1\tGSE289743\tcscc\t83\tanti-PD-1\tbulk\tgeo\tignored_by_user\tuser_ignored_after_scoring\tUSER DECISION 2026-07-03 provenance only",
                "2\tGSE284400\tovarian\t78\tici_combo\tbulk\tgeo\tignored_by_user\tuser_ignored_no_further_curation\tUSER DECISION 2026-07-03 provenance only",
                "3\tGSE160638\tmelanoma\t73\tanti-PD-1\tbulk\tgeo\tignored_by_user\tuser_ignored_no_further_curation\tUSER DECISION 2026-07-03 provenance only",
                "",
            ]
        ),
    )
    _write(
        discovery / "ici_external_candidates_triaged.tsv",
        "\n".join(
            [
                "accession\tdataset_type\ttriage_state",
                "GSE160638\tGEO\tignored_by_user",
                "GSE284400\tGEO\tignored_by_user",
                "GSE289743\tGEO\tignored_by_user",
                "PRJNA1198945\tSRA_BioProject\tignored_by_user",
                "PRJNA1224435\tSRA_BioProject\tignored_by_user",
                "PRJNA673835\tSRA_BioProject\tignored_by_user",
                "SRP290810\tSRA_BioProject\tignored_by_user",
                "",
            ]
        ),
    )
    for rel in [
        "docs/runbooks/phase1_phase2_completion_audit_2026-07-03.md",
        "docs/runbooks/phase1_phase2_phase3_status_audit_2026-07-04.md",
        "docs/runbooks/analysis_id_pipeline_orchestration.md",
        "docs/runbooks/stage_10_interpretation.md",
    ]:
        _write(repo / rel, "# runbook\n")
    _write(
        repo / "docs/runbooks/phase3_readiness_contract_map_2026-07-04.md",
        "\n".join(
            [
                "# Phase 3 Readiness Contract Map",
                "`ready_pending_approval`",
                "No full pipeline run, SSH, Slurm submission, or rsync",
                "Phase 1 -> Phase 2 -> Phase 3",
                "Track A signature-building data and Track B external-testing candidates remain separate",
                "TCGA remains prognostic context only",
                "post-run auditor",
                "explicit Phase 3 approval",
                "",
            ]
        ),
    )
    _write(
        repo / "docs/runbooks/phase3_preapproval_packet_2026-07-04.md",
        "\n".join(
            [
                "No full pipeline run, SSH, Slurm submission, or rsync pull was performed.",
                "I approve the Phase 3 full run on local/T7 with OUT_ROOT=<new_root>.",
                "I approve the Phase 3 full run on BibaLex with RUN_TAG=<tag> and BIBALEX_DATA_ROOT=<remote_data_root>.",
                "I approve the Phase 3 full run on BibaLex multi-job with RUN_TAG=<tag> and BIBALEX_DATA_ROOT=<remote_data_root>.",
                "current dry-run plan with final audit",
                "BibaLex durable single-job preview with final audit",
                "BibaLex durable single-job manifest with final audit",
                "BibaLex durable single-job script with final audit",
                "runtime_audits/bibalex_analysis_id_singlejob_current_preflight_20260704_postrun_audit",
                "BibaLex durable multi-job preview with final audit",
                "postrun_audit",
                "analysis_id_pipeline_postrun_audit.tsv",
                "`ready_pending_approval`",
                "",
            ]
        ),
    )
    _write(
        repo / "docs/runbooks/phase3_full_run_approval_packet_2026-07-03.md",
        "I approve the Phase 3 full run\nWithout one of those explicit approvals, do not execute Phase 3\n",
    )

    spec_root = repo / "specs/027-downstream-biological-interpretation"
    for name in ["spec.md", "plan.md", "research.md"]:
        _write(spec_root / name, f"# {name}\n")
    _write(
        spec_root / "quickstart.md",
        "\n".join(
            [
                "# Quickstart",
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
                "",
            ]
        ),
    )
    _write(
        spec_root / "benchmarks.md",
        "\n".join(
            [
                "# Benchmarks",
                "",
                "First reviewed-root output baseline",
                "3 analysis IDs",
                "3,412 sample-phenotype rows",
                "7,677 inferred-score rows",
                "runtime and memory baselines are still pending",
                "",
            ]
        ),
    )
    _write(
        spec_root / "tasks.md",
        "[x] T001\n[x] T061\n[x] T064\npython3.13 -m pytest tests -k interpretation -q\n",
    )

    module_root = repo / "src/pipeline/modules/10_interpretation"
    for name in ["__init__.py", "contracts.py", "enrich.py", "network.py", "hub_meta.py", "immunophenotype.py", "epi_infer.py"]:
        _write(module_root / name, "# module\n")
    _write(
        module_root / "contracts.py",
        "\n".join(
            [
                "def file_sha256(path):",
                "    return 'fixture'",
                "",
                "def interpretation_root(results_root, out=None):",
                "    expected = results_root / 'interpretation'",
                "    target = out or expected",
                "    target.relative_to(expected)",
                "    raise ValueError('Interpretation outputs must be written under')",
                "",
            ]
        ),
    )
    _write(repo / "src/pipeline/cli.py", "command=\"interpret enrich\"\ninterpret\n")
    _write(
        repo / "tests/unit/test_spec027_interpretation.py",
        "\n".join(
            [
                "def test_interpretation_path_guard_rejects_non_interpretation_output():",
                "    pass",
                "",
                "def test_interpret_network_gates_thin_signal_and_preserves_signature_checksum():",
                "    before = file_sha256('signature')",
                "    after = file_sha256('signature')",
                "    assert before == after",
                "",
            ]
        ),
    )

    registry = "\n".join(
        [
            "criteria_id\thope_group\trna_derivable\tdata_type\tgenes_or_signature\tmethod\tresponse_direction_hypothesis\tclaim_note",
            "hope_checkpoint_expression\tpredictive_biomarker\tyes\trna_expression\tCD274\tzscore\thigher\tproxy",
            "hope_msi_dmmr_proxy\tpredictive_biomarker\tyes\trna_expression\tMLH1\tzscore\tlower\tproxy",
            "hope_tcell_inflamed_gep\thot_cold\tyes\trna_signature\tCD8A\tmean\thigher\tproxy",
            "hope_cytolytic_activity\thot_cold\tyes\trna_signature\tGZMA;PRF1\tmean\thigher\tproxy",
            "hope_ifng_signature\thot_cold\tyes\trna_signature\tIFNG\tmean\thigher\tproxy",
            "hope_composite_rna\tcomposite\tyes\tderived\thope_ifng_signature\tmean\thigher\tproxy",
            "tmb\tpredictive_biomarker\tno\tdna_wes\tNA\trequires_wes\thigher\tspec020",
            "pdl1_ihc_tps_cps\tpredictive_biomarker\tno\tihc\tNA\trequires_ihc\thigher\tspec020",
            "ecog_performance_status\tpatient_criteria\tno\tclinical\tNA\trequires_clinical\tlower\tspec020",
            "irecist_pseudoprogression\tresponse_tracking\tno\tradiological\tNA\tresponse_definition_layer\tdurable\tspec010",
            "",
        ]
    )
    _write(repo / "configs/immunophenotype_criteria_registry.tsv", registry)

    scripts = {
        "scripts/run_analysis_id_pipeline.sh": "\n".join(
            [
                "ALLOW_ANALYSIS_ID_PIPELINE_RUN",
                "--execute",
                "--preflight",
                "phase3_execution_decision_manifest.tsv",
                "analysis_scope_mode",
                "tcga_behavior",
                "claim_boundary",
                "track_boundary",
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
                "",
            ]
        ),
        "scripts/bibalex_hpc/run_analysis_id_pipeline.sh": "\n".join(
            [
                "ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE",
                "--submit",
                "--preflight",
                "export PORTABLE_R_CONDA_PREFIX=",
                'if [[ -n "\\${PORTABLE_R_CONDA_PREFIX:-}" && -x "\\${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then',
                'export PATH="\\${PORTABLE_R_CONDA_PREFIX}/bin:\\${PATH}"',
                "fi",
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
                "bibalex_analysis_id_submission_preview_manifest.tsv",
                "network_action_preflight",
                "submission_preview_manifest",
                "out_root_remote",
                "downloads_root_remote",
                "portable_r_conda_prefix",
                "execution_gate",
                "inner_execution_gate",
                "sample_manifest",
                "expression_manifest",
                "gene_id_mapping",
                "gene_set_registry",
                "criteria_registry",
                "count_method",
                "allow_weak_gene_mapping",
                "claim_boundary",
                "track_boundary",
                "bibalex_singlejob_submission_manifest.tsv",
                "export ALLOW_ANALYSIS_ID_PIPELINE_RUN=1",
                "bash scripts/run_analysis_id_pipeline.sh --execute",
                "",
            ]
        ),
        "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh": "\n".join(
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
                "",
            ]
        ),
        "scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh": "ALLOW_BIBALEX_PULL_ANALYSIS_ID_RESULTS\n--pull\n--preflight\n",
        "scripts/audit_analysis_id_pipeline_run.py": "\n".join(
            [
                "#!/usr/bin/env python3",
                "def resolve_planned_path(raw, cwd, run_root=None):",
                "    return run_root / run_root.name",
                "out_path = resolve_planned_path(out_raw, cwd, run_root)",
                "check = 'planned_stage_output'",
                "check = 'interpretation_claim_classes'",
                "detail = 'blocked/skipped TCGA rows must include a reason'",
                "check = 'comparison_registry_merge_inputs'",
                "check = 'run_manifest_merge_inputs'",
                "check = 'bibalex_multijob_submission_manifest'",
                "check = 'bibalex_singlejob_submission_manifest'",
                "check = 'nmrbox_condor_submission_manifest'",
                "backend must be nmrbox_condor_single_job",
                "r_libs_user must record the NMRbox R package library path",
                "detail = 'portable_r_conda_prefix must record the Spec 094 runtime prefix'",
                "check = 'immune_effects_contract'",
                "detail = 'non-empty ssGSEA scores require cohort-level feature_source=gsva_ssgsea'",
                "check = 'interpretation_enrichment_contract'",
                "check = 'interpretation_network_contract'",
                "check = 'interpretation_hub_meta_contract'",
                "check = 'interpretation_immunophenotype_contract'",
                "check = 'interpretation_epigenetic_contract'",
                "detail = 'statistic=meta_effect_random'",
                "detail = 'HOPE RNA criteria scored or audited; non-RNA criteria skipped with routes'",
                "",
            ]
        ),
    }
    for rel, text in scripts.items():
        path = repo / rel
        _write(path, text)
        _make_executable(path)

    interp = repo / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation"
    for analysis_id in [
        "PRE_RESPONSE",
        "PAN_ICB_RESPONSE__PRE_TREATMENT",
        "ICI_COMBINATION_RESPONSE__PRE_TREATMENT",
    ]:
        enr = interp / "enrichment" / analysis_id
        _write(enr / "gsea.tsv", f"analysis_id\tstatistic\tclaim_class\n{analysis_id}\tmeta_effect_random\t{claim_class}\n")
        _write(enr / "ora.tsv", f"analysis_id\tclaim_class\n{analysis_id}\t{claim_class}\n")
        _write(enr / "dotplot_data.tsv", f"analysis_id\tclaim_class\n{analysis_id}\t{claim_class}\n")
        _write_repro(enr / "reproducibility")

    net = interp / "network/PRE_RESPONSE"
    _write(net / "hub_genes.tsv", f"analysis_id\tgene\tpermutation_fdr\tstatus\tclaim_class\nPRE_RESPONSE\t\t\tinsufficient_signal\t{claim_class}\n")
    _write_repro(net / "reproducibility")

    hub = interp / "hub_meta"
    _write(hub / "cross_cancer_hub_meta.tsv", f"gene\tmoderator_status\tstatus\tclaim_class\n\tcancer_as_low_dimension_moderator_only\tinsufficient_signal\t{claim_class}\n")
    _write_repro(hub / "reproducibility")

    imm = interp / "immunophenotype"
    _write(
        imm / "sample_phenotype.tsv",
        "\n".join(
            [
                "sample_id\tcriteria_id\tclaim_class",
                f"S1\thope_checkpoint_expression\t{claim_class}",
                f"S1\thope_tcell_inflamed_gep\t{claim_class}",
                f"S1\thope_ifng_signature\t{claim_class}",
                f"S1\thope_composite_rna\t{claim_class}",
                "",
            ]
        ),
    )
    _write(imm / "phenotype_response_assoc.tsv", f"criteria_id\tclaim_class\nhope_composite_rna\t{claim_class}\n")
    _write(
        imm / "immunophenotype_input_audit.tsv",
        "\n".join(
            [
                "module\tinput_name\tstatus\tclaim_class",
                f"immunophenotype\tssgsea_scores\tok\t{claim_class}",
                f"immunophenotype\thope_msi_dmmr_proxy\tmissing_direct_expression_or_matching_score\t{claim_class}",
                f"immunophenotype\thope_cytolytic_activity\tmissing_direct_expression_or_matching_score\t{claim_class}",
                "",
            ]
        ),
    )
    _write(
        imm / "hope_skipped_criteria.tsv",
        "\n".join(
            [
                "criteria_id\tdata_type\tmethod\tskip_reason\troute_to_spec\tclaim_class",
                "tmb\tdna_wes\trequires_wes\tnot_rna_derivable\tspec020\tdiscovery",
                "pdl1_ihc_tps_cps\tihc\trequires_ihc\tnot_rna_derivable\tspec020\tdiscovery",
                "ecog_performance_status\tclinical\trequires_clinical\tnot_rna_derivable\tspec020\tdiscovery",
                "irecist_pseudoprogression\tradiological\tresponse_definition_layer\tnot_rna_derivable\tspec010\tdiscovery",
                "",
            ]
        ),
    )
    _write_repro(imm / "reproducibility")

    epi = interp / "epigenetic"
    _write(epi / "inferred_scores.tsv", f"sample_id\tclaim_class\nS1\t{claim_class}\n")
    _write(epi / "epi_response_assoc.tsv", f"regulator_proxy\tclaim_class\nEPIGENETIC_IMMUNE_PRIMING\t{claim_class}\n")
    _write(epi / "epi_input_audit.tsv", f"check\tstatus\tclaim_class\ninput\tok\t{claim_class}\n")
    _write_repro(epi / "reproducibility")

    _write(
        interp / "interpret_run_manifest.yaml",
        "\n".join(
            [
                '{"command": "interpret enrich", "params": {"analysis_id": "PRE_RESPONSE"}}',
                '{"command": "interpret enrich", "params": {"analysis_id": "PAN_ICB_RESPONSE__PRE_TREATMENT"}}',
                '{"command": "interpret enrich", "params": {"analysis_id": "ICI_COMBINATION_RESPONSE__PRE_TREATMENT"}}',
                '{"command": "interpret network", "params": {"analysis_id": "PRE_RESPONSE"}}',
                '{"command": "interpret hub-meta"}',
                '{"command": "interpret immunophenotype"}',
                '{"command": "interpret epi-infer"}',
                "",
            ]
        ),
    )

    return repo


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _run_dashboard(repo: Path, out_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3.13",
            "scripts/phase3_readiness_dashboard.py",
            "--repo-root",
            str(repo),
            "--reviewed-root",
            str(repo / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance"),
            "--out-dir",
            str(out_dir),
        ],
        cwd=_repo_root(),
        env={**os.environ, "PYTHONPYCACHEPREFIX": str(out_dir / "pycache")},
        text=True,
        capture_output=True,
    )


def test_phase3_readiness_dashboard_passes_complete_fixture(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "status\tready_pending_approval" in result.stdout
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    assert not [row for row in rows if row["status"] == "fail"]
    assert any(row["check"] == "explicit_user_approval" and row["status"] == "warn" for row in rows)
    summary = (out_dir / "phase3_readiness_dashboard.md").read_text(encoding="utf-8")
    assert "ready_pending_approval" in summary
    assert "network_or_hpc_action: `none`" in summary


def test_phase3_readiness_dashboard_fails_validated_claim(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path, claim_class="validated")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    claim_rows = [row for row in rows if row["check"] == "claim_class_scan"]
    assert claim_rows
    assert claim_rows[0]["status"] == "fail"
    assert "validated" in claim_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_blank_claim(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/network/PRE_RESPONSE/hub_genes.tsv",
        "analysis_id\tclaim_class\nPRE_RESPONSE\t\n",
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    claim_rows = [row for row in rows if row["check"] == "claim_class_scan"]
    assert claim_rows
    assert claim_rows[0]["status"] == "fail"
    assert "<blank>" in claim_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_claim_class_column(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/epigenetic/epi_input_audit.tsv",
        "check\tstatus\ninput\tok\n",
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    claim_rows = [row for row in rows if row["check"] == "claim_class_scan"]
    assert claim_rows
    assert claim_rows[0]["status"] == "fail"
    assert "missing claim_class column" in claim_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_launcher(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    (repo / "scripts/run_analysis_id_pipeline.sh").unlink()
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    launcher_rows = [row for row in rows if row["check"] == "scripts/run_analysis_id_pipeline.sh"]
    assert launcher_rows
    assert launcher_rows[0]["status"] == "fail"


def test_phase3_readiness_dashboard_fails_missing_preapproval_boundary(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "docs/runbooks/phase3_preapproval_packet_2026-07-04.md", "# stale packet\n")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    boundary_rows = [row for row in rows if row["check"] == "phase3_preapproval_boundary"]
    assert boundary_rows
    assert boundary_rows[0]["status"] == "fail"
    assert "I approve the Phase 3 full run on local/T7" in boundary_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_preapproval_without_final_audit_evidence(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "docs/runbooks/phase3_preapproval_packet_2026-07-04.md",
        "\n".join(
            [
                "No full pipeline run, SSH, Slurm submission, or rsync pull was performed.",
                "I approve the Phase 3 full run on local/T7 with OUT_ROOT=<new_root>.",
                "I approve the Phase 3 full run on BibaLex with RUN_TAG=<tag> and BIBALEX_DATA_ROOT=<remote_data_root>.",
                "I approve the Phase 3 full run on BibaLex multi-job with RUN_TAG=<tag> and BIBALEX_DATA_ROOT=<remote_data_root>.",
                "`ready_pending_approval`",
                "",
            ]
        ),
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    boundary_rows = [row for row in rows if row["check"] == "phase3_preapproval_boundary"]
    assert boundary_rows
    assert boundary_rows[0]["status"] == "fail"
    assert "current dry-run plan with final audit" in boundary_rows[0]["detail"]
    assert "analysis_id_pipeline_postrun_audit.tsv" in boundary_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_preapproval_without_single_job_final_audit_evidence(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "docs/runbooks/phase3_preapproval_packet_2026-07-04.md",
        "\n".join(
            [
                "No full pipeline run, SSH, Slurm submission, or rsync pull was performed.",
                "I approve the Phase 3 full run on local/T7 with OUT_ROOT=<new_root>.",
                "I approve the Phase 3 full run on BibaLex with RUN_TAG=<tag> and BIBALEX_DATA_ROOT=<remote_data_root>.",
                "I approve the Phase 3 full run on BibaLex multi-job with RUN_TAG=<tag> and BIBALEX_DATA_ROOT=<remote_data_root>.",
                "current dry-run plan with final audit",
                "BibaLex durable multi-job preview with final audit",
                "postrun_audit",
                "analysis_id_pipeline_postrun_audit.tsv",
                "`ready_pending_approval`",
                "",
            ]
        ),
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    boundary_rows = [row for row in rows if row["check"] == "phase3_preapproval_boundary"]
    assert boundary_rows
    assert boundary_rows[0]["status"] == "fail"
    assert "BibaLex durable single-job preview with final audit" in boundary_rows[0]["detail"]
    assert "runtime_audits/bibalex_analysis_id_singlejob_current_preflight_20260704_postrun_audit" in boundary_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_contract_map(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    (repo / "docs/runbooks/phase3_readiness_contract_map_2026-07-04.md").unlink()
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    contract_rows = [row for row in rows if row["check"] == "phase3_readiness_contract_map"]
    assert contract_rows
    assert contract_rows[0]["status"] == "fail"
    assert "missing or empty" in contract_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_reactivated_track_b_ignored_study(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    triage = repo.parent / "specs/080-external-ici-treated-validation/discovery/ici_external_candidates_triaged.tsv"
    triage.write_text(
        triage.read_text(encoding="utf-8").replace(
            "GSE289743\tGEO\tignored_by_user",
            "GSE289743\tGEO\tnew_candidate_high",
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    boundary_rows = [row for row in rows if row["check"] == "ignored_triage_aliases"]
    assert boundary_rows
    assert boundary_rows[0]["status"] == "fail"
    assert "GSE289743:new_candidate_high" in boundary_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_shell_syntax_error(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    target = repo / "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh"
    _write(target, "if then\n")
    _make_executable(target)
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    syntax_rows = [
        row
        for row in rows
        if row["check"] == "shell_syntax:scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh"
    ]
    assert syntax_rows
    assert syntax_rows[0]["status"] == "fail"
    assert "syntax error" in syntax_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_decision_manifest_support(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "scripts/run_analysis_id_pipeline.sh", "ALLOW_ANALYSIS_ID_PIPELINE_RUN\n--execute\n--preflight\n")
    _make_executable(repo / "scripts/run_analysis_id_pipeline.sh")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    manifest_rows = [row for row in rows if row["check"] == "execution_decision_manifest"]
    assert manifest_rows
    assert manifest_rows[0]["status"] == "fail"
    assert "phase3_execution_decision_manifest.tsv" in manifest_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_sc006_checksum_test(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "tests/unit/test_spec027_interpretation.py", "def test_other():\n    pass\n")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    checksum_rows = [row for row in rows if row["check"] == "sc006_checksum_test"]
    assert checksum_rows
    assert checksum_rows[0]["status"] == "fail"
    assert "file_sha256" in checksum_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_stale_spec027_benchmark_stub(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "specs/027-downstream-biological-interpretation/benchmarks.md", "# Benchmarks\nNo baseline yet\n")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    benchmark_rows = [row for row in rows if row["check"] == "spec027_benchmark_baseline"]
    assert benchmark_rows
    assert benchmark_rows[0]["status"] == "fail"
    assert "First reviewed-root output baseline" in benchmark_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_stale_spec027_quickstart(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "specs/027-downstream-biological-interpretation/quickstart.md", 'PY="python3.13 -m pipeline.cli"\n')
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    quickstart_rows = [row for row in rows if row["check"] == "spec027_quickstart_contract"]
    assert quickstart_rows
    assert quickstart_rows[0]["status"] == "fail"
    assert 'PYTHON="${PYTHON:-python3.13}"' in quickstart_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_quickstart_enrichment_id(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    shutil.rmtree(
        repo
        / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/enrichment/PAN_ICB_RESPONSE__PRE_TREATMENT"
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    enrichment_rows = [row for row in rows if row["check"] == "enrichment_outputs"]
    assert enrichment_rows
    assert enrichment_rows[0]["status"] == "fail"
    assert "missing quickstart analysis_id folders=PAN_ICB_RESPONSE__PRE_TREATMENT" in enrichment_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_bad_hope_handoff_route(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo
        / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/immunophenotype/hope_skipped_criteria.tsv",
        "\n".join(
            [
                "criteria_id\tdata_type\tmethod\tskip_reason\troute_to_spec\tclaim_class",
                "tmb\tdna_wes\trequires_wes\tnot_rna_derivable\tspec010\tdiscovery",
                "pdl1_ihc_tps_cps\tihc\trequires_ihc\tnot_rna_derivable\tspec020\tdiscovery",
                "ecog_performance_status\tclinical\trequires_clinical\tnot_rna_derivable\tspec020\tdiscovery",
                "irecist_pseudoprogression\tradiological\tresponse_definition_layer\tnot_rna_derivable\tspec010\tdiscovery",
                "",
            ]
        ),
    )
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    hope_rows = [row for row in rows if row["check"] == "immunophenotype_hope"]
    assert hope_rows
    assert hope_rows[0]["status"] == "fail"
    assert "tmb:route_to_spec=spec010" in hope_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_interpretation_write_scope_guard(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "src/pipeline/modules/10_interpretation/contracts.py", "def other():\n    pass\n")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    guard_rows = [row for row in rows if row["check"] == "interpretation_write_scope_guard"]
    assert guard_rows
    assert guard_rows[0]["status"] == "fail"
    assert "def interpretation_root" in guard_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_orchestration_chain(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "scripts/run_analysis_id_pipeline.sh",
        "\n".join(
            [
                "ALLOW_ANALYSIS_ID_PIPELINE_RUN",
                "--execute",
                "--preflight",
                "phase3_execution_decision_manifest.tsv",
                "analysis_scope_mode",
                "tcga_behavior",
                "claim_boundary",
                "track_boundary",
                "design build",
                "design plan-runs",
                "de run",
                "meta run",
                "",
            ]
        ),
    )
    _make_executable(repo / "scripts/run_analysis_id_pipeline.sh")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    chain_rows = [row for row in rows if row["check"] == "analysis_id_orchestration_chain"]
    assert chain_rows
    assert chain_rows[0]["status"] == "fail"
    assert "report build" in chain_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_bibalex_submission_manifest_support(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        "ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE\n--submit\n--preflight\n",
    )
    _make_executable(repo / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    manifest_rows = [row for row in rows if row["check"] == "bibalex_submission_preview_manifest"]
    assert manifest_rows
    assert manifest_rows[0]["status"] == "fail"
    assert "bibalex_analysis_id_submission_preview_manifest.tsv" in manifest_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_single_job_portable_r_path(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh",
        "\n".join(
            [
                "ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE",
                "--submit",
                "--preflight",
                "export PORTABLE_R_CONDA_PREFIX=",
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
                "",
            ]
        ),
    )
    _make_executable(repo / "scripts/bibalex_hpc/run_analysis_id_pipeline.sh")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    path_rows = [row for row in rows if row["check"] == "bibalex_single_job_portable_r_path"]
    assert path_rows
    assert path_rows[0]["status"] == "fail"
    assert "PORTABLE_R_CONDA_PREFIX}/bin/Rscript" in path_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_postrun_audit_contract(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo / "scripts/audit_analysis_id_pipeline_run.py", "#!/usr/bin/env python3\n")
    _make_executable(repo / "scripts/audit_analysis_id_pipeline_run.py")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    audit_rows = [row for row in rows if row["check"] == "postrun_audit_contracts"]
    assert audit_rows
    assert audit_rows[0]["status"] == "fail"
    assert "def resolve_planned_path" in audit_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_stale_phase2_spec_link(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo.parent / "specs/093-bibalex-hpc-execution-backend/quickstart.md", "# old bootstrap only\n")
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    spec_rows = [row for row in rows if row["check"] == "spec093_analysis_id_backend"]
    assert spec_rows
    assert spec_rows[0]["status"] == "fail"
    assert "Analysis-ID Phase 3 Launcher" in spec_rows[0]["detail"]


def test_phase3_readiness_dashboard_fails_missing_interpret_quickstart_manifest(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    (repo / "results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/interpret_run_manifest.yaml").unlink()
    out_dir = tmp_path / "dashboard"
    result = _run_dashboard(repo, out_dir)
    assert result.returncode == 1
    rows = _read_tsv(out_dir / "phase3_readiness_dashboard.tsv")
    manifest_rows = [row for row in rows if row["check"] == "interpret_quickstart_manifest"]
    assert manifest_rows
    assert manifest_rows[0]["status"] == "fail"
    assert "missing or empty" in manifest_rows[0]["detail"]
