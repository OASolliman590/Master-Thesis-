# `endpoint_matrix.tsv`

## Row grain

One patient × endpoint instance × mapping version.

## Required columns

`patient_uid`, `study_id`, `outcome_id`, `raw_endpoint_label`, `endpoint_class`, `assessment_criteria`, `assessment_day`, `best_overall_response`, `canonical_category`, `orr_mapping`, `dcr_mapping`, `dcb_mapping`, `duration_threshold`, `event_time`, `event_indicator`, `censoring`, `evaluability`, `mapping_rule_version`, `mapping_confidence`, `discrepancy_status`, `source_locator`.

## Invariants

Raw labels are immutable; different endpoints do not overwrite each other; branch mappings are versioned; conflicts remain visible.

## Failure conditions

Undefined source binary endpoint, prohibited endpoint conversion, inconsistent censoring, missing criteria for canonical response or unresolved patient link.

## Receipt

The receipt reports raw/canonical category counts, discrepancies, exclusions, rule version and hashes.
