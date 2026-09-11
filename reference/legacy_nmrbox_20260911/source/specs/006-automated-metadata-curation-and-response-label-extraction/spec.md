# Feature Specification: Automated Metadata Curation and Response Label Extraction (v1)

**Feature Branch**: `006-automated-metadata-curation-and-response-label-extraction`
**Created**: 2026-04-18
**Status**: Draft
**Input**: Spec-005 verification evidence run (2026-04-18) showing 3 DE-eligible cohorts due to missing response labels, despite 501 samples across 12 cohorts having response data in SOFT `characteristics_ch1` fields.

## Context Lock

### Current Baseline

Already implemented (Spec-005):

- 30 GEO cohorts ingested, 1097 sample rows in manifest, 0 sync stubs
- 5 cohorts curated with include_flag=true (446 samples)
- 3 cohorts DE-eligible for PRE_RESPONSE (gse126044, gse78220, gse218989)
- `expression_sample_alias` column added for GSM-to-column mapping
- Full pipeline completes end-to-end with 1-gene signature (CD274/PD-L1, tier_2)
- extract-geo-metadata (MINiML XML) already run for all 30 cohorts

### Current Review Findings That Drive This Spec

- 25 cohorts have `include_flag=false` due to missing curated response labels
- 12 of those 25 cohorts have response data in SOFT `characteristics_ch1` fields (501 samples total)
- The pipeline's `_infer_response_from_text()` heuristic only searches title/source fields, not characteristics
- Characteristics field names are heterogeneous across studies (e.g., `response`, `recist`, `tumor.response`, `best response on immunotherapy (recist)`, `pathologic_response`, `dth response`)
- Meta-analysis power is severely limited at 3 DE-eligible cohorts; extracting the available response data could yield 8-10 DE-eligible cohorts
- External tools evaluated:
  - `getGeoMetadata` (R): parses characteristics into tidy columns; R dependency unnecessary since we have SOFT files locally
  - `extract-geo-metadata` (Python/MINiML): already integrated; found no additional response labels beyond SOFT

This spec automates metadata extraction from GEO `characteristics_ch1` fields, builds expression sample alias mappings, and re-curates the manifest to maximize DE-eligible cohorts.

## User Scenarios & Testing

### User Story 1 - Extract structured metadata from GEO characteristics (Priority: P1)

As the analysis owner, I need the pipeline to extract all key-value pairs from SOFT `characteristics_ch1` fields into a structured, searchable table so I can identify which samples have response labels, timing, and other clinical annotations.

**Independent Test**: Running the extractor on all 30 cohorts produces a flat TSV with one row per sample and columns for every unique characteristic key, with 501+ samples having non-empty response fields.

### User Story 2 - Map heterogeneous response labels to pipeline categories (Priority: P1)

As the analysis owner, I need a configurable mapping from the diverse GEO response field names and values (PD, PR, CR, SD, NR, response, non-response) to the pipeline's standard labels (responder, non_responder) so the DE step can form valid contrasts.

**Independent Test**: A cohort-specific response mapping config correctly maps GSE91061's `PD` to `non_responder` and `PR/CR` to `responder`, and GSE67501's `no_response` to `non_responder`.

### User Story 3 - Build expression sample alias mappings for newly curated cohorts (Priority: P1)

As the analysis owner, I need the expression column alias mapping to be extended to all newly curated cohorts so the DE step can match manifest sample IDs to expression matrix column names.

**Independent Test**: After alias extraction, gse91061 (109 samples) has 109 expression_sample_alias values that match the columns in its supplementary FPKM file.

### User Story 4 - Re-curate manifest and re-run evidence (Priority: P2)

As the analysis owner, I need the sample manifest rebuilt with the newly extracted response labels and aliases, then the pipeline re-run to verify increased meta-analysis power and signature gene count.

**Independent Test**: The re-run produces >=5 meta-eligible PRE_RESPONSE cohorts and a signature with more genes than the current 1-gene result.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST parse all `characteristics_ch1` key-value pairs from SOFT files into a flat, structured TSV.
- **FR-002**: The system MUST handle heterogeneous characteristic key names across studies (e.g., `response`, `recist`, `tumor.response`, `best response on immunotherapy (recist)`).
- **FR-003**: The system MUST produce a configurable response label mapping from GEO-native values to pipeline-standard values (responder/non_responder).
- **FR-004**: The response mapping MUST be cohort-specific to handle different response schemas per study.
- **FR-005**: The system MUST extract timing/visit information where available in characteristics.
- **FR-006**: The system MUST build `expression_sample_alias` mappings for all cohorts where expression columns differ from GSM IDs.
- **FR-007**: The system MUST update the sample manifest with extracted response labels, timing, and aliases.
- **FR-008**: The system MUST NOT override manually curated labels (existing include_flag=true rows must be preserved).
- **FR-009**: The system MUST produce a reconciliation report showing per-cohort extraction coverage and DE eligibility.
- **FR-010**: The system MUST handle RECIST criteria mapping: CR/PR → responder, SD/PD → non_responder (configurable).
- **FR-011**: The system MUST handle pre/on-treatment timing extraction for longitudinal cohorts (e.g., GSE91061).
- **FR-012**: The system MUST integrate with `getGeoMetadata` (R) as an optional supplementary extraction source for cohorts where local SOFT parsing is insufficient.

### Key Entities

- **Characteristics Extraction Table**: Flat TSV with all SOFT characteristics as columns, one row per sample.
- **Response Label Mapping Config**: Per-cohort mapping from GEO field names/values to pipeline-standard labels.
- **Expression Alias Table**: GSM ID to expression column name mapping per cohort.
- **Curation Reconciliation Report**: Per-cohort summary of extraction coverage, DE eligibility, and remaining gaps.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Characteristics extraction produces a structured TSV for all 30 cohorts.
- **SC-002**: Response labels are extracted for >=7 currently-uncurated cohorts (>=350 newly labeled samples).
- **SC-003**: Expression alias mappings are built for all cohorts with non-GSM column names.
- **SC-004**: Updated manifest has >=8 DE-eligible PRE_RESPONSE cohorts (up from 3).
- **SC-005**: Pipeline re-run produces a signature with >=2 genes (up from 1).
- **SC-006**: Existing curated cohorts (gse126044, gse78220, gse218989, gse93157, gse115821) are not regressed.
- **SC-007**: All 28 existing tests pass after code changes.
