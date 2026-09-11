# Tasks: Spec 010 — Stage 01 Intake (Assay & Response Contract)

FR traceability in the final table. Phases map to plan.md milestones.

## Round-3 Status Snapshot
- Implemented and test-covered: Stage-01 detector contract, override conflict handling, response/timing provenance, curation report, unreadable/methylation typed exclusions, gse126044 dedup and gse165278 drop gates.
- Real-cohort SC-002/SC-003 verification executed (T024): response-definition linkage passes, but assay-confidence and non-default SD-handling thresholds remain unmet in current committed-state inputs.
- SC-004 full rerun executed at `results/full_pipeline_20260530_113322`; migration note recorded in `docs/reviews/spec010_sc004_fullrun_2026-05-30.md`.
- Memory-update task remains deferred unless explicitly requested by user policy.

## Phase 0: Spec Kit Setup (M1)
- [x] T001 Write spec.md, research.md, plan.md, benchmarks.md, tasks.md, quickstart.md (this commit).

## Phase 1: Tests-First (M2) — FR-010 driver
- [x] T002 Build a multi-cohort fixture: raw-count, TPM, rlog/VST, microarray-intensity matrices + a curated-label cohort, a sampleid-only cohort, an SD-as-benefit cohort, an empty-metadata cohort.
- [x] T003 Failing unit test: assay detection assigns correct type for all 6 types + `raw_counts_suspect`.
- [x] T004 Failing unit test: `assay_type_override` precedence + conflict logging (FR-002).
- [x] T005 Failing unit test: response-provenance precedence curated>text>sampleid; `needs_manual_confirmation` set for sampleid path (FR-006).
- [x] T006 Failing unit test: `sd_handling` capture for the SD-as-benefit cohort (FR-005).
- [x] T007 Failing unit test: timing provenance enum (FR-007).
- [x] T008 Failing integration test: `intake` end-to-end on fixture → manifest + 3 records vs committed golden.

## Phase 2: Assay detector (M3) — FR-001, FR-002, FR-003
- [x] T009 Implement `assay_detect.py` evidence observers (integer_frac, has_negative, colsum stats, range) on top of `common/expression.py`.
- [x] T010 Implement deterministic classification rules (research.md §2) + confidence.
- [x] T011 `intake detect-assay-type` CLI; emit `assay_detection.tsv`; honour override.
- [x] T012 Add `assay_type`, `assay_type_override` to the sample manifest writer.

## Phase 3: Response & timing records (M4) — FR-005, FR-006, FR-007
- [x] T013 Implement `response_record.py`: precedence, SD-handling, `response_definition_id`, counts.
- [x] T014 Demote `_infer_response_label` to flagged fallback; route through provenance.
- [x] T015 Implement `timing.py` provenance; add `timing_provenance` to manifest.
- [x] T016 Link every `response_label` to `response_definition_id`.

## Phase 4: Curation report (M5) — FR-008
- [x] T017 Implement `curation_report.py`; emit `intake_curation_report.{md,tsv}`.

## Phase 5: Module extraction + shrink (M6) — FR-009
- [x] T018 Move helpers into `_01_dataset_intake`; CLI dispatches to module.
- [x] T019 Verify `cli.py` Stage 01 surface drops ≥400 lines (`wc -l` before/after in benchmarks.md).
- [x] T020 Confirm all existing intake tests still pass (no regression).

## Phase 6: Reproducibility + runbook (M7) — FR-011, FR-012
- [x] T021 Emit reproducibility bundle (`commands.sh`, `environment.yml`, `checksums.sha256`).
- [x] T022 Write `docs/runbooks/stage_01_intake.md`.

## Phase 7: Sign-off (M8) — SC-001..SC-007
- [x] T023 Run full pipeline with `assay_type`-driven routing stubbed/contract-only; produce SC-004 migration note (which cohorts' model class *would* change). (Run: `results/full_pipeline_20260530_113322`; migration artifacts: Stage-06 `de_model_migration.md` + `docs/reviews/spec010_sc004_fullrun_2026-05-30.md`.)
- [x] T024 Verify SC-002 (≥95% assay confidence) and SC-003 (response_definition_id coverage) on the real cohort set. (2026-05-30 verification note: SC-003 linkage met, SC-002 and SC-003 `sd_handling` threshold currently not met.)
- [x] T025 CHANGELOG + status bookkeeping completed for current no-results-mutation cycle; memory update deferred by policy (only on explicit request).

## Task → FR traceability

| FR | Tasks |
|---|---|
| FR-001 | T003, T009, T010 |
| FR-002 | T004, T011 |
| FR-003 | T012, T018 |
| FR-004 | (contract frozen here; consumed in spec 015/018) T012 |
| FR-005 | T006, T013 |
| FR-006 | T005, T014 |
| FR-007 | T007, T015 |
| FR-008 | T017 |
| FR-009 | T018, T019, T020 |
| FR-010 | T002–T008 |
| FR-011 | T021 |
| FR-012 | T022 |
