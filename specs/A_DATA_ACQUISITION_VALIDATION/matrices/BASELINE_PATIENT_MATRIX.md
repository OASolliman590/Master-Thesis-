# `baseline_patient_matrix.tsv`

## Row grain

One eligible patient for one named branch and matrix version.

## Required columns

`patient_uid`, `study_id`, `cancer_type`, `cancer_subtype`, `selected_baseline_specimen_uid`, `selected_assay_uid`, `expression_matrix_column`, `treatment_regimen_id`, `checkpoint_class`, `prior_ici`, `prior_systemic_treatment`, `biopsy_site`, `raw_endpoint_label`, `canonical_orr`, `canonical_dcr`, `endpoint_evaluability`, `measurement_unit`, `feature_annotation`, `inclusion_status`, `exclusion_reason`, `split_role`, `prior_exposure_state`, `admission_receipt_id`, `matrix_build_receipt_id`.

## Invariants

Exactly one included row per patient at this branch/version; selected specimen and assay resolve to registries; selection is outcome-independent; NE/unknown handling follows the endpoint rule; split assignment is frozen where required; no raw patient ID is exported publicly.

## Failure conditions

Duplicate patient, unresolved specimen/assay/header, outcome-informed selection, unsupported assay, unadmitted source, split leakage, unknown exposure for final-test status or hash mismatch.

## Receipt

A `matrix_build_receipt` records counts, exclusions, feature coverage, input/code/config/output hashes and validation status.
