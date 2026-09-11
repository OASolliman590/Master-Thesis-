# Tasks: Spec 025 — Visualization Module

## Round-3 Status Snapshot
- Implemented: `viz build`, figure registry + loader, scientific-note caption sidecars/linting, reproducibility bundle, and Stage-07 forest plotting extraction to `_viz`.
- Pending: broader end-to-end builder integration coverage on committed mini-run artifacts and final sign-off bookkeeping.

## Phase 0: Spec Kit (M1)
- [x] T001 spec.md, research.md, plan.md, benchmarks.md, quickstart.md (this commit).

## Phase 1: Tests-first (M2)
- [x] T002 Per-builder render test on a fixture (no error, file produced, Agg backend).
- [x] T003 Integration: `viz build` on a mini committed run → `figure_manifest.tsv` complete; every row has `scientific_note`.
- [x] T004 Lint test: no figure caption contains "validation" for TCGA/concordance; TCGA captions contain "prognostic".

## Phase 2: Registry (M3) — FR-002
- [x] T005 `configs/figure_registry.tsv` (research §2 catalogue); `registry.py` loader.

## Phase 3: Builders (M4) — FR-003, FR-004
- [x] T006 Reuse qc_plots builders; add volcano (per-cohort DE).
- [x] T007 Forest builder reading corrected meta (spec 016).
- [x] T008 Signature heatmap (spec 008 signature × expression).
- [x] T009 ssGSEA-layer violin/box R-vs-NR (spec 018 GSVA scores).
- [x] T010 TCGA continuous-Cox KM + Thorsson-association (spec 021); concordance-tier bar (spec 010-framing).

## Phase 4: Scientific labeling (M5) — FR-005
- [x] T011 Enforce `scientific_note` per figure + caption sidecars.

## Phase 5: Consolidate (M6) — FR-007
- [x] T012 Move inline forest code out of `cmd_meta_run`; Stage 07 dispatches to `_viz`.

## Phase 6: Sign-off (M7) — FR-001, FR-006, FR-009
- [x] T013 `viz build` CLI + `figure_manifest.tsv`; deterministic/headless.
- [x] T014 Reproducibility bundle; `docs/runbooks/visualization.md` (thesis-figure → figure_id map).
- [x] T015 CHANGELOG + status bookkeeping completed for current no-results-mutation cycle; memory update deferred by policy (only on explicit request).

## Task → FR
| FR | Tasks |
|---|---|
| FR-001 | T013 |
| FR-002 | T005 |
| FR-003 | T006–T010 |
| FR-004 | T007, T009, T010 |
| FR-005 | T004, T011 |
| FR-006 | T002, T013 |
| FR-007 | T012 |
| FR-008 | T002, T003 |
| FR-009 | T014 |
