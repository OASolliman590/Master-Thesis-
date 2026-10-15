# `patient_timepoint_long.tsv`

## Row grain

One patient × biological specimen × assay × canonical/raw timepoint.

## Required columns

`patient_uid`, `study_id`, `specimen_uid`, `assay_uid`, `cancer_type`, `regimen_id`, `treatment_exposure_id`, `timing_raw_text`, `canonical_timing_category`, `exact_relative_day`, `lesion_site`, `scheduled_or_indicated`, `raw_endpoint_label`, `endpoint_assessment_day`, `pairability`, `pair_quality_status`, `inclusion_status`, `exclusion_reason`, `source_locator`, `admission_receipt_id`.

## Invariants

All specimens and follow-ups are preserved; chronology and treatment episode resolve; blood and tumour remain distinct; repeated sequencing is not a new specimen; no row-order inference.

## Failure conditions

Unresolved patient/specimen link, chronology conflict, missing treatment reference, unknown biological compartment or assay incompatibility.

## Receipt

The build receipt reports patients, specimens, assays, timepoint categories, unresolved records and hashes.
