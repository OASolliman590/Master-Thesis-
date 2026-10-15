# `assay_feature_coverage.tsv`

## Row grain

One assay × required feature or programme × branch version.

## Required columns

`assay_uid`, `study_id`, `branch_id`, `feature_or_programme_id`, `feature_identifier`, `required`, `measured_state`, `measurement_reason`, `annotation_version`, `coverage_fraction`, `missingness_fraction`, `validation_status`, `receipt_id`.

## Invariants

Missing is not zero; not screened is distinct from measured negative; feature IDs are annotation-versioned; coverage for final tests is evaluated before role freeze.

## Failure conditions

Feature collision, incomplete mapping, required feature absent, annotation mismatch, unknown universe or assay not validated.

## Receipt

The assay/matrix receipt reports required and optional coverage, unresolved mappings and hashes.
