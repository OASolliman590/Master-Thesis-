# I/O Contracts: ICI Discovery + Immune-State Interpretation to PRAD Epigenetic Validation (v1)

## Contract 1: Analysis Cohort Manifest (Merged Phase)

**Path**: `../../02_data_inventory/analysis_cohorts_merged_v1.tsv`

Required columns:

- `cohort_id`
- `accession`
- `cancer_type`
- `therapy_class`
- `therapy_agent`
- `assay_type`
- `timing_category`
- `response_framework`
- `original_analysis_role`
- `analysis_role_merged`

## Contract 2: Retrieval Ledger

**Path**: `results/retrieval/retrieval_ledger.tsv`

Required columns:

- `cohort_id`
- `input_accession`
- `gse_id`
- `srp_id`
- `srx_id`
- `srr_id`
- `bioproject_id`
- `source_db`
- `source_uri`
- `retrieval_status`
- `retrieval_timestamp`
- `retrieval_note`

## Contract 3: Dataset Inspection Record

**Path**: `results/dataset_intake/dataset_inspection.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `assay_type`
- `file_format`
- `input_class`
- `read_layout`
- `is_paired_sample`
- `normalization_state`
- `intake_include_flag`
- `intake_exclude_reason`

Allowed `input_class` values:

- `FASTQ`
- `raw_counts`
- `processed_matrix`

## Contract 4: Cohort Promotion Audit

**Path**: `results/cohort_audit/cohort_promotion_audit.tsv`

Required columns:

- `candidate_id`
- `source_stream`
- `cancer_type`
- `therapy_context`
- `comparison_type`
- `resolved_accession`
- `publication`
- `already_in_inventory`
- `proposed_role`
- `decision`
- `notes`

Allowed `decision` values:

- `already_covered`
- `promote_discovery`
- `promote_validation`
- `context_only`
- `hold`

## Contract 5: Canonical Sample Manifest

**Path**: `configs/sample_manifest.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `patient_id`
- `cancer_type`
- `therapy_class`
- `therapy_agent`
- `specimen_type`
- `timing_category`
- `response_label`
- `pair_id`
- `input_class`
- `analysis_role`
- `include_flag`
- `exclude_reason`
- `response_label_source`

## Contract 6: Contrast Registry

**Path**: `configs/contrast_registry.yaml`

Required entries:

- `PRE_RESPONSE`
- `TREATMENT_DELTA`
- `ON_RESPONSE`

Each entry must define:

- required timing constraints
- required label constraints
- paired-design preference flag
- minimum sample thresholds

## Contract 7: Cohort QC Output

**Path**: `results/cohort_qc/{cohort_id}/`

Required files:

- `qc_metrics.tsv`
- `sample_outlier_flags.tsv`
- `cohort_qc_summary.md`

## Contract 8: Within-Cohort DE Output

**Path**: `results/within_cohort_de/{contrast}/{cohort_id}.tsv`

Required columns:

- `gene_id`
- `gene_symbol`
- `log2fc`
- `se_or_stat`
- `p_value`
- `fdr`
- `mean_expression`
- `contrast_family`
- `n_case`
- `n_control`
- `model_class`
- `normalization_method`

## Contract 9: Meta-Analysis Output

**Path**: `results/meta_analysis/{contrast}/meta_effects.tsv`

Required columns:

- `gene_id`
- `gene_symbol`
- `meta_effect`
- `meta_se`
- `meta_p_value`
- `meta_fdr`
- `heterogeneity_q`
- `heterogeneity_i2`
- `n_cohorts_contributed`
- `direction_consistency`

Companion leave-one-out sensitivity artifacts:

- `results/meta_analysis/{contrast}/meta_leave_one_out.tsv`
- `results/meta_analysis/{contrast}/meta_leave_one_out_summary.tsv`

`meta_leave_one_out.tsv` required columns:

- `gene_id`
- `gene_symbol`
- `omitted_cohort`
- `n_cohorts_contributed`
- `meta_effect_random`
- `meta_se_random`
- `meta_p_value`
- `direction_consistency`

`meta_leave_one_out_summary.tsv` required columns:

- `gene_id`
- `gene_symbol`
- `n_cohorts_total`
- `n_loo_runs`
- `full_meta_effect_random`
- `full_meta_fdr`
- `max_abs_delta_effect`
- `direction_flip_any`
- `loo_support_fraction`
- `signature_stability_label`
- `notes`

## Contract 10: Signature Sets

**Path**: `results/signature_sets/{contrast}_signature_v1.tsv`

Required columns:

- `gene_id`
- `gene_symbol`
- `signature_direction`
- `meta_fdr`
- `direction_consistency`
- `signature_tier`

## Contract 11: ESTIMATE Scores

**Path**: `results/immune_state/estimate_scores.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `immune_score`
- `stromal_score`
- `estimate_score`
- `purity_proxy`
- `score_scale`

## Contract 12: CIBERSORTx Absolute Scores

**Path**: `results/immune_state/cibersort_absolute.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `cell_type`
- `absolute_score`
- `p_value`
- `permutation_n`
- `signature_matrix`

## Contract 13: CIBERSORTx Relative Scores

**Path**: `results/immune_state/cibersort_relative.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `cell_type`
- `relative_fraction`
- `p_value`
- `permutation_n`
- `signature_matrix`

## Contract 14: ssGSEA Scores

**Path**: `results/immune_state/ssgsea_scores.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `gene_set_id`
- `gene_set_name`
- `ssgsea_score`
- `gene_set_version`

## Contract 15: HOPE Type Labels

**Path**: `results/immune_state/hope_types.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `cd274_state`
- `cd8b_state`
- `hope_type`
- `classification_threshold_source`

Allowed `hope_type` values:

- `A`
- `B`
- `C`
- `D`
- `unclassified`

## Contract 16: HOPE-18 Scores

**Path**: `results/immune_state/hope18_scores.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `hope18_score`
- `n_genes_used`
- `score_method`

## Contract 17: Marker Correlations

**Path**: `results/immune_state/marker_correlations.tsv`

Required columns:

- `cohort_id`
- `marker_gene`
- `immune_feature`
- `correlation_method`
- `correlation_value`
- `p_value`
- `fdr`

## Contract 18: Cohort-Level Immune Effects

**Path**: `results/immune_state/cohort_level_effects.tsv`

Required columns:

- `cohort_id`
- `contrast_family`
- `immune_feature`
- `effect_type`
- `effect_size`
- `se_or_stat`
- `p_value`
- `fdr`
- `model_class`
- `analysis_mode`

Allowed `analysis_mode` values:

- `continuous_primary`
- `median_sensitivity`
- `quartile_sensitivity`

## Contract 19: Concordance-Driven Validation Outputs

**Path**: `results/validation/`

Required files:

- `validation_concordance.tsv`
- `validation_concordance_summary.tsv`
- `validation_tcga_survival.tsv`
- `validation_leakage_guard.tsv`
- `validation_leakage_overlap_samples.tsv`
- `validation_summary.md`

`validation_concordance.tsv` required columns:

- `gene_id`
- `in_signature`
- `indirect_effect`
- `indirect_meta_fdr`
- `mega_effect`
- `mega_fdr`
- `concordance_tier`

`validation_concordance_summary.tsv` required columns:

- `contrast`
- `status`
- `n_genes_indirect_meta`
- `n_genes_mega`
- `n_genes_overlap`
- `n_gold`
- `n_silver`
- `n_bronze`
- `signature_gene_count`
- `signature_overlap_count`
- `signature_gold_count`
- `notes`

`validation_tcga_survival.tsv` required columns:

- `project`
- `n_samples`
- `hazard_ratio`
- `lower_95_ci`
- `upper_95_ci`
- `p_value`
- `status`
- `source_file`

`validation_leakage_guard.tsv` required columns:

- `check_name`
- `status`
- `n_discovery_samples`
- `n_tcga_samples`
- `n_overlap`
- `notes`

## Contract 20: TCGA GDC Sample Map

**Path**: `results/tcga_gdc_map/tcga_sample_map.tsv`

Required columns:

- `project`
- `expression_url`
- `survival_url`
- `local_expression_path`
- `local_survival_path`
- `status`

## Contract 21: TCGA Projection and Survival Inputs

**Path**: `results/tcga_projection/`

Per-project required files (for each mapped project with local data present):

- `{project}_survival_input.tsv`
- `{project}_survival_stats.tsv`
- `{project}_survival_km.png`

`{project}_survival_input.tsv` required columns:

- `sample_id`
- `signature_score`
- `signature_group`
- plus survival columns from the project survival table (for example `OS.time`, `OS`)

`{project}_survival_stats.tsv` required columns:

- `project`
- `n_samples`
- `hazard_ratio`
- `lower_95_ci`
- `upper_95_ci`
- `p_value`

## Contract 22: TCIA IPS Annotation Overlay

**Path**: `results/tcia_overlay/tcia_ips_annotations.tsv`

Required columns:

- `project`
- `sample_barcode`
- `ips_score`
- `ips_percentile`
- `annotation_source`
- `non_independent_tcga_flag`

## Contract 23: TCGA Immune-Methylation Integration

**Path**: `results/methylation_integration/tcga_immune_methylation_integration.tsv`

Required columns:

- `gene_id`
- `gene_symbol`
- `signature_direction`
- `prad_expression_state`
- `prad_immune_state`
- `comparator_immune_state`
- `ips_overlay_state`
- `prad_methylation_state`
- `promoter_probe_support`
- `epigenetic_repression_flag`
- `integration_priority_tier`

## Contract 24: Run Manifest

**Path**: `logs/run_manifest_*.yaml` (newline-delimited JSON records)

Required fields:

- `timestamp_utc`
- `command`
- `params`
- `outputs`
- `software`

## Contract 25: Mega-Analysis Outputs

**Path**: `results/mega_analysis/`

Required file:

- `mega_de_results.tsv`

`mega_de_results.tsv` required columns:

- `gene_id`
- `log2fc`
- `se_or_stat`
- `p_value`
- `fdr`

Optional concordance file (when indirect meta input is supplied):

- `concordance_indirect_vs_mega.tsv`

`concordance_indirect_vs_mega.tsv` required columns:

- `gene_id`
- `indirect_meta_fdr`
- `mega_fdr`
- `indirect_effect`
- `mega_effect`
- `concordance_tier`

## Contract 26: Visualization Index

**Path**: `results/router/visualizations/{track}/visualization_index.tsv`  
Alternative run-root form: `results/<run_id>/router/visualizations/{track}/visualization_index.tsv`

Required columns:

- `stage`
- `plot_type`
- `cohort_id`
- `contrast`
- `plot_path`
- `notes`

Expected companion artifact:

- `results/router/visualizations/{track}/visualization_index.md`
