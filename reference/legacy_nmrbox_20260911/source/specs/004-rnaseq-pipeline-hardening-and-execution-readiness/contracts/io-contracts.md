# I/O Contracts: RNA-seq Pipeline Hardening and Execution Readiness (v1)

## Contract 1: Cohort Readiness Status

**Path**: `results/<run_root>/router/cohort_readiness_status.tsv`

Required columns:

- `cohort_id`
- `track_name`
- `readiness_status`
- `execution_status`
- `blocking_reason`
- `is_sync_stub`
- `has_expression`
- `contrast_eligible`

Allowed `readiness_status` values:

- `analyzed`
- `blocked`
- `stub_excluded`
- `routed_not_executed`

## Contract 2: Run Readiness Summary

**Path**: `results/<run_root>/reports/run_readiness_summary.tsv`

Required columns:

- `run_root`
- `track_name`
- `n_routed_cohorts`
- `n_analyzed_cohorts`
- `n_blocked_cohorts`
- `n_stub_excluded_cohorts`
- `n_meta_eligible_cohorts`
- `signature_status`
- `validation_status`

## Contract 3: Evidence Readiness Status

**Path**: `results/<run_root>/reports/evidence_readiness_status.tsv`

Required columns:

- `stage`
- `status`
- `reason`
- `detail`

Expected stage values:

- `router`
- `meta_analysis`
- `signature`
- `immune_effects`
- `validation`

## Contract 4: Immune Effects Smoke Outputs

**Path**: smoke-test fixture output directory

Required files:

- `marker_correlations.tsv`
- `cohort_level_effects.tsv`

Required condition:

- command completes without unresolved local-config scope errors

