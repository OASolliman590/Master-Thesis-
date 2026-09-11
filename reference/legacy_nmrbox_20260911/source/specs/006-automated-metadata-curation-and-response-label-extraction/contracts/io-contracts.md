# I/O Contracts: Automated Metadata Curation and Response Label Extraction

## Contract 1: Characteristics Extraction (Long Format)

**Path**: `results/spec_006/characteristics_extracted_long.tsv`
**Columns**: `cohort_id`, `sample_id`, `char_key`, `char_value`, `source` (soft_characteristics / soft_title / soft_source / soft_description)
**Rows**: One row per characteristic per sample. Expected: 5000-15000 rows for 30 cohorts.
**Invariant**: Every sample in `geo_tables_summary.tsv` that has a SOFT file is represented.

## Contract 2: Characteristics Extraction (Wide Format)

**Path**: `results/spec_006/characteristics_extracted_wide.tsv`
**Columns**: `cohort_id`, `sample_id`, `title`, `source_name`, `description`, then one column per unique characteristic key (e.g., `response`, `tissue`, `age`, `sex`, etc.)
**Rows**: One row per sample. Expected: ~1097 rows.
**Invariant**: Column names are normalized (lowercase, spaces → underscores).

## Contract 3: Characteristic Key Inventory

**Path**: `results/spec_006/characteristic_key_inventory.tsv`
**Columns**: `char_key`, `n_cohorts`, `n_samples`, `cohort_list`, `relevance_class` (response / timing / clinical / demographic / other)
**Rows**: One row per unique characteristic key across all cohorts.

## Contract 4: Response Label Mapping Config

**Path**: `configs/response_label_mapping.tsv`
**Columns**: `cohort_id`, `source_field`, `source_value`, `pipeline_label`, `notes`
**Rows**: One row per mapping rule. First rows use `cohort_id=DEFAULT` for RECIST mapping.
**Invariant**: Every `source_value` found in the data for response-related fields has a mapping.

## Contract 5: Timing Label Mapping Config

**Path**: `configs/timing_label_mapping.tsv`
**Columns**: `cohort_id`, `source_field`, `source_value`, `pipeline_label`, `notes`
**Invariant**: Every timing-related value has a mapping.

## Contract 6: Response Labels Mapped

**Path**: `results/spec_006/response_labels_mapped.tsv`
**Columns**: `cohort_id`, `sample_id`, `response_label`, `timing_category`, `mapping_source`, `confidence` (high / medium / low)
**Rows**: One row per sample that has a response or timing label.
**Invariant**: `response_label` is one of: `responder`, `non_responder`, `unknown`. `timing_category` is one of: `pre_treatment`, `on_treatment`, `post_treatment`, `unknown`.

## Contract 7: Expression Aliases

**Path**: `results/spec_006/expression_aliases.tsv`
**Columns**: `cohort_id`, `sample_id`, `expression_sample_alias`, `match_method` (title_exact / title_transform / description_match / manual)
**Rows**: One row per sample that has a non-GSM expression column name.

## Contract 8: DE Eligibility Report

**Path**: `results/spec_006/de_eligibility_report.tsv`
**Columns**: `cohort_id`, `n_total`, `n_included`, `n_responder`, `n_non_responder`, `n_pre_treatment`, `de_eligible`, `comparison_track`, `blocker_reason`
**Rows**: One row per cohort.
**Invariant**: `de_eligible=true` iff `n_responder >= 2 AND n_non_responder >= 2` (for PRE_RESPONSE track, also requires pre-treatment timing).

## Contract 9: Curation Reconciliation Report

**Path**: `results/spec_006/curation_reconciliation_report.md`
**Sections**: Executive summary, per-cohort extraction results, response mapping decisions, DE eligibility changes, signature comparison (before vs after), remaining gaps.

## Contract 10: Updated Sample Manifest

**Path**: `configs/sample_manifest_curated.tsv` (in-place update)
**New/updated columns**: `response_label`, `timing_category`, `include_flag`, `expression_sample_alias`
**Invariant**: Existing include_flag=true rows are NOT modified. Only rows with include_flag=false may be promoted.
