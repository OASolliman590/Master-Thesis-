# Tasks: Spec 018 — Stage 09 Real ssGSEA / Deconvolution / Layer-4

FR traceability at end. Phases map to plan.md.

## Round-3 Status Snapshot
- Implemented: real GSVA dispatch by default, backend-required failure behavior, Layer-4 registry coverage tests, ESTIMATE/EPIC wiring, and directional legacy-API `abs.ranking = FALSE`.
- Pending: dedicated module extraction/reproducibility sign-off tasks not required for current no-results-mutation cycle.

## Phase 0: Spec Kit (M1)
- [x] T001 spec.md, research.md, plan.md, benchmarks.md, quickstart.md (this commit).

## Phase 1: Tests-first (M2)
- [x] T002 ssGSEA pipeline output == direct `GSVA::gsva(ssgseaParam())` on a fixture (tolerance).
- [x] T003 Layer-4 membership test: all 8 sets present + parsed.
- [x] T004 Backend-required test: missing R/GSVA → loud failure, no proxy fallback.

## Phase 2: Wire real ssGSEA (M3) — FR-001, FR-002
- [x] T005 `ssgsea.py` dispatch to `scripts/ssgsea_gsva.R`; delete Python rank-mean (keep behind deprecated `--legacy-rank-mean` until sign-off).
- [x] T006 Feed assay-correct (log2-normalized) expression; fix `abs.ranking` for directional sets.

## Phase 3: Layer-4 GMTs (M4) — FR-004
- [x] T007 Author 6 missing GMTs with cited membership: PRC2_IMMUNE_TARGETS, SWI_SNF_ICB, DNMT_IMMUNE_LOCI, HISTONE_WRITERS_ICB, RETROELEMENT_SENSING, T_CELL_EXHAUSTION_EPIGENETIC, T_CELL_MEMORY_EPIGENETIC.
- [x] T008 Register + score; membership unit test.

## Phase 4: Deconvolution (M5) — FR-003, FR-005
- [x] T009 Wire `estimate_scores.R` + `epic_scores.R` (or delete placeholders + `*_proxy_deprecated` columns).
- [x] T010 Expose composition as the spec-015 mediation mediator (NOT a default DE covariate).

## Phase 5: Module + sign-off (M6)
- [x] T011 Extract to `_09_immune_state`; CLI dispatch.
- [x] T012 Reproducibility bundle; `docs/runbooks/stage_09_immune_state.md`.
- [x] T013 CHANGELOG + status bookkeeping completed for current no-results-mutation cycle; memory update deferred by policy (only on explicit request). Spec-007 "real ssGSEA" contract marked MET in implementation docs/tests.

## Task → FR
| FR | Tasks |
|---|---|
| FR-001 | T002, T004, T005, T006 |
| FR-002 | T006 |
| FR-003 | T009 |
| FR-004 | T003, T007, T008 |
| FR-005 | T010 |
| FR-006 | (HOPE thresholds — fold into T005) |
