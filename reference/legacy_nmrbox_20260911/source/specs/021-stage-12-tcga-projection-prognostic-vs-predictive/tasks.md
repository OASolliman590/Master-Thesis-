# Tasks: Spec 021 — Stage 12 TCGA Projection

## Phase 0: Spec Kit Setup
- [x] T001 spec.md + full spec kit files (`plan/research/benchmarks/quickstart`).

## Phase 1: Audit
- [x] Audit `cmd_tcga_project` scoring + `scripts/tcga_survival.R`.
- [x] Define Thorsson-subtype manifest contract for optional layer-4 association path.

## Phase 2: Contract lock
- [x] Freeze z-scored score definition, prognostic framing language, and layer-4 output schema.

## Phase 3: Harden (FR-001..FR-005)
- [x] z-score projection; continuous Cox; layer-4 vs Thorsson subtype association.
- [x] Add optional age/stage covariates for continuous Cox when present.

## Phase 4: Test
- [x] Unit contracts in `tests/unit/test_spec018_backend_and_spec021_projection_contracts.py`.

## Phase 5: Reproducibility
- [x] Reproducibility bundle emitted for TCGA projection outputs.

## Phase 6: Docs
- [x] `docs/runbooks/stage_12_tcga_projection.md` includes prognostic-vs-predictive framing.

## Phase 7: Sign-off
- [x] CHANGELOG + status updates completed.
- [ ] Memory update (deferred: memory edits only on explicit user request).
