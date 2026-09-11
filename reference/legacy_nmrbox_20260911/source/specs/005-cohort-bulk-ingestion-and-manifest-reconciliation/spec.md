# Feature Specification: Cohort Bulk Ingestion and Manifest Reconciliation (Spec-005)

**Feature Branch**: `005-cohort-bulk-ingestion-and-manifest-reconciliation`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: Blocker analysis for empty signature risk after evidence run underpowered by cohort/sample manifest coverage.

## Context Lock

### Current Baseline

- pipeline architecture is implemented and execution-safe across Specs 002-004
- current scientific bottleneck is cohort/sample coverage, not core stage wiring
- T7 already holds a wider GEO corpus (`30` cohorts) that has not been fully ingested into the active intake/manifest cycle

### Locked Decisions

- keep legacy-style cohort IDs for continuity in current manifests and downstream references
- introduce explicit `downloads_folder` mapping for expression resolution against T7 folder names
- perform full publication-level curation for all `30` GEO cohorts
- use `extract-geo-metadata` as a supplementary metadata source (SOFT parsing remains primary baseline)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconcile legacy cohort IDs to T7 folder names (Priority: P1)

As the analysis owner, I need a deterministic cohort-ID reconciliation ledger so path resolution and manifest joins stay stable when cohort IDs and T7 folder names differ.

**Independent Test**: reconciliation ledger includes all 30 GEO cohorts and maps each canonical cohort ID to one T7 folder.

### User Story 2 - Expand intake manifests to all downloaded GEO cohorts (Priority: P1)

As the analysis owner, I need discovery and routing manifests expanded from 13 to 30 rows so intake stages can run on the full downloaded GEO coverage.

**Independent Test**: `discovery_geo_focus.tsv` and `geo_input_routing_manifest.tsv` each contain 30 cohort rows and are internally joinable by `cohort_id`.

### User Story 3 - Rebuild sample manifests without sync stubs (Priority: P1)

As the analysis owner, I need real sample-level manifest rows for all cohorts instead of placeholder sync stubs so contrast eligibility and DE routing are meaningful.

**Independent Test**: rebuilt curated sample manifest has zero `_SYNC_STUB` rows.

### User Story 4 - Verification run produces non-empty signature (Priority: P2)

As the analysis owner, I need a full evidence rerun after bulk ingestion/curation to confirm primary `PRE_RESPONSE` is no longer blocked by intake sparsity.

**Independent Test**: verification run exits `0` and `pre_response_signature_v1.tsv` is non-empty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create `configs/cohort_id_reconciliation_ledger.tsv` with explicit cohort/folder reconciliation state.
- **FR-002**: The ingestion layer MUST support `downloads_folder` mapping for expression resolution while preserving backward compatibility.
- **FR-003**: `results/geo_tables/geo_tables_summary.tsv` MUST include `downloads_folder`.
- **FR-004**: `configs/discovery_geo_focus.tsv` MUST expand to 30 GEO cohorts while preserving existing 13 rows unchanged.
- **FR-005**: `configs/geo_input_routing_manifest.tsv` MUST expand to 30 rows with data-route classification based on actual downloaded file structures.
- **FR-006**: Supplementary metadata extraction outputs MUST be merged with SOFT-derived metadata into `results/spec_005/supplementary_metadata_merged.tsv`.
- **FR-007**: Intake rebuild stages (`build-geo-tables`, `build-geo-sample-manifest`, `gene-audit`, `method inspect`, `method curation-sheet`) MUST run on the full GEO set.
- **FR-008**: Manual curation application MUST rebuild `configs/sample_manifest_curated.tsv` with zero sync stubs.
- **FR-009**: Verification evidence run MUST emit a reconciliation report at `results/spec_005/ingestion_reconciliation_report.md`.

### Key Entities *(include if feature involves data)*

- **Cohort ID Reconciliation Record**: canonical cohort ID, accession, T7 folder mapping, legacy and timer lineage.
- **Expanded Discovery Manifest Row**: cohort-level scientific metadata for one GEO cohort in the 30-cohort ingestion set.
- **Expanded Routing Manifest Row**: per-cohort input-route recommendation and file inventory-derived route evidence.
- **Supplementary Metadata Merge Row**: sample-level SOFT + MINiML extraction alignment with disagreement flags.
- **Ingestion Reconciliation Report**: run-level narrative and tabular summary of ingestion coverage/readiness outcomes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `results/geo_tables/geo_tables_summary.tsv` has exactly `30` cohort rows.
- **SC-002**: At least `28` cohorts have non-empty `primary_expression_file`.
- **SC-003**: `configs/sample_manifest_curated.tsv` has at least `400` real sample rows.
- **SC-004**: `configs/sample_manifest_curated.tsv` has `0` `_SYNC_STUB` sample IDs.
- **SC-005**: `PRE_RESPONSE` eligible cohorts are at least `8`.
- **SC-006**: `TREATMENT_DELTA` eligible cohorts are at least `3`.
- **SC-007**: Meta-eligible `PRE_RESPONSE` cohorts are at least `5`.
- **SC-008**: `pre_response_signature_v1.tsv` contains at least `1` gene.
- **SC-009**: Verification evidence run exits with code `0`.
