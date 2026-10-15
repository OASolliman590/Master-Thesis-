# `longitudinal_pair_matrix.tsv`

## Row grain

One patient × prespecified contrast/window × branch version.

## Required columns

`patient_uid`, `study_id`, `response_group`, `regimen_id`, `pre_specimen_uid`, `followup_specimen_uid`, `pre_assay_uid`, `followup_assay_uid`, `pre_day`, `followup_day`, `followup_category`, `same_lesion`, `same_platform`, `same_measurement_scale`, `pair_quality_status`, `contrast_id`, `window_version`, `inclusion_status`, `exclusion_reason`, `missing_followup_reason`, `admission_receipt_id`, `matrix_build_receipt_id`.

## Invariants

Pair choice is row-order invariant; on-treatment, post-treatment and progression are not pooled by default; multiple windows remain separate; intervening regimen changes are explicit.

## Failure conditions

No eligible pair, multiple follow-ups without a rule, chronology conflict, after-regimen-change contamination, endpoint conflict or incompatible measurement.

## Receipt

The receipt reports candidate and selected pair counts, quality states, missing follow-up mechanisms, window counts and hashes.
