# Tasks: Spec 019 — Stage 10 Validation Framing

## Phase 0: Spec Kit Setup
- [x] T001 spec.md + full spec kit files (`plan/research/benchmarks/quickstart`).

## Phase 1: Audit
- [x] Document same-sample indirect-vs-mega design and robustness framing.

## Phase 2: Contract lock
- [x] Lock held-out evaluation contract (`auc`, `effect_concordance`) and readiness semantics.

## Phase 3: Harden (FR-001..FR-004)
- [x] Reframe concordance outputs as internal robustness.
- [x] Add external held-out ingestion + schema/range guards.

## Phase 4: Test
- [x] Unit/integration contract tests in `tests/unit/test_second_slice_hardening.py`.

## Phase 5: Reproducibility
- [x] Validation reproducibility bundle emitted (`commands.sh`, `environment.yml`, `checksums.sha256`).

## Phase 6: Docs
- [x] `docs/runbooks/stage_10_validation.md` and report language updated to robustness framing.

## Phase 7: Sign-off
- [x] CHANGELOG + status updates completed.
- [ ] Memory update (deferred: memory edits only on explicit user request).
