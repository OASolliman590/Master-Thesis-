# Tasks: RNA-seq Pipeline Hardening and Execution Readiness (v1)

**Input**: Design documents from `/specs/004-rnaseq-pipeline-hardening-and-execution-readiness/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `quickstart.md`, `contracts/io-contracts.md`

## Status Snapshot (2026-04-06)

Spec-004 implementation slices have been executed through readiness completion.

Current cycle state:

- CLI/report readiness contracts are implemented and tested
- `T009` and `T020` are completed in code and execution evidence
- router/report readiness artifacts now reflect analyzed vs blocked cohorts truthfully
- immune-effect execution path is runtime-hardened for current local environment constraints
- the remaining risk is scientific power (strict discovery thresholds can still yield empty signatures in small slices)

## Phase 0: Spec Kit Initialization

- [x] T001 Create `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/spec.md`.
- [x] T002 Create `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/plan.md`.
- [x] T003 Create `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/research.md`.
- [x] T004 Create `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/quickstart.md`.
- [x] T005 Create `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/contracts/io-contracts.md`.
- [x] T006 Create `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/tasks.md`.

## Phase 1: Runtime Correctness

- [x] T007 Repair `cmd_immune_effects` so gene-ID mapping config and threshold variables are defined locally inside the command.
- [x] T008 Add a direct smoke test for `immune effects` that emits `marker_correlations.tsv` and `cohort_level_effects.tsv`.
- [x] T009 Audit adjacent stage handlers for similar local-config resolution issues.

## Phase 2: Cohort Readiness Model

- [x] T010 Add an explicit cohort-readiness artifact for router/evidence runs.
- [x] T011 Introduce readiness statuses: `analyzed`, `blocked`, `stub_excluded`, `routed_not_executed`.
- [x] T012 Exclude sync stubs from default router/evidence execution while preserving an explicit override path.
- [x] T013 Add tests proving sync stubs are not counted as analyzed by default.

## Phase 3: Truthful Reporting

- [x] T014 Update route summaries to separate routed cohorts from scientifically analyzed cohorts.
- [x] T015 Add `run_readiness_summary.tsv` and `evidence_readiness_status.tsv`.
- [x] T016 Update report builder so empty-signature and underpowered-meta states are reported as blocked readiness outcomes.
- [x] T017 Add tests for truthful blocked/stub/analyzed counts in summary outputs.

## Phase 4: Meta and Signature Readiness Gates

- [x] T018 Add a minimum meta-eligibility rule for primary discovery-ready interpretation.
- [x] T019 Ensure empty signature outputs remain explicit artifacts but are labeled as blocked readiness states in summaries.
- [x] T020 Update validation summaries to inherit readiness language from upstream meta/signature status.

## Phase 5: Canonical Next Evidence Cycle

- [x] T021 Add one canonical analysis-ready evidence rerun path to docs/quickstart-facing material.
- [x] T022 Define rerun prerequisites: mounted data roots, analysis-ready cohort subset, resolvable gene-set registry, repaired immune-effects path.
- [x] T023 Define expected success vs blocked outputs for the next rerun.

## Completion Definition

Spec-004 is considered implementation-complete when:

- `immune effects` is repaired and smoke-tested,
- sync stubs no longer inflate default execution claims,
- run summaries distinguish routed vs analyzed vs blocked vs stub-excluded cohorts,
- empty meta/signature states are treated as readiness blockers rather than successful biology,
- and one canonical analysis-ready evidence rerun path is documented for the next cycle.
