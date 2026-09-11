# Tasks: Cohort Bulk Ingestion and Manifest Reconciliation (Spec-005)

**Input**: Design documents from `/specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `quickstart.md`, `contracts/io-contracts.md`

## Status Snapshot (2026-04-12)

Spec-005 initialized from the empty-signature risk analysis.

Current intent:

- close manifest/data-ingestion gap between implemented pipeline and full 30-cohort GEO downloads on T7
- preserve legacy cohort-ID continuity while fixing expression path reconciliation
- separate automatable ingestion work from manual publication curation workload

## Phase 0: Spec Kit Initialization

- [x] T001 Create `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/spec.md`.
- [x] T002 Create `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/plan.md`.
- [x] T003 Create `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/research.md`.
- [x] T004 Create `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/quickstart.md`.
- [x] T005 Create `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/contracts/io-contracts.md`.
- [x] T006 Create `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/tasks.md`.

## Phase 1: Path Resolution Layer [Workstream A]

- [ ] T007 Build `configs/cohort_id_reconciliation_ledger.tsv` from T7 reconciled roster + existing manifests.
- [ ] T008 Add `downloads_folder` support in expression-path resolution with backward-compatible fallback.
- [ ] T009 Add/extend unit tests for path resolution with and without `downloads_folder`.

## Phase 2: Discovery Manifest Expansion [Workstream B]

- [ ] T010 Expand `configs/discovery_geo_focus.tsv` from 13 to 30 rows (preserve existing 13 rows verbatim).
- [ ] T011 Expand `configs/geo_input_routing_manifest.tsv` from 13 to 30 rows using folder-level route classification.

## Phase 3: Supplementary Metadata Extraction [Workstream C]

- [ ] T012 Set up `extract-geo-metadata` tooling and validate on one GEO cohort.
- [ ] T013 Build supplementary metadata outputs across the 30-accession GEO set.
- [ ] T014 Merge supplementary metadata with SOFT-derived metadata into `results/spec_005/supplementary_metadata_merged.tsv`.

## Phase 4: Full Intake Rebuild [Workstream D]

- [ ] T015 Run `intake build-geo-tables` on all 30 cohorts and rebuild `results/geo_tables/*`.
- [ ] T016 Ensure rebuilt `geo_tables_summary.tsv` includes `downloads_folder` and has 30 rows.
- [ ] T017 Run `intake build-geo-sample-manifest` to produce `configs/sample_manifest_geo_all.tsv` and `configs/sample_manifest_geo_ready.tsv`.
- [ ] T018 Run `intake gene-audit` preflight across full GEO set.
- [ ] T019 Run `method inspect` and `method curation-sheet` for full cohort coverage.

## Phase 5: Publication-Level Curation [Workstream E]

- [ ] T020 Merge supplementary metadata pre-fills into the curation sheet.
- [ ] T021 Complete publication-level curation for all 30 cohorts (response, timing, pair IDs, include/hold/exclude).
- [ ] T022 Apply curation to rebuild `configs/sample_manifest_curated.tsv` and `configs/projection_manifest.tsv`.
- [ ] T023 Verify rebuilt curated manifest has zero sync stubs and 400+ real sample rows.

## Phase 6: Verification Evidence Run [Workstream F]

- [ ] T024 Execute full pre-flight checklist (mounts, counts, path resolution, tests).
- [ ] T025 Execute full pipeline verification run using rebuilt manifests.
- [ ] T026 Verify success criteria thresholds and signature non-emptiness.
- [ ] T027 Write `results/spec_005/ingestion_reconciliation_report.md`.

## Completion Definition

Spec-005 is considered complete when:

- all 30 GEO cohorts are represented in rebuilt discovery/routing/intake outputs,
- expression files resolve correctly with legacy IDs via `downloads_folder`,
- curated sample manifest has zero sync stubs and thesis-usable sample coverage,
- and verification run readiness/signature outputs clear the locked success thresholds.
