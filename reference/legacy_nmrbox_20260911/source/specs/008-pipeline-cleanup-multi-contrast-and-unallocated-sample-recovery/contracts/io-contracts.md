# I/O Contracts: Spec 008

## Contract 1: Sample Allocation Matrix

Path: `results/spec_008/sample_allocation_matrix.tsv`

Columns:

`cohort_id`, `sample_id`, `patient_uid`, `pair_id`, `timing_category`, `response_label`, `include_flag`, `assigned_bucket`, `eligible_contrasts`, `role`, `eligible`, `unallocated_reason`, `curation_priority`, `source_fields`

Invariant:

- One row per curated sample manifest row.
- Every row has exactly one `assigned_bucket`.
- Unknown-response rows must use `UNALLOCATED_REQUIRES_CURATION`.

## Contract 2: Cohort Allocation Summary

Path: `results/spec_008/cohort_allocation_summary.tsv`

Columns:

`cohort_id`, `n_samples`, `n_pre_response`, `n_post_response`, `n_on_response`, `n_treatment_delta`, `n_qc_only`, `n_unallocated`

## Contract 3: Unallocated Samples

Path: `results/spec_008/unallocated_samples.tsv`

Same columns as Contract 1, filtered to `assigned_bucket=UNALLOCATED_REQUIRES_CURATION`.

## Contract 4: Reproducibility Bundle

Path: `results/spec_008/reproducibility/`

Files:

- `commands.sh`
- `environment.yml`
- `checksums.sha256`

## Contract 5: Multi-Contrast Router

Path: `results/<run>/router/track_manifests/multi_contrast.tsv`

Triggered by:

```bash
python -m pipeline.cli router run --contrasts PRE_RESPONSE,POST_RESPONSE,ON_RESPONSE,TREATMENT_DELTA ...
```

## Contract 6: DE Outputs

Path:

`results/<run>/router/within_cohort_de/<track_or_multi>/<contrast_id>/<cohort_id>.tsv`

Required columns include:

`comparison_id`, `gene_id`, `log2fc`, `p_value`, `fdr`, `contrast_family`, `n_case`, `n_control`, `model_class`

