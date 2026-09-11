# Tasks: Spec 026 — Analysis Design Contrast Registry

## Phase 0: Spec Kit (M1)
- [x] T001 Write spec.md, research.md, plan.md, benchmarks.md, quickstart.md, contracts/io-contracts.md.

## Phase 1: Tests-first (M2)
- [x] T002 Fixture with PRE/ON/POST response samples, paired DELTA samples, drug/cancer strata, unknown labels, and hard-excluded assay samples.
- [x] T003 Unit test: normalized analysis sample manifest preserves raw and collapsed labels.
- [x] T004 Unit test: registry creates feasible and blocked co-equal analysis families with reasons.
- [x] T005 Unit test: DELTA membership uses paired samples only.
- [x] T006 Integration test: `design build` writes all four required outputs.
- [x] T007 Router dry-run test: analysis registry is consumed and planned `analysis_id`s are reported.

## Phase 2: Design module (M3)
- [x] T008 Implement sample normalization.
- [x] T009 Implement response, drug, cancer, pan-ICB, and paired DELTA candidate generation.
- [x] T010 Implement analysis membership materialization.
- [x] T011 Implement Markdown audit report.
- [x] T011a Add dedicated ICI-containing combination response family.
- [x] T011b Add Stage-06-aligned assay/readiness gating for design feasibility.
- [x] T011c Add content-based assay detection fallback for readable `bulk_rna_seq` matrices.

## Phase 3: CLI wiring (M4, M5)
- [x] T012 Add `design build` CLI.
- [x] T013 Add router dry-run support for `--analysis-registry`.
- [x] T014 Add optional `analysis_id`/membership support for Stage 06 DE.
- [x] T015 Add optional `analysis_id` output support for Stage 07 meta.

## Phase 4: Sign-off (M6)
- [x] T016 Run targeted tests for Spec 026 and legacy PRE/DELTA compatibility.

## Task to FR Traceability

| FR | Tasks |
|---|---|
| FR-001 | T003, T008 |
| FR-002 | T004, T009 |
| FR-003 | T004, T009 |
| FR-004 | T005, T010 |
| FR-005 | T003, T009, T010 |
| FR-006 | T009, T010 |
| FR-007 | T004, T011 |
| FR-008 | T006, T012 |
| FR-009 | T014, T015, T016 |
| FR-010 | T007, T013 |
| FR-011 | T004, T009, T011a |
| FR-012 | T004, T011b, T012 |
| FR-013 | T003, T011c, T014 |
