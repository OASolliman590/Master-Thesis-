# `split_registry.tsv`

## Row grain

One patient × immutable split version.

## Required columns

`split_assignment_id`, `patient_uid`, `study_id`, `trial_id`, `publication_family_id`, `split_version`, `split_role`, `assignment_rule`, `prior_exposure_state`, `overlap_status`, `feature_coverage_status`, `frozen_utc`, `freeze_receipt_id`.

## Invariants

A patient has one role per split version; originating-study/trial/publication relationships are checked; final-test roles are assigned before performance inspection; prior exposure is never reset by path changes.

## Failure conditions

Patient/study overlap across incompatible roles, unknown exposure for untouched claim, post-performance assignment, missing required source or inadequate feature coverage.

## Receipt

The freeze receipt records aggregate membership, disjointness checks, exposure state, rule/config hashes and reviewer.
