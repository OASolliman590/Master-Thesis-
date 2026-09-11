# Tasks: Spec 015 — Stage 06 Within-Cohort DE Method

FR traceability at the end. Phases map to plan.md milestones. Depends on spec 010 Active.

## Round-3 Status Snapshot
- Implemented: assay-type-driven harmonization path, limma-trend backend (`scripts/rna_limma.R`), explicit Welch fallback switch, moderated DELTA handling, and primary unadjusted vs secondary adjusted signature framing.
- Pending: deeper model-routing refactor/module extraction items and migration-note/full-run sign-off tasks tied to committed-output regeneration.

## Phase 0: Spec Kit (M1)
- [x] T001 spec.md, research.md, plan.md, benchmarks.md, quickstart.md (this commit).

## Phase 1: Tests-first (M2)
- [x] T002 Simulated dataset with known per-gene effect + noise; assert limma/DESeq2 SE recovers truth, Welch SE biased at small n.
- [x] T003 Assay-routing unit tests: each `assay_type` → correct harmonization + model; methylation/unreadable hard-excluded.
- [x] T004 Golden integration test: DE on a multi-assay fixture → uniform `{log2fc,se,model_class}` schema.

## Phase 2: Harmonization (M3) — FR-001
- [x] T005 `harmonize.py`: assay_type→transform (VST/rlog/log2(x+1)/as-is); delete `is_log` heuristic from cli.py.

## Phase 3: Uniform model (M4) — FR-002, FR-003
- [x] T006 New `scripts/rna_limma.R` (limma + eBayes trend) emitting log2fc + se.
- [x] T007 `de_models.py`: dispatch counts→DESeq2/edgeR/voom, normalized/log→limma, microarray→classic limma; uniform output.
- [x] T008 Confirm DESeq2 path output byte-identical to baseline for verified-count cohorts.

## Phase 4: Replace Welch (M5) — FR-003
- [x] T009 Remove Welch default; retain only as `--allow-welch-fallback` flagged path.

## Phase 5: DELTA + mediation (M6) — FR-004, FR-007
- [x] T010 Paired/duplicateCorrelation limma for TREATMENT_DELTA.
- [x] T011 Primary DE composition-UNADJUSTED; optional `--composition-adjusted` secondary; `mediation.py` hook (consumes spec-018 deconvolution).

## Phase 6: Migration + R audit (M7) — FR-005, FR-006
- [x] T012 Emit `de_model_migration.md` (cohorts whose model/representation changed + top-gene effect).
- [x] T013 Document R-script designs + se semantics in research.md.

## Phase 7: Module + sign-off (M8) — FR-009-style
- [x] T014 Extract to `_06_within_cohort_de`; CLI dispatches; cli.py shrink check.
- [x] T015 Reproducibility bundle; `docs/runbooks/stage_06_de.md`.
- [x] T016 CHANGELOG + status bookkeeping completed for current no-results-mutation cycle; memory update deferred by policy (only on explicit request).

## Task → FR
| FR | Tasks |
|---|---|
| FR-001 | T003, T005 |
| FR-002 | T002, T006, T007, T008 |
| FR-003 | T006, T007, T009 |
| FR-004 | T010 |
| FR-005 | T013 |
| FR-006 | T012 |
| FR-007 | T011 |
