from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_analysis_id_launcher_dry_run_writes_full_stage_plan(tmp_path: Path) -> None:
    repo = _repo_root()
    out_root = tmp_path / "analysis_id_dry_run"
    env = {
        **os.environ,
        "OUT_ROOT": str(out_root),
        "ANALYSIS_IDS": "PRE_RESPONSE",
        "PYTHON_BIN": "python3.13",
    }
    result = subprocess.run(
        ["bash", "scripts/run_analysis_id_pipeline.sh", "--dry-run"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    plan = out_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    assert plan.exists(), result.stdout + result.stderr
    text = plan.read_text(encoding="utf-8")
    assert "design_build\tALL" in text
    assert "stage06_de\tPRE_RESPONSE" in text
    assert "stage07_meta\tPRE_RESPONSE" in text
    assert "signature\tPRE_RESPONSE" in text
    assert "immune_score\tALL" in text
    assert "validate\tPRE_RESPONSE" in text
    assert "tcga_skip\tPRE_RESPONSE" in text
    assert "interpret_epi_infer\tALL" in text
    assert "report\tALL" in text
    assert "postrun_audit\tALL" in text
    assert "audit_analysis_id_pipeline_run.py" in text
    assert "--analysis-id PRE_RESPONSE" in text
    decision = out_root / "orchestration" / "phase3_execution_decision_manifest.tsv"
    assert decision.exists(), result.stdout + result.stderr
    decision_text = decision.read_text(encoding="utf-8")
    assert "analysis_scope_mode\texplicit_analysis_ids" in decision_text
    assert "analysis_ids_requested\tPRE_RESPONSE" in decision_text
    assert "tcga_behavior\tmissing_tcga_map_status" in decision_text


def test_analysis_id_launcher_dry_run_unset_ids_writes_scope_note(tmp_path: Path) -> None:
    repo = _repo_root()
    out_root = tmp_path / "analysis_id_dry_run_unset"
    env = {
        **os.environ,
        "OUT_ROOT": str(out_root),
        "PYTHON_BIN": "python3.13",
    }
    env.pop("ANALYSIS_IDS", None)
    result = subprocess.run(
        ["bash", "scripts/run_analysis_id_pipeline.sh", "--dry-run"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    note = out_root / "orchestration" / "analysis_id_pipeline_dry_run_scope.txt"
    assert note.exists(), result.stdout + result.stderr
    note_text = note.read_text(encoding="utf-8")
    assert "dry-run previews the pilot IDs only" in note_text
    assert "execute mode" in note_text
    assert "PRE_RESPONSE PAN_ICB_RESPONSE__PRE_TREATMENT ICI_COMBINATION_RESPONSE__PRE_TREATMENT" in note_text
    assert "dry_run_scope_note" in result.stdout
    decision = out_root / "orchestration" / "phase3_execution_decision_manifest.tsv"
    assert decision.exists(), result.stdout + result.stderr
    decision_text = decision.read_text(encoding="utf-8")
    assert "analysis_scope_mode\tdesign_derived_all_feasible" in decision_text
    assert "analysis_ids_requested\t<unset>" in decision_text
    assert "execute_scope_detail\tApproved --execute derives feasible analysis IDs from the Spec-026 design plan." in decision_text
    assert "decision_manifest" in result.stdout


def test_analysis_id_launcher_preflight_writes_readiness_report(tmp_path: Path) -> None:
    repo = _repo_root()
    out_root = tmp_path / "analysis_id_preflight"
    env = {
        **os.environ,
        "OUT_ROOT": str(out_root),
        "ANALYSIS_IDS": "PRE_RESPONSE",
        "PYTHON_BIN": "python3.13",
    }
    result = subprocess.run(
        ["bash", "scripts/run_analysis_id_pipeline.sh", "--preflight"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    report = out_root / "orchestration" / "analysis_id_pipeline_preflight.tsv"
    assert report.exists(), result.stdout + result.stderr
    text = report.read_text(encoding="utf-8")
    assert "python_bin\tpass" in text
    assert "sample_manifest\tpass" in text
    assert "expression_manifest\tpass" in text
    assert "downloads_root\tpass" in text
    assert "tcga_map\twarn" in text
    assert "analysis_ids\tpass\tPRE_RESPONSE" in text
    assert "preflight_status\tpass" in result.stdout
    decision = out_root / "orchestration" / "phase3_execution_decision_manifest.tsv"
    assert decision.exists(), result.stdout + result.stderr
    decision_text = decision.read_text(encoding="utf-8")
    assert "analysis_scope_mode\texplicit_analysis_ids" in decision_text
    assert "claim_boundary\t" in decision_text
    assert "decision_manifest" in result.stdout


def test_analysis_id_launcher_preflight_fails_missing_required_file(tmp_path: Path) -> None:
    repo = _repo_root()
    out_root = tmp_path / "analysis_id_preflight_fail"
    env = {
        **os.environ,
        "OUT_ROOT": str(out_root),
        "ANALYSIS_IDS": "PRE_RESPONSE",
        "PYTHON_BIN": "python3.13",
        "CRITERIA_REGISTRY": str(tmp_path / "missing_criteria.tsv"),
    }
    result = subprocess.run(
        ["bash", "scripts/run_analysis_id_pipeline.sh", "--preflight"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    report = out_root / "orchestration" / "analysis_id_pipeline_preflight.tsv"
    assert report.exists(), result.stdout + result.stderr
    assert "criteria_registry\tfail" in report.read_text(encoding="utf-8")
    assert "preflight_status\tfail" in result.stdout


def test_analysis_id_launcher_execute_requires_explicit_gate(tmp_path: Path) -> None:
    repo = _repo_root()
    env = {
        **os.environ,
        "OUT_ROOT": str(tmp_path / "blocked_run"),
        "ANALYSIS_IDS": "PRE_RESPONSE",
        "PYTHON_BIN": "python3.13",
    }
    result = subprocess.run(
        ["bash", "scripts/run_analysis_id_pipeline.sh", "--execute"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 3
    assert "ALLOW_ANALYSIS_ID_PIPELINE_RUN is not 1" in result.stderr


def test_bibalex_analysis_id_launcher_requires_submission_gate() -> None:
    repo = _repo_root()
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/run_analysis_id_pipeline.sh"],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 3
    assert "ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE is not 1" in result.stderr


def test_bibalex_analysis_id_preflight_writes_local_preview(tmp_path: Path) -> None:
    repo = _repo_root()
    preflight_dir = tmp_path / "bibalex_preflight"
    env = {
        **os.environ,
        "BIBALEX_DATA_ROOT": "/cluster/users/alex086u1/ici_thesis_pipeline_remote/data/audited_retrieval",
        "BIBALEX_PREFLIGHT_OUT": str(preflight_dir),
        "RUN_TAG": "testtag",
        "ANALYSIS_IDS": "PRE_RESPONSE",
    }
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/run_analysis_id_pipeline.sh", "--preflight"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    report = preflight_dir / "bibalex_analysis_id_pipeline_preflight.tsv"
    preview = preflight_dir / "run_analysis_id_pipeline_testtag.sh"
    submission = preflight_dir / "bibalex_analysis_id_submission_preview_manifest.tsv"
    assert report.exists(), result.stdout + result.stderr
    assert preview.exists(), result.stdout + result.stderr
    assert submission.exists(), result.stdout + result.stderr
    report_text = report.read_text(encoding="utf-8")
    preview_text = preview.read_text(encoding="utf-8")
    submission_text = submission.read_text(encoding="utf-8")
    assert "data_root\tpass" in report_text
    assert "reviewed_root_guard\tpass" in report_text
    assert "submission_preview_manifest\tpass" in report_text
    assert "preflight_status\tpass" in result.stdout
    assert "submission_manifest\t" in result.stdout
    assert "#SBATCH --job-name=analysis_id_pipeline_testtag" in preview_text
    assert "export PORTABLE_R_CONDA_PREFIX='/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor'" in preview_text
    assert 'if [[ -n "${PORTABLE_R_CONDA_PREFIX:-}" && -x "${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then' in preview_text
    assert 'export PATH="${PORTABLE_R_CONDA_PREFIX}/bin:${PATH}"' in preview_text
    assert "export SAMPLE_MANIFEST='configs/sample_manifest_curated.tsv'" in preview_text
    assert "export EXPRESSION_MANIFEST='results/geo_tables/geo_tables_summary.tsv'" in preview_text
    assert "export GENE_ID_MAPPING='configs/gene_id_mapping_human.tsv'" in preview_text
    assert "export GENE_SET_REGISTRY='configs/immune_gene_sets_registry.tsv'" in preview_text
    assert "export CRITERIA_REGISTRY='configs/immunophenotype_criteria_registry.tsv'" in preview_text
    assert "export COUNT_METHOD='deseq2'" in preview_text
    assert 'export RUN_MANIFEST="${OUT_ROOT}/logs/run_manifest.yaml"' in preview_text
    assert "export ALLOW_ANALYSIS_ID_PIPELINE_RUN=1" in preview_text
    assert "export ALLOW_EMPTY_SIGNATURE='1'" in preview_text
    assert "export ALLOW_WEAK_GENE_MAPPING='0'" in preview_text
    assert "export ALLOW_WELCH_FALLBACK='0'" in preview_text
    assert "export ANALYSIS_IDS='PRE_RESPONSE'" in preview_text
    assert 'bibalex_singlejob_submission_manifest.tsv' in preview_text
    assert "backend\\tbibalex_single_job" in preview_text
    assert "slurm_job_id\\t%s\\n" in preview_text
    assert "execution_gate\\tALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1 outer gate; ALLOW_ANALYSIS_ID_PIPELINE_RUN=1 inner gate" in preview_text
    assert "claim_boundary\\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only" in preview_text
    assert "track_boundary\\tTrack A derivation remains separate from Track B external candidates" in preview_text
    assert "network_action_preflight\tnone" in submission_text
    assert "out_root_remote\t" in submission_text
    assert "downloads_root_remote\t" in submission_text
    assert "portable_r_conda_prefix\t" in submission_text
    assert "portable_r_conda_prefix\t/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor" in submission_text
    assert "sample_manifest\tconfigs/sample_manifest_curated.tsv" in submission_text
    assert "expression_manifest\tresults/geo_tables/geo_tables_summary.tsv" in submission_text
    assert "gene_id_mapping\tconfigs/gene_id_mapping_human.tsv" in submission_text
    assert "gene_set_registry\tconfigs/immune_gene_sets_registry.tsv" in submission_text
    assert "criteria_registry\tconfigs/immunophenotype_criteria_registry.tsv" in submission_text
    assert "count_method\tdeseq2" in submission_text
    assert "allow_empty_signature\t1" in submission_text
    assert "allow_weak_gene_mapping\t0" in submission_text
    assert "allow_welch_fallback\t0" in submission_text
    assert "analysis_ids\tPRE_RESPONSE" in submission_text
    assert "execution_gate\tALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1 required for --submit" in submission_text
    assert "inner_execution_gate\tALLOW_ANALYSIS_ID_PIPELINE_RUN=1 set inside remote job" in submission_text
    assert "claim_boundary\t" in submission_text
    assert "track_boundary\t" in submission_text


def test_bibalex_analysis_id_preflight_requires_data_root(tmp_path: Path) -> None:
    repo = _repo_root()
    preflight_dir = tmp_path / "bibalex_preflight_fail"
    env = {
        **os.environ,
        "BIBALEX_PREFLIGHT_OUT": str(preflight_dir),
    }
    env.pop("BIBALEX_DATA_ROOT", None)
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/run_analysis_id_pipeline.sh", "--preflight"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    report = preflight_dir / "bibalex_analysis_id_pipeline_preflight.tsv"
    assert report.exists(), result.stdout + result.stderr
    assert "data_root\tfail" in report.read_text(encoding="utf-8")
    assert "preflight_status\tfail" in result.stdout


def test_bibalex_multijob_analysis_id_preflight_writes_dependency_preview(tmp_path: Path) -> None:
    repo = _repo_root()
    preflight_dir = tmp_path / "bibalex_multijob_preflight"
    env = {
        **os.environ,
        "BIBALEX_DATA_ROOT": "/cluster/users/alex086u1/ici_thesis_pipeline_remote/data/audited_retrieval",
        "BIBALEX_PREFLIGHT_OUT": str(preflight_dir),
        "RUN_TAG": "multijobtag",
        "ANALYSIS_IDS": "PRE_RESPONSE",
    }
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh", "--preflight"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    report = preflight_dir / "bibalex_analysis_id_multijob_preflight.tsv"
    submission = preflight_dir / "bibalex_analysis_id_multijob_submission_preview_manifest.tsv"
    submitter = preflight_dir / "submit_analysis_id_pipeline_multijobtag.sh"
    design = preflight_dir / "analysis_id_pipeline_multijobtag_00_design.sh"
    fanout = preflight_dir / "analysis_id_pipeline_multijobtag_10_submit_fanout.sh"
    analysis = preflight_dir / "analysis_id_pipeline_multijobtag_20_analysis_task.sh"
    immune = preflight_dir / "analysis_id_pipeline_multijobtag_30_immune_task.sh"
    finalize = preflight_dir / "analysis_id_pipeline_multijobtag_40_finalize.sh"
    for path in [report, submission, submitter, design, fanout, analysis, immune, finalize]:
        assert path.exists(), result.stdout + result.stderr
    report_text = report.read_text(encoding="utf-8")
    submission_text = submission.read_text(encoding="utf-8")
    submitter_text = submitter.read_text(encoding="utf-8")
    fanout_text = fanout.read_text(encoding="utf-8")
    analysis_text = analysis.read_text(encoding="utf-8")
    immune_text = immune.read_text(encoding="utf-8")
    finalize_text = finalize.read_text(encoding="utf-8")
    design_text = design.read_text(encoding="utf-8")
    assert "preflight_status\tpass" in result.stdout
    assert "network_action_preflight\tpass\tnone" in report_text
    assert "multijob_submission_preview_manifest\tpass" in report_text
    assert "multi_job_strategy\tdependency_fanout" in submission_text
    assert "comparison_registry_strategy\tper_analysis_shards_final_merge" in submission_text
    assert "run_manifest_strategy\tper_job_shards_final_merge" in submission_text
    assert "execution_gate\tALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB=1 required for --submit-multijob" in submission_text
    assert "inner_execution_gate\tALLOW_ANALYSIS_ID_PIPELINE_RUN=1 set inside remote jobs" in submission_text
    assert "sbatch --parsable" in submitter_text
    assert "--run-manifest \"${RUN_MANIFEST}\"" in design_text
    assert "export PORTABLE_R_CONDA_PREFIX='/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor'" in design_text
    assert 'if [[ -n "${PORTABLE_R_CONDA_PREFIX:-}" && -x "${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then' in design_text
    assert 'export PATH="${PORTABLE_R_CONDA_PREFIX}/bin:${PATH}"' in design_text
    assert "export PORTABLE_R_CONDA_PREFIX='/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor'" in analysis_text
    assert 'export PATH="${PORTABLE_R_CONDA_PREFIX}/bin:${PATH}"' in analysis_text
    assert "export PORTABLE_R_CONDA_PREFIX='/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor'" in immune_text
    assert 'export PATH="${PORTABLE_R_CONDA_PREFIX}/bin:${PATH}"' in immune_text
    assert "export PORTABLE_R_CONDA_PREFIX='/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor'" in finalize_text
    assert 'export PATH="${PORTABLE_R_CONDA_PREFIX}/bin:${PATH}"' in finalize_text
    assert "--dependency=afterok:${DESIGN_JOB}" in submitter_text
    assert "analysis_execution_plan.tsv" in fanout_text
    assert "analysis_id_pipeline_plan.tsv" in fanout_text
    assert "stage06_de" in fanout_text
    assert "stage07_meta" in fanout_text
    assert "comparison_registry_merge" in fanout_text
    assert "run_manifest_merge" in fanout_text
    assert "postrun_audit" in fanout_text
    assert "comparison_registry_strategy" in fanout_text
    assert "run_manifest_strategy" in fanout_text
    assert "tcga_skip" in fanout_text
    assert "interpret_hub_meta" in fanout_text
    assert "report" in fanout_text
    assert "--dependency=afterok:${SLURM_JOB_ID}" in fanout_text
    assert "job_manifests/design.jsonl" in design_text
    assert "de run" in analysis_text
    assert "meta run" in analysis_text
    assert "signature derive" in analysis_text
    assert "comparison_registry_by_analysis" in analysis_text
    assert '--comparison-registry "${analysis_comparison_registry}"' in analysis_text
    assert '--comparison-registry "${OUT_ROOT}/comparison_registry.tsv"' not in analysis_text
    assert 'analysis_${analysis_id}.jsonl' in analysis_text
    assert "interpret enrich" in analysis_text
    assert "interpret network" in analysis_text
    assert "immune score" in immune_text
    assert "immune effects" in immune_text
    assert "immune.jsonl" in immune_text
    assert "comparison_registry_by_analysis" in finalize_text
    assert "comparison_registry.tsv.tmp" in finalize_text
    assert "Merged comparison registry is empty" in finalize_text
    assert "finalize.jsonl" in finalize_text
    assert "run_manifest.yaml.tmp" in finalize_text
    assert "No per-analysis run manifest shards found" in finalize_text
    assert "interpret hub-meta" in finalize_text
    assert "interpret immunophenotype" in finalize_text
    assert "report build" in finalize_text
    assert "audit_analysis_id_pipeline_run.py" in finalize_text
    assert "analysis_id_pipeline_postrun_audit.tsv" in finalize_text


def test_bibalex_multijob_submission_requires_explicit_gate(tmp_path: Path) -> None:
    repo = _repo_root()
    env = {
        **os.environ,
        "BIBALEX_DATA_ROOT": "/cluster/users/alex086u1/ici_thesis_pipeline_remote/data/audited_retrieval",
        "BIBALEX_PREFLIGHT_OUT": str(tmp_path / "blocked_multijob"),
        "RUN_TAG": "blockedmultijob",
    }
    env.pop("ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB", None)
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh", "--submit-multijob"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 3
    assert "ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB is not 1" in result.stderr


def test_bibalex_lightweight_pull_preflight_writes_preview(tmp_path: Path) -> None:
    repo = _repo_root()
    preview_dir = tmp_path / "pull_preview"
    dest = tmp_path / "pulled_results"
    env = {
        **os.environ,
        "REMOTE_RUN_ROOT": "/cluster/users/alex086u1/ici_thesis_pipeline_remote/ici_thesis_pipeline/results/analysis_id_pipeline_testtag",
        "BIBALEX_PULL_PREVIEW_OUT": str(preview_dir),
        "DEST": str(dest),
    }
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh", "--preflight"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    preview = preview_dir / "bibalex_analysis_id_pull_preview.tsv"
    assert preview.exists(), result.stdout + result.stderr
    text = preview.read_text(encoding="utf-8")
    assert "network_action\tnone" in text
    assert "retrieval/downloads" in text
    assert "fastq" in text
    assert "pull_status\tpreview_only" in result.stdout


def test_bibalex_lightweight_pull_requires_explicit_gate(tmp_path: Path) -> None:
    repo = _repo_root()
    preview_dir = tmp_path / "pull_preview_gate"
    env = {
        **os.environ,
        "REMOTE_RUN_ROOT": "/cluster/users/alex086u1/ici_thesis_pipeline_remote/ici_thesis_pipeline/results/analysis_id_pipeline_testtag",
        "BIBALEX_PULL_PREVIEW_OUT": str(preview_dir),
    }
    result = subprocess.run(
        ["bash", "scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh", "--pull"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 3
    assert "ALLOW_BIBALEX_PULL_ANALYSIS_ID_RESULTS is not 1" in result.stderr
    assert (preview_dir / "bibalex_analysis_id_pull_preview.tsv").exists()
