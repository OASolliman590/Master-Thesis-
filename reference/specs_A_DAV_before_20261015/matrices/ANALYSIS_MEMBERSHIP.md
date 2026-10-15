# `analysis_membership.tsv`

## Row grain

One patient × named analysis branch × membership version.

## Required columns

`membership_id`, `patient_uid`, `study_id`, `branch_id`, `membership_version`, `inclusion_status`, `exclusion_reason_code`, `selected_specimen_uid`, `selected_assay_uid`, `selected_outcome_id`, `admission_receipt_id`, `split_assignment_id`, `created_utc`.

## Invariants

Membership is branch-specific; one patient may pass one branch and fail another; every included row references a passed admission receipt; no global include flag substitutes for this table.

## Failure conditions

Unknown branch, conflicting included/excluded state, missing selected entity, unadmitted cohort, invalid split role or duplicate membership.

## Receipt

The branch report records included/excluded counts and reason codes and links to the matrix/admission receipts.
