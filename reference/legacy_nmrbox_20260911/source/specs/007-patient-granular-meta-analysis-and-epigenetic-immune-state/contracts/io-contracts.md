# I/O Contracts: Patient-Granular Meta-Analysis and Epigenetic Immune-State Layer

## Contract 1: Patient Manifest

**Path**: `results/patient_manifest/patient_manifest.tsv`

**Granularity**: one row per `patient_uid`

**Required columns**:
`patient_uid`, `patient_id_raw`, `cohort_id`, `cancer_type`, `therapy_agent`, `response_label`, `response_source`, `has_pre`, `has_on`, `has_post`, `n_timepoints`, `is_longitudinal`, `is_stub`, `pre_sample_ids`, `on_sample_ids`, `post_sample_ids`, `unknown_sample_ids`

**Invariants**:
- `patient_uid` is non-empty and unique.
- `patient_uid` format is `<cohort_id>::<patient_id_raw>`.
- `response_label` is one of `responder`, `non_responder`, `unknown`.
- Boolean fields use `true` or `false`.
- Sample list fields use `|` as the separator and are empty when unavailable.

## Contract 2: Corrected Sample Annotations

**Path**: `results/patient_manifest/sample_annotations_corrected.tsv`

**Granularity**: one row per sample

**Required columns**:
`cohort_id`, `sample_id`, `patient_uid`, `patient_id_raw`, `timing_category`, `response_label`, `response_source`, `correction_source`, `is_stub`

**Invariants**:
- Every non-stub sample row in `configs/sample_manifest_curated.tsv` is represented unless explicitly excluded by command options.
- `patient_uid` joins to Contract 1.
- `timing_category` is one of `pre-treatment`, `on-treatment`, `post-treatment`, `unknown`.

## Contract 3: Patient Clinical Record

**Path**: `results/patient_manifest/patient_clinical_record.tsv`

**Granularity**: one row per `patient_uid`

**Required columns**:
`patient_uid`, `cancer_type`, `clinical_stage`, `icb_drug`, `icb_drug_class`, `prior_treatment_lines`, `biopsy_site`, `dose_schedule`, `source_field`

**Invariants**:
- `patient_uid` joins to Contract 1.
- Unknown fields are written as `unknown`, never blank.
- `icb_drug_class` is one of `PD1`, `PDL1`, `CTLA4`, `COMBO`, `OTHER`, `unknown`.

## Contract 4: Patient Manifest Validation

**Path**: `results/patient_manifest/patient_manifest_validation.tsv`

**Granularity**: one row per validation metric

**Required columns**:
`metric`, `expected_value`, `observed_value`, `status`, `notes`

**Invariants**:
- Includes row count comparison against `results/patient_manifest/patient_manifest_v1.tsv`.
- Includes response-label count comparison.
- Includes longitudinal patient count comparison.

## Contract 5: Manifest Divergences

**Path**: `results/manifest_build/divergences.tsv`

**Granularity**: one row per sample-level disagreement

**Required columns**:
`cohort_id`, `sample_id`, `patient_uid`, `field`, `sample_manifest_value`, `patient_manifest_value`, `resolution`, `source`

**Invariants**:
- `resolution` is `patient_manifest_wins` when patient manifest has a non-unknown value.
- File may contain only a header when no divergences are found.

## Contract 6: Comparison Registry

**Path**: `results/spec_007/comparison_registry.tsv`

**Granularity**: one row per DE contrast

**Required columns**:
`comparison_id`, `analysis_type`, `cohort_id`, `cancer_type`, `drug_class`, `contrast_definition`, `n_group_A`, `n_group_B`, `n_patients_A`, `n_patients_B`, `n_genes_tested`, `software`, `created_at`

**Invariants**:
- `comparison_id` is unique.
- `(cohort_id, analysis_type, contrast_definition)` is unique within a run.
- `analysis_type` is one of `PRE_RESPONSE`, `TREATMENT_DELTA`, `ON_RESPONSE`.
- `n_group_A` and `n_group_B` are positive integers.

## Contract 7: DE Output With Comparison ID

**Path pattern**: existing Stage 06 DE output path, with either a `comparison_id` column or a header metadata row accepted by downstream readers.

**Required columns added**:
`comparison_id`

**Invariants**:
- Every DE row joins to Contract 6 through `comparison_id`.
- Existing Spec 006 DE columns remain readable.

## Contract 8: Meta Summary

**Path**: `results/meta_analysis/meta_summary.tsv`

**Granularity**: one row per gene

**Required columns added**:
`gene_id`, `meta_p`, `meta_fdr`, `meta_effect_random`, `n_cohorts_contributed`, `n_patients_contributed`, `i2`, `loco_max_delta_padj`, `loco_unstable`

**Invariants**:
- `i2` is numeric between 0 and 100 when estimable.
- `loco_unstable` is `true` or `false`.
- Existing Spec 006 meta outputs remain readable.

## Contract 9: Meta Subgroups

**Path patterns**:
- `results/meta_analysis/subgroups/by_cancer_type/<cancer_type>.tsv`
- `results/meta_analysis/subgroups/by_drug_class/<drug_class>.tsv`

**Granularity**: one row per gene per subgroup file

**Required columns**:
`subgroup_type`, `subgroup_value`, `gene_id`, `meta_p`, `meta_fdr`, `meta_effect_random`, `n_cohorts_contributed`, `n_patients_contributed`, `i2`

**Invariants**:
- Each subgroup output contains only cohorts from that subgroup.
- Empty or underpowered subgroups are reported in a summary file rather than silently omitted.

## Contract 10: Gene Set Registry

**Path**: `configs/immune_gene_sets_registry.tsv`

**Required columns**:
`gene_set_id`, `gene_set_layer`, `gene_set_name`, `gmt_path`, `source`, `enabled`, `notes`

**Invariants**:
- `gene_set_layer` is one of `L1_ICB_PREDICTOR`, `L2_C7_EXHAUSTION`, `L3_HALLMARK`, `L4_EPIGENETIC`, `L5_HOPE_18`.
- Enabled rows have resolvable `gmt_path`.
- Layer 4 paths point to version-controlled files under `inputs/gene_sets/epigenetic_layer/`.

## Contract 11: ssGSEA Scores

**Path**: `results/immune_state/ssgsea_scores.tsv`

**Granularity**: one row per sample

**Required columns**:
`cohort_id`, `sample_id`, `patient_uid`, followed by one numeric column per enabled gene set.

**Invariants**:
- Every QC-pass sample has one row.
- Missing gene-set scores are written as `nan` only when overlap is below threshold and are reported in QC.

## Contract 12: Layer Summary

**Path**: `results/immune_state/layer_summary.tsv`

**Granularity**: one row per sample per layer

**Required columns**:
`cohort_id`, `sample_id`, `patient_uid`, `gene_set_layer`, `n_gene_sets_scored`, `mean_score`, `median_score`, `method`

**Invariants**:
- `method` is `ssgsea`.
- Deprecated proxy scores, if retained, use method label `immune_score_proxy_deprecated`.

## Contract 13: TCGA Epigenetic Layer Validation

**Path**: `results/tcga_projection/epigenetic_layer_tcga_validation.tsv`

**Granularity**: one row per `(gene_set, tcga_project)` test

**Required columns**:
`gene_set`, `tcga_project`, `n_patients`, `n_subtypes`, `kw_statistic`, `p_value`, `fdr`, `input_expression_path`, `input_subtype_path`

**Invariants**:
- `tcga_project` includes at least SKCM, BLCA, HNSC, LUAD, and KIRC when inputs exist.
- FDR is computed across all emitted tests.

