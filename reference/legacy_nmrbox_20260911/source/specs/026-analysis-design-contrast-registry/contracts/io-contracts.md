# I/O Contracts: Spec 026 — Analysis Design Contrast Registry

## `analysis_sample_manifest.tsv`

Required columns:

`cohort_id`, `sample_id`, `patient_id`, `pair_id`, `timing_category`, `response_label`, `include_flag`, `analysis_eligible`, `analysis_exclusion_reason`, `assay_type`, `input_class`, `drug_group`, `therapy_class_raw`, `therapy_agent_raw`, `cancer_group`, `cancer_type_raw`, `analysis_role`

## `analysis_contrast_registry.tsv`

Required columns:

`analysis_id`, `analysis_family`, `legacy_contrast_alias`, `interpretation_label`, `contrast_type`, `timing_scope`, `pairing_required`, `drug_scope`, `cancer_scope`, `raw_scope_label`, `case_definition`, `control_definition`, `n_cohorts_total`, `n_cohorts_eligible`, `n_case_samples`, `n_control_samples`, `n_pairs_case`, `n_pairs_control`, `feasibility_status`, `blocker_reason`, `priority_status`, `notes`

## `analysis_contrast_membership.tsv`

Required columns:

`analysis_id`, `cohort_id`, `sample_id`, `patient_id`, `pair_id`, `timing_category`, `response_label`, `membership_role`, `drug_group`, `therapy_class_raw`, `therapy_agent_raw`, `cancer_group`, `cancer_type_raw`, `assay_type`, `input_class`

## `analysis_design_audit.md`

Required sections:

- Overview
- Feasible analyses
- Blocked analyses
- Timing by response counts
- Drug by timing counts
- Cancer by timing counts

