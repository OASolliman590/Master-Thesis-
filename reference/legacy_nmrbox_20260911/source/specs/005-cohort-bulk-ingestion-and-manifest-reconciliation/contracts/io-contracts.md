# I/O Contracts: Cohort Bulk Ingestion and Manifest Reconciliation (Spec-005)

## Contract 1: Cohort ID Reconciliation Ledger

**Path**: `configs/cohort_id_reconciliation_ledger.tsv`

Required columns:

- `canonical_cohort_id`
- `accession`
- `t7_folder_name`
- `legacy_cohort_id`
- `timer_stub_id`
- `reconciliation_status`
- `in_geo_tables`
- `in_sample_manifest`

Required row count:

- `30` (one per GEO accession in reconciled merged30 set)

## Contract 2: Extended GEO Tables Summary

**Path**: `results/geo_tables/geo_tables_summary.tsv`

Required columns:

- `cohort_id`
- `downloads_folder` (new)
- `n_samples`
- `n_expression_candidates`
- `source_type_selected`
- `primary_expression_file`

Required row count:

- `30`

## Contract 3: Curated Sample Manifest Rebuild

**Path**: `configs/sample_manifest_curated.tsv`

Required invariants:

- zero rows where `sample_id` contains `_SYNC_STUB`
- all rows are real sample-level rows (`sync_status != added_cohort_stub_no_sample_rows`)
- minimum real-row target: `>= 400`

## Contract 4: Supplementary Metadata Merge

**Path**: `results/spec_005/supplementary_metadata_merged.tsv`

Required columns:

- `cohort_id`
- `sample_id`
- `response_label_soft`
- `response_label_supplementary`
- `timing_category_soft`
- `timing_category_supplementary`
- `disease_soft`
- `disease_supplementary`
- `response_disagreement_flag`
- `timing_disagreement_flag`
- `disease_disagreement_flag`

## Contract 5: Ingestion Reconciliation Report

**Path**: `results/spec_005/ingestion_reconciliation_report.md`

Required sections:

- Cohort inventory
- Expression resolution
- Sample coverage
- Contrast eligibility
- Curation tier assignment
- Evidence run summary
