# Tasks: Spec 017 — Stage 08 Signature Derivation

## Phase 0: Spec Kit Setup
- [x] T001 Promote spec.md from stub to active next-cycle contract.
- [x] T002 Add plan.md, research.md, benchmarks.md, and quickstart.md.

## Phase 1: Corrected-output audit
- [x] T003 Confirm current corrected Stage 06/07 run root. See `docs/reviews/stage08_corrected_run_root_audit_2026-06-05.md`.
- [x] T004 Inventory `analysis_id` coverage, blocked analyses, and contributing cohorts. See `docs/reviews/stage08_corrected_run_root_audit_2026-06-05.md`.
- [x] T005 Verify meta output uses a common effect scale and records effect direction. Guard implemented; current corrected-root meta blocks with `missing_common_scale_provenance` until Stage 06/07 emit explicit scale fields.
- [x] T006 Verify Stage 09 immune scoring outputs are regenerated or blocked for the same run root before downstream reporting. Corrected-root Stage 09 score/effects outputs are under `results/analysis_id_runs_t7_20260530/immune_state`; deconvolution remains NA/unavailable without local ESTIMATE/EPIC packages.

## Phase 2: Contract lock
- [x] T007 Define `signature_thresholds.yaml` with tier-specific FDR, effect, cohort-count, and heterogeneity rules.
- [x] T008 Define `signature_registry.tsv` schema and required provenance columns.
- [x] T009 Define module-assignment registry/rules for antigen presentation, IFN, chemokine, cytotoxic/T-cell-inflamed, checkpoint/adaptive resistance, and epigenetic-repression candidates.
- [x] T010 Define nested/LOCO derivation manifest consumed by Stage 10.

## Phase 3: Harden implementation
- [x] T011 Extract signature derivation to `_08_signature` or equivalent current module pattern.
- [x] T012 Block derivation when corrected common-scale meta effects are unavailable.
- [x] T013 Implement tiered signature selection from configuration, not hardcoded thresholds.
- [x] T014 Emit core, tiered, audit, threshold, module, and LOCO manifest outputs.

## Phase 4: Tests
- [x] T015 Add fixture test for mixed-scale meta effects blocking.
- [x] T016 Add fixture test for deterministic tier assignment.
- [x] T017 Add provenance test requiring `analysis_id`, cohort count, timing label, and analysis family.
- [x] T018 Add circularity guardrail test: same-sample concordance cannot be labelled external validation.

## Phase 5: Reproducibility and docs
- [x] T019 Add runbook at `docs/runbooks/stage_08_signature_derivation.md`.
- [x] T020 Add reproducibility manifest/checksum output.
- [x] T021 Update CHANGELOG/status docs after implementation.

## Phase 6: Sign-off
- [x] T022 Run focused Stage 08 tests.
- [x] T023 Run full pytest suite or document why it was not run. Focused tests passed; full suite not run in this slice because the workspace has substantial unrelated dirty state and this change was scoped to Stage 07/08 contracts.
- [ ] T024 Build downstream report from the selected run root. Stage 07/08 reviewed root now exists at `results/analysis_id_runs_t7_20260607_stage07_scale_provenance`; Stage 10 validation framing should run before final report build.

## Task to FR
| FR | Tasks |
|---|---|
| FR-001 | T003, T005, T012, T015 |
| FR-002 | T007, T013, T016 |
| FR-003 | T010, T014, T018 |
| FR-004 | T008, T014, T017 |
| FR-005 | T010, T018 |
| FR-006 | T009, T014, T016 |
| FR-007 | T011, T019, T020 |
