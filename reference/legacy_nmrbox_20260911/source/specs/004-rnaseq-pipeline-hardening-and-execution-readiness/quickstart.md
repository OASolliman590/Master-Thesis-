# Quickstart: RNA-seq Pipeline Hardening and Execution Readiness (Spec-004)

This file defines the implementation-facing stage order for the hardening cycle. For canonical operational commands, the repo should continue to use `docs/USAGE.md`.

## Purpose

Spec-004 is not a new biology workflow. It is the readiness layer that must be completed before the next thesis-facing evidence run.

## Stage Order

### 0) Runtime repair

Required implementation target:

- repair `python -m pipeline.cli immune effects ...` so it resolves all required gene-mapping config locally and runs as documented

Minimum acceptance:

- a direct smoke test passes for `immune effects`

### 1) Cohort-readiness model

Required implementation target:

- introduce explicit cohort-readiness states used by router/evidence/report outputs

Minimum accepted state families:

- `analyzed`
- `blocked`
- `stub_excluded`
- `routed_not_executed`

### 2) Truthful router/report outputs

Required implementation target:

- router summaries and report builder must distinguish operational execution from scientific analysis readiness

Minimum acceptance:

- sync-stub cohorts do not appear as default analyzed cohorts
- evidence run summaries show analyzed vs blocked vs stub-excluded counts

### 3) Empty-output readiness gating

Required implementation target:

- empty meta/signature states are reported as readiness blockers rather than successful discovery outcomes

Minimum acceptance:

- a run with insufficient eligible cohorts emits a blocked readiness artifact and summary language that says so explicitly

### 4) Canonical next evidence rerun definition

Required implementation target:

- document one analysis-ready evidence rerun path

Minimum prerequisites for that rerun:

- mounted data paths available
- analysis-ready cohort subset defined
- `immune effects` smoke test passing
- gene-set registry paths resolvable
- sync stubs excluded by default

## Acceptance Check (Spec-004)

Spec-004 is complete when:

- repaired commands are smoke-tested
- sync stubs no longer inflate default execution claims
- reports/readiness artifacts reflect real scientific eligibility
- the next evidence run has one clear, analysis-ready execution path

