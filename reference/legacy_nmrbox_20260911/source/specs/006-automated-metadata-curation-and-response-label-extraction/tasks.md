# Tasks: Automated Metadata Curation and Response Label Extraction (v1)

**Input**: Design documents from `/specs/006-automated-metadata-curation-and-response-label-extraction/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `quickstart.md`, `contracts/io-contracts.md`

## Phase 0: Spec Kit Initialization

- [x] T001 Create `specs/006-automated-metadata-curation-and-response-label-extraction/` with all 6 kit files (spec.md, plan.md, tasks.md, research.md, quickstart.md, contracts/io-contracts.md).

## Phase 1: Comprehensive Characteristics Extraction

- [x] T002 Write `intake extract-characteristics` CLI command to parse all SOFT `characteristics_ch1` fields into structured long-format and wide-format TSVs.
- [x] T003 Run extraction on all 30 cohorts. Verify >=12 cohorts have response-related fields.
- [x] T004 Produce characteristic key inventory with per-cohort frequency and relevance classification.

## Phase 2: Response Label Mapping

- [x] T005 Create `configs/response_label_mapping.tsv` with per-cohort response value → pipeline label mapping. Include DEFAULT RECIST mapping.
- [x] T006 Create `configs/timing_label_mapping.tsv` with per-cohort timing value → pipeline label mapping.
- [x] T007 Write `intake apply-characteristics-mapping` CLI command that applies response and timing mappings to extracted characteristics.

## Phase 3: Expression Alias Extraction

- [x] T008 Write `intake extract-expression-aliases` CLI command to build GSM → expression column name mappings from SOFT titles.
- [x] T009 Run alias extraction for all 30 cohorts. Verify >=95% coverage for cohorts with non-GSM columns.
- [ ] T010 Handle supplementary metadata files (e.g., GSE207422_metadata.xlsx) for cohorts where SOFT titles don't match expression columns.

## Phase 4: Manifest Rebuild

- [x] T011 Write `intake merge-extracted-metadata` CLI command to merge extracted response labels, timing, and aliases into the manifest.
- [x] T012 Apply DE eligibility rules and produce per-cohort eligibility report.
- [x] T013 Update `geo_tables_summary.tsv` expression file paths for cohorts with empty series matrices.

## Phase 5: Verification Evidence Run

- [x] T014 Run `pytest tests/` — verify all 28 tests pass.
- [x] T015 Re-run the full pipeline with the updated manifest.
- [ ] T016 Verify success criteria: >=8 DE-eligible cohorts, >=5 meta-eligible, signature >=2 genes.
- [x] T017 Produce `results/spec_006/curation_reconciliation_report.md`.

## Phase 6: Optional getGeoMetadata Integration

- [ ] T018 If >=5 cohorts still lack response labels, install getGeoMetadata (R) and run supplementary extraction.
- [ ] T019 Merge getGeoMetadata output and re-run evidence.

## Completion Definition

Spec-006 is considered implementation-complete when:

- All SOFT `characteristics_ch1` fields are extracted into structured tables,
- Response label mappings are defined and applied for all cohorts with response data,
- Expression alias mappings cover all cohorts with non-GSM expression columns,
- The sample manifest is rebuilt with >=8 DE-eligible PRE_RESPONSE cohorts,
- A pipeline re-run produces a signature with >=2 genes,
- And a curation reconciliation report documents coverage, decisions, and remaining gaps.
