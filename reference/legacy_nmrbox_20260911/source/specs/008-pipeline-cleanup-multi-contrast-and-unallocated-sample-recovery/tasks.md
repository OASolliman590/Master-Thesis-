# Tasks: Spec 008 Pipeline Cleanup and Multi-Contrast Recovery

## Phase 0: Spec Kit Setup

- [x] T001 Create Spec 008 kit directory.
- [x] T002 Create all six Spec Kit files.
- [x] T003 Install/read ClawBio `rnaseq-de`, `bio-orchestrator`, and `diff-visualizer` references.

## Phase 1: Allocation Audit

- [x] T004 Add production allocation module.
- [x] T005 Add `intake build-sample-allocation`.
- [x] T006 Emit `sample_allocation_matrix.tsv`.
- [x] T007 Emit `cohort_allocation_summary.tsv`.
- [x] T008 Emit `unallocated_samples.tsv`.
- [x] T009 Emit ClawBio-style reproducibility bundle.
- [x] T010 Add curation templates for top unallocated cohorts.

## Phase 2: Multi-Contrast Routing

- [x] T011 Add `router run --contrasts`.
- [x] T012 Preserve legacy `--track` behavior.
- [x] T013 Add `multi_contrast` route mode.
- [x] T014 Add contrast-first report summary.

## Phase 3: Stage 06 DE

- [x] T015 Add POST_RESPONSE sample selection.
- [x] T016 Add ON_RESPONSE sample selection.
- [x] T017 Let TREATMENT_DELTA inspect paired rows even when post/on rows are excluded from PRE.
- [x] T018 Extract contrast resolver out of monolithic CLI.
- [x] T019 Add full DELTA pair audit report.

## Phase 4: Tests And Verification

- [x] T020 Add unit tests for sample allocation.
- [x] T021 Add unit tests for POST_RESPONSE and ON_RESPONSE DE.
- [x] T022 Run `python -m pytest tests/ -q`.
- [x] T023 Run allocation audit on full manifest.
- [x] T024 Run multi-contrast router dry run.

## Phase 5: Documentation Cleanup

- [x] T025 Update `README.md`.
- [x] T026 Update `docs/USAGE.md`.
- [x] T027 Add unallocated sample interpretation note.

## Phase 6: Execution Report

- [x] T028 Write `results/spec_008/spec_008_execution_report.md`.
