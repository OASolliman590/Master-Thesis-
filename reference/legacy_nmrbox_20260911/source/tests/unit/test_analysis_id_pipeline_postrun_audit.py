from __future__ import annotations

import csv
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture_run(tmp_path: Path, claim_class: str = "mechanism_hypothesis") -> Path:
    root = tmp_path / "analysis_id_pipeline_fixture"
    _write(root / "logs" / "run_manifest.yaml", "run: fixture\n")
    _write(
        root / "orchestration" / "phase3_execution_decision_manifest.tsv",
        "\n".join(
            [
                "key\tvalue",
                "analysis_scope_mode\texplicit_analysis_ids",
                "tcga_behavior\tmissing_tcga_map_status",
                "execution_gate\tALLOW_ANALYSIS_ID_PIPELINE_RUN=1 required for --execute",
                "reviewed_root_guard\trefuses OUT_ROOT containing analysis_id_runs_t7_20260607_stage07_scale_provenance",
                "claim_boundary\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only",
                "track_boundary\tTrack A derivation remains separate from Track B external candidates",
            ]
        )
        + "\n",
    )
    _write(root / "comparison_registry.tsv", "analysis_id\tcohort_id\nPRE_RESPONSE\tcohort1\n")
    _write(root / "design" / "analysis_sample_manifest.tsv", "sample_id\nS1\n")
    _write(root / "design" / "analysis_contrast_registry.tsv", "analysis_id\nPRE_RESPONSE\n")
    _write(root / "design" / "analysis_contrast_membership.tsv", "analysis_id\tsample_id\nPRE_RESPONSE\tS1\n")
    _write(root / "design" / "analysis_design_audit.md", "# audit\n")
    _write(root / "de" / "PRE_RESPONSE" / "cohort_de.tsv", "gene\tlogFC\nA\t1\n")
    _write(root / "meta" / "PRE_RESPONSE" / "meta_effects.tsv", "gene_symbol\tmeta_effect_random\nA\t1\n")
    _write(root / "signature" / "PRE_RESPONSE" / "responder_signature_tiered.tsv", "gene_symbol\nA\n")
    _write(root / "immune_state" / "ssgsea_scores.tsv", "sample_id\tSCORE\nS1\t1\n")
    _write(
        root / "immune_state" / "ssgsea_scores_long.tsv",
        "cohort_id\tsample_id\tgene_set_id\tgene_set_layer\tssgsea_score\tmethod\ncohort1\tS1\tT_CELL_INFLAMED_GEP_18\tL1_ICB_PREDICTOR\t1.2\tgsva_ssgsea_r\n",
    )
    _write(
        root / "immune_state" / "layer_summary.tsv",
        "cohort_id\tsample_id\tgene_set_layer\tmean_score\tmethod\ncohort1\tS1\tL1_ICB_PREDICTOR\t1.2\tssgsea\n",
    )
    _write(
        root / "immune_state" / "cohort_level_effects.tsv",
        "\n".join(
            [
                "cohort_id\tcontrast_family\timmune_feature\tfeature_source\tgene_set_layer\teffect_type\teffect_size\tse_or_stat\tp_value\tfdr\tmodel_class\tanalysis_mode\tn_responders\tn_non_responders\tmean_responder\tmean_non_responder",
                "cohort1\tPRE_RESPONSE\timmune_score\testimate\t\tresponse_association\t0.500000\t0.000000\t1\t1\twelch_t_test\tcontinuous_primary\t1\t1\t1.000000\t0.500000",
                "cohort1\tPRE_RESPONSE\tT_CELL_INFLAMED_GEP_18\tgsva_ssgsea\tL1_ICB_PREDICTOR\tresponse_association\t0.700000\t0.000000\t1\t1\twelch_t_test\tcontinuous_primary\t1\t1\t1.200000\t0.500000",
                "",
            ]
        ),
    )
    _write(
        root / "immune_state" / "marker_correlations.tsv",
        "cohort_id\tmarker_gene\timmune_feature\tcorrelation_method\tcorrelation_value\tp_value\tfdr\n",
    )
    _write(
        root / "immune_state" / "immune_effects_input_audit.tsv",
        "cohort_id\texpression_path\tmarker_correlation_status\tmarker_correlations_emitted\tnote\ncohort1\t\tmissing_expression\t0\tcohort-level immune effects were computed from immune score tables when available\n",
    )
    _write(root / "validation" / "PRE_RESPONSE" / "validation_readiness_status.tsv", "analysis_id\tstatus\nPRE_RESPONSE\tinternal_only\n")
    _write(
        root / "tcga_projection" / "PRE_RESPONSE" / "tcga_projection_status.tsv",
        "stage\tproject\tsignature_tier\tstatus\treason\tdetail\ntcga_project\t\tALL\tblocked\tmissing_tcga_map\tSet TCGA_MAP to enable prognostic projection.\n",
    )
    _write(root / "interpretation" / "enrichment" / "PRE_RESPONSE" / "gsea.tsv", f"analysis_id\tstatistic\tclaim_class\nPRE_RESPONSE\tmeta_effect_random\t{claim_class}\n")
    _write(root / "interpretation" / "enrichment" / "PRE_RESPONSE" / "ora.tsv", f"analysis_id\tclaim_class\nPRE_RESPONSE\t{claim_class}\n")
    _write(root / "interpretation" / "enrichment" / "PRE_RESPONSE" / "dotplot_data.tsv", f"analysis_id\tclaim_class\nPRE_RESPONSE\t{claim_class}\n")
    _write(root / "interpretation" / "network" / "PRE_RESPONSE" / "hub_genes.tsv", f"analysis_id\tpermutation_fdr\tstatus\tclaim_class\nPRE_RESPONSE\t\tinsufficient_signal\t{claim_class}\n")
    _write(root / "interpretation" / "hub_meta" / "cross_cancer_hub_meta.tsv", f"gene\tmoderator_status\tstatus\tclaim_class\nA\tcancer_as_low_dimension_moderator_only\tinsufficient_signal\t{claim_class}\n")
    _write(
        root / "interpretation" / "immunophenotype" / "sample_phenotype.tsv",
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
    _write(root / "interpretation" / "immunophenotype" / "phenotype_response_assoc.tsv", f"criteria_id\tclaim_class\nhope_composite_rna\t{claim_class}\n")
    _write(
        root / "interpretation" / "immunophenotype" / "hope_skipped_criteria.tsv",
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
    _write(
        root / "interpretation" / "immunophenotype" / "immunophenotype_input_audit.tsv",
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
    _write(root / "interpretation" / "epigenetic" / "inferred_scores.tsv", f"sample_id\tclaim_class\nS1\t{claim_class}\n")
    _write(root / "interpretation" / "epigenetic" / "epi_response_assoc.tsv", f"regulator_proxy\tclaim_class\nEPIGENETIC_IMMUNE_PRIMING\t{claim_class}\n")
    _write(root / "interpretation" / "epigenetic" / "epi_input_audit.tsv", f"module\tstatus\tclaim_class\nepigenetic\tok\t{claim_class}\n")
    _write(root / "reports" / "report.md", "# report\n")
    plan_rows = [
        ("design_build", "ALL", root / "design"),
        ("design_plan", "ALL", root / "orchestration" / "analysis_execution_plan.tsv"),
        ("stage06_de", "PRE_RESPONSE", root / "de" / "PRE_RESPONSE"),
        ("stage07_meta", "PRE_RESPONSE", root / "meta" / "PRE_RESPONSE"),
        ("signature", "PRE_RESPONSE", root / "signature" / "PRE_RESPONSE"),
        ("immune_score", "ALL", root / "immune_state"),
        ("immune_effects", "ALL", root / "immune_state"),
        ("validate", "PRE_RESPONSE", root / "validation" / "PRE_RESPONSE"),
        ("tcga_skip", "PRE_RESPONSE", root / "tcga_projection" / "PRE_RESPONSE"),
        ("interpret_enrich", "PRE_RESPONSE", root / "interpretation" / "enrichment" / "PRE_RESPONSE"),
        ("interpret_network", "PRE_RESPONSE", root / "interpretation" / "network" / "PRE_RESPONSE"),
        ("interpret_hub_meta", "ALL", root / "interpretation" / "hub_meta"),
        ("interpret_immunophenotype", "ALL", root / "interpretation" / "immunophenotype"),
        ("interpret_epi_infer", "ALL", root / "interpretation" / "epigenetic"),
        ("report", "ALL", root / "reports"),
        ("postrun_audit", "ALL", root / "orchestration" / "analysis_id_pipeline_postrun_audit.tsv"),
    ]
    plan = ["stage\tanalysis_id\toutput_dir\tcommand"]
    for stage, analysis_id, output in plan_rows:
        plan.append(f"{stage}\t{analysis_id}\t{output}\techo {stage}")
    _write(root / "orchestration" / "analysis_id_pipeline_plan.tsv", "\n".join(plan) + "\n")
    _write(root / "orchestration" / "analysis_execution_plan.tsv", "analysis_id\nPRE_RESPONSE\n")
    return root


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _append_plan_row(run_root: Path, stage: str, analysis_id: str, output_dir: Path, command: str = "echo stage") -> None:
    plan_path = run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    with plan_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stage}\t{analysis_id}\t{output_dir}\t{command}\n")


def _write_multijob_submission_manifest(run_root: Path) -> None:
    _write(
        run_root / "orchestration" / "bibalex_multijob_submission_manifest.tsv",
        "\n".join(
            [
                "key\tvalue",
                "design_job_id\t101",
                "immune_job_id\t103",
                "analysis_job_ids\t104",
                "final_job_id\t105",
                "analysis_ids\tPRE_RESPONSE",
                "comparison_registry_strategy\tper_analysis_shards_final_merge",
                "run_manifest_strategy\tper_job_shards_final_merge",
                "claim_boundary\tspec027 discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only",
                "track_boundary\tTrack A derivation remains separate from Track B external candidates",
            ]
        )
        + "\n",
    )


def _write_singlejob_submission_manifest(run_root: Path) -> None:
    _write(
        run_root / "orchestration" / "bibalex_singlejob_submission_manifest.tsv",
        "\n".join(
            [
                "key\tvalue",
                "backend\tbibalex_single_job",
                "slurm_job_id\t201",
                "job_name\tanalysis_id_pipeline_test",
                "run_tag\ttest",
                f"out_root\t{run_root}",
                "downloads_root\t/cluster/users/alex086u1/ici_thesis_pipeline_remote/data/audited_retrieval/retrieval/downloads_timer_all",
                "portable_r_conda_prefix\t/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor",
                "sample_manifest\tconfigs/sample_manifest_curated.tsv",
                "expression_manifest\tresults/geo_tables/geo_tables_summary.tsv",
                "gene_id_mapping\tconfigs/gene_id_mapping_human.tsv",
                "gene_set_registry\tconfigs/immune_gene_sets_registry.tsv",
                "criteria_registry\tconfigs/immunophenotype_criteria_registry.tsv",
                "count_method\tdeseq2",
                "analysis_ids\tPRE_RESPONSE",
                "pilot_only\t0",
                "tcga_map\t<unset>",
                "allow_empty_signature\t1",
                "allow_weak_gene_mapping\t0",
                "allow_welch_fallback\t0",
                "execution_gate\tALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1 outer gate; ALLOW_ANALYSIS_ID_PIPELINE_RUN=1 inner gate",
                "claim_boundary\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only",
                "track_boundary\tTrack A derivation remains separate from Track B external candidates",
            ]
        )
        + "\n",
    )


def _write_nmrbox_condor_submission_manifest(run_root: Path) -> None:
    _write(
        run_root / "orchestration" / "nmrbox_condor_submission_manifest.tsv",
        "\n".join(
            [
                "key\tvalue",
                "backend\tnmrbox_condor_single_job",
                "condor_cluster_id\t1247000",
                "condor_process_id\t0",
                "job_name\tanalysis_id_pipeline_test",
                "run_tag\ttest",
                f"out_root\t{run_root}",
                "remote_job_dir\t/home/nmrbox/0000/osoliman/ici_thesis_pipeline_remote/condor_jobs/test",
                "downloads_root\t/home/nmrbox/0000/osoliman/ici_thesis_pipeline_remote/data/audited_retrieval/retrieval/downloads_timer_all",
                "portable_r_conda_prefix\t<unset>",
                "r_libs_user\t/home/nmrbox/0000/osoliman/ici_thesis_pipeline_remote/R_libs/4.1",
                "sample_manifest\tconfigs/sample_manifest_curated.tsv",
                "expression_manifest\tresults/geo_tables/geo_tables_summary.tsv",
                "gene_id_mapping\tconfigs/gene_id_mapping_human.tsv",
                "gene_set_registry\tconfigs/immune_gene_sets_registry.tsv",
                "criteria_registry\tconfigs/immunophenotype_criteria_registry.tsv",
                "count_method\tdeseq2",
                "analysis_ids\tPRE_RESPONSE",
                "pilot_only\t0",
                "tcga_map\t<unset>",
                "allow_empty_signature\t1",
                "allow_weak_gene_mapping\t0",
                "allow_welch_fallback\t0",
                "request_cpus\t8",
                "request_memory\t32GB",
                "request_disk\t40GB",
                "execution_gate\tALLOW_NMRBOX_ANALYSIS_ID_PIPELINE=1 outer gate; ALLOW_ANALYSIS_ID_PIPELINE_RUN=1 inner gate",
                "claim_boundary\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only",
                "track_boundary\tTrack A derivation remains separate from Track B external candidates",
            ]
        )
        + "\n",
    )


def test_postrun_audit_passes_complete_fixture(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    out = tmp_path / "audit.tsv"
    summary = tmp_path / "audit.md"
    result = subprocess.run(
        [
            "python3.13",
            "scripts/audit_analysis_id_pipeline_run.py",
            "--run-root",
            str(run_root),
            "--analysis-id",
            "PRE_RESPONSE",
            "--out",
            str(out),
            "--summary-out",
            str(summary),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    summary_text = summary.read_text(encoding="utf-8")
    assert "status\tpass" in result.stdout
    assert {row["status"] for row in rows} <= {"pass", "warn"}
    assert any(row["check"] == "execution_decision_manifest" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "interpretation_enrichment_contract" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "interpretation_network_contract" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "interpretation_hub_meta_contract" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "interpretation_immunophenotype_contract" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "interpretation_epigenetic_contract" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "immune_effects_contract" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "interpretation_claim_classes" and row["status"] == "pass" for row in rows)
    assert "No failing checks." in summary_text
    assert "Spec 027 interpretation outputs" in summary_text


def test_postrun_audit_accepts_resumed_global_stages_with_payloads(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    plan_path = run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    resumed_stages = {
        "interpret_hub_meta",
        "interpret_immunophenotype",
        "interpret_epi_infer",
        "report",
        "postrun_audit",
    }
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    kept = [
        line
        for line in lines
        if not any(line.startswith(f"{stage}\t") for stage in resumed_stages)
    ]
    plan_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    _write(
        run_root / "orchestration" / "postrun_audit.tsv",
        "check\tscope\tstatus\tpath\tdetail\nprevious\tresume\tfail\t\told audit before resume\n",
    )

    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    rows = _read_tsv(out)
    coverage_rows = [row for row in rows if row["check"] == "planned_stage_coverage"]
    assert "status\tpass" in result.stdout
    assert coverage_rows
    assert coverage_rows[0]["status"] == "pass"
    assert "missing=none" in coverage_rows[0]["detail"]
    assert "resumed_payload=" in coverage_rows[0]["detail"]
    assert "interpret_hub_meta" in coverage_rows[0]["detail"]


def test_postrun_audit_fails_interpretation_gsea_wrong_statistic(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "interpretation" / "enrichment" / "PRE_RESPONSE" / "gsea.tsv",
        "analysis_id\tstatistic\tclaim_class\nPRE_RESPONSE\tp_value\tmechanism_hypothesis\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    enrichment_rows = [row for row in rows if row["check"] == "interpretation_enrichment_contract"]
    assert enrichment_rows
    assert enrichment_rows[0]["status"] == "fail"
    assert "statistic=p_value" in enrichment_rows[0]["detail"]


def test_postrun_audit_fails_missing_immune_effect_associations(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    (run_root / "immune_state" / "cohort_level_effects.tsv").unlink()
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    immune_rows = [row for row in rows if row["check"] == "immune_effects_contract"]
    assert immune_rows
    assert immune_rows[0]["status"] == "fail"
    assert "cohort_level_effects.tsv" in immune_rows[0]["detail"]


def test_postrun_audit_fails_ssgsea_scores_without_gsva_effect_rows(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "immune_state" / "cohort_level_effects.tsv",
        "\n".join(
            [
                "cohort_id\tcontrast_family\timmune_feature\tfeature_source\tgene_set_layer\teffect_type\teffect_size\tse_or_stat\tp_value\tfdr\tmodel_class\tanalysis_mode\tn_responders\tn_non_responders\tmean_responder\tmean_non_responder",
                "cohort1\tPRE_RESPONSE\timmune_score\testimate\t\tresponse_association\t0.500000\t0.000000\t1\t1\twelch_t_test\tcontinuous_primary\t1\t1\t1.000000\t0.500000",
                "",
            ]
        ),
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    immune_rows = [row for row in rows if row["check"] == "immune_effects_contract"]
    assert immune_rows
    assert immune_rows[0]["status"] == "fail"
    assert "feature_source=gsva_ssgsea" in immune_rows[0]["detail"]


def test_postrun_audit_fails_interpretation_network_without_permutation_fdr(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "interpretation" / "network" / "PRE_RESPONSE" / "hub_genes.tsv",
        "analysis_id\tstatus\tclaim_class\nPRE_RESPONSE\tinsufficient_signal\tmechanism_hypothesis\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    network_rows = [row for row in rows if row["check"] == "interpretation_network_contract"]
    assert network_rows
    assert network_rows[0]["status"] == "fail"
    assert "permutation_fdr" in network_rows[0]["detail"]


def test_postrun_audit_fails_interpretation_hope_bad_route(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "interpretation" / "immunophenotype" / "hope_skipped_criteria.tsv",
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
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    hope_rows = [row for row in rows if row["check"] == "interpretation_immunophenotype_contract"]
    assert hope_rows
    assert hope_rows[0]["status"] == "fail"
    assert "tmb:route_to_spec=spec010" in hope_rows[0]["detail"]


def test_postrun_audit_fails_interpretation_hope_unresolved_rna_criterion(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "interpretation" / "immunophenotype" / "immunophenotype_input_audit.tsv",
        "module\tinput_name\tstatus\tclaim_class\nimmunophenotype\tssgsea_scores\tok\tmechanism_hypothesis\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    hope_rows = [row for row in rows if row["check"] == "interpretation_immunophenotype_contract"]
    assert hope_rows
    assert hope_rows[0]["status"] == "fail"
    assert "hope_msi_dmmr_proxy" in hope_rows[0]["detail"]
    assert "hope_cytolytic_activity" in hope_rows[0]["detail"]


def test_postrun_audit_passes_bibalex_singlejob_submission_manifest(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write_singlejob_submission_manifest(run_root)
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    assert "status\tpass" in result.stdout
    assert any(row["check"] == "bibalex_singlejob_submission_manifest" and row["status"] == "pass" for row in rows)


def test_postrun_audit_fails_bibalex_singlejob_submission_manifest_missing_portable_r(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write_singlejob_submission_manifest(run_root)
    manifest = run_root / "orchestration" / "bibalex_singlejob_submission_manifest.tsv"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "portable_r_conda_prefix\t/cluster/users/alex086u1/ici_thesis_pipeline_remote/conda_envs/ici-r-bioconductor",
            "portable_r_conda_prefix\t<unset>",
        ),
        encoding="utf-8",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    manifest_rows = [row for row in rows if row["check"] == "bibalex_singlejob_submission_manifest"]
    assert manifest_rows
    assert manifest_rows[0]["status"] == "fail"
    assert "portable_r_conda_prefix" in manifest_rows[0]["detail"]


def test_postrun_audit_passes_nmrbox_condor_submission_manifest(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write_nmrbox_condor_submission_manifest(run_root)
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    assert "status\tpass" in result.stdout
    assert any(row["check"] == "nmrbox_condor_submission_manifest" and row["status"] == "pass" for row in rows)


def test_postrun_audit_fails_nmrbox_condor_submission_manifest_missing_r_libs(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write_nmrbox_condor_submission_manifest(run_root)
    manifest = run_root / "orchestration" / "nmrbox_condor_submission_manifest.tsv"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "r_libs_user\t/home/nmrbox/0000/osoliman/ici_thesis_pipeline_remote/R_libs/4.1",
            "r_libs_user\t<unset>",
        ),
        encoding="utf-8",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    manifest_rows = [row for row in rows if row["check"] == "nmrbox_condor_submission_manifest"]
    assert manifest_rows
    assert manifest_rows[0]["status"] == "fail"
    assert "r_libs_user" in manifest_rows[0]["detail"]


def test_postrun_audit_remaps_remote_plan_paths_to_local_pulled_root(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    remote_root = (
        Path("/cluster/users/alex086u1/ici_thesis_pipeline_remote/ici_thesis_pipeline/results")
        / run_root.name
    )
    plan_path = run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8").replace(str(run_root), str(remote_root)),
        encoding="utf-8",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        [
            "python3.13",
            "scripts/audit_analysis_id_pipeline_run.py",
            "--run-root",
            str(run_root),
            "--analysis-id",
            "PRE_RESPONSE",
            "--out",
            str(out),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    assert "status\tpass" in result.stdout
    stage_rows = [row for row in rows if row["check"] == "planned_stage_output"]
    assert stage_rows
    assert all(row["status"] == "pass" for row in stage_rows)
    assert all("/cluster/users/" not in row["path"] for row in stage_rows)


def test_postrun_audit_remaps_renamed_nmrbox_pull_root(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    remote_root = Path("/home/nmrbox/0000/osoliman/results/analysis_id_pipeline_phase3_full_axes")
    plan_path = run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8").replace(str(run_root), str(remote_root)),
        encoding="utf-8",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        [
            "python3.13",
            "scripts/audit_analysis_id_pipeline_run.py",
            "--run-root",
            str(run_root),
            "--analysis-id",
            "PRE_RESPONSE",
            "--out",
            str(out),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    stage_rows = [row for row in rows if row["check"] == "planned_stage_output"]
    assert "status\tpass" in result.stdout
    assert stage_rows
    assert all(row["status"] == "pass" for row in stage_rows)
    assert all("/home/nmrbox/" not in row["path"] for row in stage_rows)


def test_postrun_audit_passes_multijob_comparison_registry_merge(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    registry_dir = run_root / "comparison_registry_by_analysis"
    _write(registry_dir / "PRE_RESPONSE.tsv", "analysis_id\tcohort_id\nPRE_RESPONSE\tcohort1\n")
    _append_plan_row(run_root, "comparison_registry_merge", "ALL", run_root / "comparison_registry.tsv", "merge registries")
    _write_multijob_submission_manifest(run_root)
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    assert "status\tpass" in result.stdout
    assert any(row["check"] == "comparison_registry_merge_inputs" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "comparison_registry_merge_output" and row["status"] == "pass" for row in rows)


def test_postrun_audit_fails_multijob_comparison_registry_missing_inputs(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _append_plan_row(run_root, "comparison_registry_merge", "ALL", run_root / "comparison_registry.tsv", "merge registries")
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    merge_rows = [row for row in rows if row["check"] == "comparison_registry_merge_inputs"]
    assert merge_rows
    assert merge_rows[0]["status"] == "fail"
    assert "missing per-analysis registry directory" in merge_rows[0]["detail"]


def test_postrun_audit_passes_multijob_run_manifest_merge(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    manifest_dir = run_root / "logs" / "job_manifests"
    shards = {
        "design.jsonl": '{"command":"design build"}\n',
        "immune.jsonl": '{"command":"immune score"}\n',
        "analysis_PRE_RESPONSE.jsonl": '{"command":"de run","analysis_id":"PRE_RESPONSE"}\n',
        "finalize.jsonl": '{"command":"report build"}\n',
    }
    for name, text in shards.items():
        _write(manifest_dir / name, text)
    _write(run_root / "logs" / "run_manifest.yaml", "".join(shards.values()))
    _append_plan_row(run_root, "run_manifest_merge", "ALL", run_root / "logs" / "run_manifest.yaml", "merge manifests")
    _write_multijob_submission_manifest(run_root)
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    assert "status\tpass" in result.stdout
    assert any(row["check"] == "run_manifest_merge_inputs" and row["status"] == "pass" for row in rows)
    assert any(row["check"] == "run_manifest_merge_output" and row["status"] == "pass" for row in rows)


def test_postrun_audit_fails_multijob_run_manifest_missing_shard(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    manifest_dir = run_root / "logs" / "job_manifests"
    _write(manifest_dir / "design.jsonl", '{"command":"design build"}\n')
    _write(manifest_dir / "immune.jsonl", '{"command":"immune score"}\n')
    _write(manifest_dir / "finalize.jsonl", '{"command":"report build"}\n')
    _append_plan_row(run_root, "run_manifest_merge", "ALL", run_root / "logs" / "run_manifest.yaml", "merge manifests")
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    merge_rows = [row for row in rows if row["check"] == "run_manifest_merge_inputs"]
    assert merge_rows
    assert merge_rows[0]["status"] == "fail"
    assert "analysis_PRE_RESPONSE.jsonl" in merge_rows[0]["detail"]


def test_postrun_audit_passes_bibalex_multijob_submission_manifest(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    registry_dir = run_root / "comparison_registry_by_analysis"
    _write(registry_dir / "PRE_RESPONSE.tsv", "analysis_id\tcohort_id\nPRE_RESPONSE\tcohort1\n")
    _append_plan_row(run_root, "comparison_registry_merge", "ALL", run_root / "comparison_registry.tsv", "merge registries")
    _write_multijob_submission_manifest(run_root)
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    rows = _read_tsv(out)
    assert "status\tpass" in result.stdout
    assert any(row["check"] == "bibalex_multijob_submission_manifest" and row["status"] == "pass" for row in rows)


def test_postrun_audit_fails_bibalex_multijob_submission_manifest_bad_strategy(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    registry_dir = run_root / "comparison_registry_by_analysis"
    _write(registry_dir / "PRE_RESPONSE.tsv", "analysis_id\tcohort_id\nPRE_RESPONSE\tcohort1\n")
    _append_plan_row(run_root, "comparison_registry_merge", "ALL", run_root / "comparison_registry.tsv", "merge registries")
    _write(
        run_root / "orchestration" / "bibalex_multijob_submission_manifest.tsv",
        "\n".join(
            [
                "key\tvalue",
                "design_job_id\t101",
                "immune_job_id\t103",
                "analysis_job_ids\t104",
                "final_job_id\t105",
                "analysis_ids\tPRE_RESPONSE",
                "comparison_registry_strategy\tshared_canonical_registry",
                "run_manifest_strategy\tper_job_shards_final_merge",
                "claim_boundary\tspec027 discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only",
                "track_boundary\tTrack A derivation remains separate from Track B external candidates",
            ]
        )
        + "\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    manifest_rows = [row for row in rows if row["check"] == "bibalex_multijob_submission_manifest"]
    assert manifest_rows
    assert manifest_rows[0]["status"] == "fail"
    assert "comparison_registry_strategy" in manifest_rows[0]["detail"]


def test_postrun_audit_fails_validated_interpretation_claim(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path, claim_class="validated")
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    claim_rows = [row for row in rows if row["check"] == "interpretation_claim_classes"]
    assert claim_rows
    assert claim_rows[0]["status"] == "fail"
    assert "validated" in claim_rows[0]["detail"]
    assert "interpretation_claim_classes" in out.with_suffix(".md").read_text(encoding="utf-8")


def test_postrun_audit_fails_blank_interpretation_claim(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "interpretation" / "network" / "PRE_RESPONSE" / "hub_genes.tsv",
        "analysis_id\tclaim_class\nPRE_RESPONSE\t\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    claim_rows = [row for row in rows if row["check"] == "interpretation_claim_classes"]
    assert claim_rows
    assert claim_rows[0]["status"] == "fail"
    assert "<blank>" in claim_rows[0]["detail"]


def test_postrun_audit_fails_missing_interpretation_claim_class_column(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "interpretation" / "epigenetic" / "inferred_scores.tsv",
        "sample_id\nS1\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    claim_rows = [row for row in rows if row["check"] == "interpretation_claim_classes"]
    assert claim_rows
    assert claim_rows[0]["status"] == "fail"
    assert "missing claim_class column" in claim_rows[0]["detail"]


def test_postrun_audit_requires_tcga_or_tcga_skip_stage(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    plan_path = run_root / "orchestration" / "analysis_id_pipeline_plan.tsv"
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not line.startswith("tcga_skip\t")]
    plan_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    coverage_rows = [row for row in rows if row["check"] == "planned_stage_coverage"]
    assert coverage_rows
    assert coverage_rows[0]["status"] == "fail"
    assert "tcga_or_tcga_skip" in coverage_rows[0]["detail"]


def test_postrun_audit_requires_explicit_tcga_skip_reason(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "tcga_projection" / "PRE_RESPONSE" / "tcga_projection_status.tsv",
        "stage\tproject\tsignature_tier\tstatus\treason\tdetail\ntcga_project\t\tALL\tblocked\t\tmissing reason\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    tcga_rows = [row for row in rows if row["check"] == "tcga_outcome"]
    assert tcga_rows
    assert tcga_rows[0]["status"] == "fail"
    assert "blocked/skipped TCGA rows must include a reason" in tcga_rows[0]["detail"]


def test_postrun_audit_fails_missing_decision_manifest(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    (run_root / "orchestration" / "phase3_execution_decision_manifest.tsv").unlink()
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    decision_rows = [row for row in rows if row["check"] == "execution_decision_manifest"]
    assert decision_rows
    assert decision_rows[0]["status"] == "fail"
    assert "missing or empty" in decision_rows[0]["detail"]


def test_postrun_audit_fails_invalid_decision_manifest_tcga_behavior(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = _fixture_run(tmp_path)
    _write(
        run_root / "orchestration" / "phase3_execution_decision_manifest.tsv",
        "\n".join(
            [
                "key\tvalue",
                "analysis_scope_mode\texplicit_analysis_ids",
                "tcga_behavior\ticb_response_validation",
                "execution_gate\tALLOW_ANALYSIS_ID_PIPELINE_RUN=1 required for --execute",
                "reviewed_root_guard\trefuses OUT_ROOT containing analysis_id_runs_t7_20260607_stage07_scale_provenance",
                "claim_boundary\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only",
                "track_boundary\tTrack A derivation remains separate from external candidates",
            ]
        )
        + "\n",
    )
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--analysis-id", "PRE_RESPONSE", "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    decision_rows = [row for row in rows if row["check"] == "execution_decision_manifest"]
    assert decision_rows
    assert decision_rows[0]["status"] == "fail"
    assert "tcga_behavior" in decision_rows[0]["detail"]
    assert "Track A and Track B" in decision_rows[0]["detail"]


def test_postrun_audit_refuses_reviewed_root_token(tmp_path: Path) -> None:
    repo = _repo_root()
    run_root = tmp_path / "analysis_id_runs_t7_20260607_stage07_scale_provenance"
    run_root.mkdir()
    out = tmp_path / "audit.tsv"
    result = subprocess.run(
        ["python3.13", "scripts/audit_analysis_id_pipeline_run.py", "--run-root", str(run_root), "--out", str(out)],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    rows = _read_tsv(out)
    assert rows[0]["check"] == "reviewed_root_guard"
    assert rows[0]["status"] == "fail"
