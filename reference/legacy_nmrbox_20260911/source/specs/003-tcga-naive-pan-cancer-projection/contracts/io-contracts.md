# I/O Contracts: TCGA Treatment-Naive Pan-Cancer Projection (v1)

## Contract 1: GEO-to-TCGA Cancer Mapping

**Path**: `results/tcga_naive_projection/mapping/geo_tcga_cancer_mapping.tsv`

Required columns:

- `cohort_id`
- `geo_cancer_type`
- `tcga_project`
- `tcga_cancer_type`
- `mapping_basis`
- `mapping_confidence`
- `include_flag`
- `notes`

Allowed `mapping_confidence` values:

- `high`
- `moderate`
- `low`

## Contract 2: TCGA Project Registry (Config)

**Path**: `configs/tcga_naive_project_registry.tsv`

Required columns:

- `tcga_project`
- `tcga_cancer_type`
- `matched_geo_group`
- `priority`
- `analysis_include_flag`
- `required_outcomes`
- `notes`

## Contract 3: TCGA URL/Local Map

**Path**: `results/tcga_naive_projection/mapping/tcga_sample_map.tsv`

Required columns:

- `project`
- `expression_url`
- `survival_url`
- `local_expression_path`
- `local_survival_path`
- `status`

## Contract 4: TCGA Naive Patient Manifest

**Path**: `results/tcga_naive_projection/manifests/tcga_naive_patient_manifest.tsv`

Required columns:

- `project`
- `case_id`
- `sample_id`
- `naive_flag`
- `naive_rule_version`
- `treatment_any_flag`
- `treatment_evidence`
- `rna_available_flag`
- `survival_available_flag`
- `include_primary_projection`
- `exclude_reason`

Allowed `naive_flag` values:

- `1`
- `0`
- `NA`

## Contract 5: TCGA Clinical Flat Table

**Path**: `results/tcga_naive_projection/manifests/tcga_clinical_flat.tsv`

Required columns:

- `project`
- `case_id`
- `sample_id`
- `age_at_index`
- `sex`
- `race`
- `ethnicity`
- `vital_status`
- `days_to_death`
- `days_to_last_follow_up`
- `ajcc_pathologic_stage`
- `tumor_grade`
- `smoking_status`
- `pack_years_smoked`
- `alcohol_history`
- `molecular_subtype`

## Contract 6: TCGA Signature Scores

**Path**: `results/tcga_naive_projection/projection/{project}[_{tier}]_score_input.tsv`

Required columns:

- `project`
- `sample_id`
- `signature_name`
- `signature_tier`
- `n_up_genes_used`
- `n_down_genes_used`
- `signature_score`
- `score_group`
- `naive_flag`
- `include_primary_projection`

Allowed `signature_tier` values:

- `ALL`
- `GOLD_SILVER`
- `GOLD`

## Contract 7: Project Survival Input

**Path**: `results/tcga_naive_projection/projection/{project}[_{tier}]_survival_input.tsv`

Required columns:

- `sample_id`
- `signature_score`
- `signature_group`
- `OS.time`
- `OS`

Optional columns:

- `PFS.time`
- `PFS`
- `DSS.time`
- `DSS`

## Contract 8: Project Survival Stats

**Path**: `results/tcga_naive_projection/projection/{project}[_{tier}]_survival_stats.tsv`

Required columns:

- `project`
- `endpoint`
- `signature_tier`
- `n_samples`
- `n_events`
- `hazard_ratio`
- `lower_95_ci`
- `upper_95_ci`
- `p_value`
- `model_covariates`
- `status`

Companion status artifact:

- `results/tcga_naive_projection/projection/tcga_projection_status.tsv`

## Contract 9: Epidemiology Interaction Results

**Path**: `results/tcga_naive_projection/epidemiology/tcga_epidemiology_interactions.tsv`

Required columns:

- `project`
- `endpoint`
- `signature_tier`
- `covariate_family`
- `covariate_name`
- `interaction_term`
- `beta_interaction`
- `se_interaction`
- `p_value`
- `fdr`
- `n_samples`
- `status`
- `notes`

Allowed `covariate_family` values:

- `demographic`
- `clinical_stage`
- `exposure`
- `molecular_subtype`

Companion diagnostics/status artifacts:

- `results/tcga_naive_projection/epidemiology/tcga_epidemiology_model_diagnostics.tsv`
- `results/tcga_naive_projection/epidemiology/tcga_epidemiology_status.tsv`

## Contract 10: Pan-Cancer Survival Summary

**Path**: `results/tcga_naive_projection/reports/tcga_pan_cancer_survival_summary.tsv`

Required columns:

- `project`
- `tcga_cancer_type`
- `endpoint`
- `signature_tier`
- `hazard_ratio`
- `lower_95_ci`
- `upper_95_ci`
- `p_value`
- `n_samples`
- `n_events`
- `status`

## Contract 11: Pan-Cancer Heterogeneity Summary

**Path**: `results/tcga_naive_projection/reports/tcga_pan_cancer_heterogeneity.tsv`

Required columns:

- `endpoint`
- `signature_tier`
- `n_projects`
- `pooled_log_hr`
- `pooled_hr`
- `q_statistic`
- `i2_percent`
- `tau2`
- `status`

Companion artifacts:

- `results/tcga_naive_projection/reports/tcga_pan_cancer_forest.png`
- `results/tcga_naive_projection/reports/tcga_pan_cancer_status.tsv`

## Contract 12: Tier Comparison Summary

**Path**: `results/tcga_naive_projection/concordance_tiers/tier_performance_summary.tsv`

Required columns:

- `signature_tier`
- `n_genes`
- `n_projects_with_signal`
- `median_hr_abs_distance_from_1`
- `median_p_value`
- `best_project`
- `best_project_hr`
- `status`

Companion artifacts:

- `results/tcga_naive_projection/concordance_tiers/tier_signature_gold.tsv`
- `results/tcga_naive_projection/concordance_tiers/tier_signature_gold_silver.tsv`
- `results/tcga_naive_projection/concordance_tiers/tier_signature_all.tsv`
- `results/tcga_naive_projection/concordance_tiers/tier_gene_counts.tsv`
- `results/tcga_naive_projection/concordance_tiers/tier_performance_comparison.tsv`
- `results/tcga_naive_projection/concordance_tiers/tier_validation_status.tsv`

## Contract 13: Skip/Block Status Artifact

**Path**: `results/tcga_naive_projection/manifests/tcga_naive_manifest_status.tsv`

Required columns:

- `stage`
- `project`
- `status`
- `reason`
- `detail`

Allowed `status` values:

- `blocked`
- `completed`
- `skipped`

## Contract 14: Run Manifest

**Path**: `logs/run_manifest_*.yaml` (newline-delimited JSON records)

Required fields:

- `timestamp_utc`
- `command`
- `params`
- `outputs`
- `software`
