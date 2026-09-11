# Tasks: Spec 016 — Stage 07 Meta-Analysis

## Phase 0: Spec Kit Setup
- [x] T001 spec.md + full spec kit files (`plan/research/benchmarks/quickstart`).

## Phase 1: Audit
- [x] Confirm `_compute_meta_stats` correctness and preserve existing validated estimator path.
- [x] Inventory subgroup emission + k=1 handling.

## Phase 2: Contract lock
- [x] Freeze common-scale input guard contract with spec 015 and subgroup policy.

## Phase 3: Harden (FR-001..FR-005)
- [x] Implement input guard; cancer-group meta-regression; k=1 flagging and side-table emission.
- [x] Add Knapp-Hartung option path for small-k inference sensitivity.

## Phase 4: Test
- [x] Unit + integration contract coverage in `tests/unit/test_spec007_meta_hardening.py`.

## Phase 5: Reproducibility
- [x] Reproducibility artifacts and run-manifest logging retained for Stage-07 outputs.

## Phase 6: Docs
- [x] `docs/runbooks/stage_07_meta.md` documents guards, k=1 handling, and optional meta-regression.

## Phase 7: Sign-off
- [x] CHANGELOG + status updates completed.
- [ ] Memory update (deferred: memory edits only on explicit user request).
