# Feature Specification: RNA-seq Pipeline Hardening and Execution Readiness (v1)

**Feature Branch**: `004-rnaseq-pipeline-hardening-and-execution-readiness`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: Formal review of the current RNA-seq pipeline after evidence run `results/evidence_20260327_104332`, with direction to convert the scaffold from exploratory-ready to execution-ready.

## Context Lock

### Current Baseline

Already implemented in the current codebase:

- router orchestration for tracks `A/B/C`
- cohort QC
- within-cohort DE
- cross-cohort meta-analysis
- signature derivation
- immune scoring
- validation scaffolding
- TCGA projection scaffolding
- report builder

Current test baseline:

- local test suite passes (`21 passed`)

### Current Review Findings That Drive This Spec

- evidence execution is operationally broad but biologically sparse
- `mega_analysis` can be skipped because too few analysis-ready cohorts contribute to the primary contrast
- signature derivation can complete as an empty artifact rather than a biologically useful output
- routed/executed summaries still include sync stubs in a way that overstates scientific execution breadth
- `immune effects` contains at least one runtime-safety defect and is not yet trustworthy as an execution-ready stage

This spec does not redesign the thesis architecture. It hardens the existing pipeline so another execution cycle can be run with defensible status reporting and clearer scientific readiness.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run only scientifically eligible cohorts by default (Priority: P1)

As the analysis owner, I need router and evidence runs to distinguish analysis-ready cohorts from sync stubs and blocked cohorts so execution summaries match biological reality.

**Independent Test**: A router run with mixed real cohorts and sync stubs emits separate counts/status rows for analyzed, blocked, and stub cohorts, and excludes stubs from default execution.

### User Story 2 - Trust immune-effects execution status (Priority: P1)

As the analysis owner, I need `immune effects` to run without hidden runtime defects so the immune-state branch can be included in the next evidence cycle.

**Independent Test**: A smoke test for `immune effects` completes on a minimal fixture cohort and emits both `marker_correlations.tsv` and `cohort_level_effects.tsv`.

### User Story 3 - Prevent misleading “successful biology” when outputs are empty (Priority: P1)

As the analysis owner, I need empty signature and underpowered meta states to be treated as blocked readiness outcomes, not successful discovery runs.

**Independent Test**: A run with insufficient eligible cohorts emits explicit blocked readiness artifacts and summary language rather than a misleading success posture.

### User Story 4 - Re-run evidence on an analysis-ready subset (Priority: P2)

As the analysis owner, I need one canonical evidence rerun path using analysis-ready cohorts only so the next execution cycle can test whether the pipeline now produces non-empty discovery outputs.

**Independent Test**: The documented evidence rerun path produces a readiness summary showing cohort eligibility counts, meta eligibility counts, and signature status.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define explicit cohort-readiness states for routed cohorts.
- **FR-002**: The default router behavior MUST exclude `sync_stub` cohorts from execution unless explicitly overridden.
- **FR-003**: The system MUST distinguish at minimum these statuses in execution-facing outputs:
  - `analyzed`
  - `blocked`
  - `stub_excluded`
  - `routed_not_executed`
- **FR-004**: The system MUST emit a machine-readable readiness summary for each evidence-style run.
- **FR-005**: The readiness summary MUST report counts for routed cohorts, analyzed cohorts, blocked cohorts, stub cohorts, and meta-eligible cohorts.
- **FR-006**: The system MUST repair `immune effects` so all required gene-ID mapping settings are resolved locally within the command.
- **FR-007**: The system MUST add a direct smoke test for `immune effects`.
- **FR-008**: The system MUST treat empty-signature outcomes as explicit readiness-status outputs, not as implicitly successful scientific discovery.
- **FR-009**: The system MUST require a minimum eligible cohort threshold before meta-analysis and signature derivation are presented as primary discovery-ready outcomes.
- **FR-010**: The report builder MUST separate command execution status from scientific-analysis status.
- **FR-011**: The report layer MUST NOT mix sync stubs with analyzed cohorts without an explicit status field.
- **FR-012**: The pipeline MUST preserve the current architecture of within-cohort DE followed by cross-cohort synthesis.
- **FR-013**: The pipeline MUST continue to support blocked/skipped artifacts as first-class outputs.
- **FR-014**: The quickstart and usage-facing docs MUST define one canonical evidence rerun path for analysis-ready cohorts only.
- **FR-015**: The system MUST keep processed-matrix DE available but MUST label it as exploratory-grade in readiness-facing reporting/documentation.

### Key Entities *(include if feature involves data)*

- **Cohort Readiness Record**: cohort-level execution eligibility state and reason.
- **Run Readiness Summary**: per-run counts and statuses for routed, analyzed, blocked, and stub cohorts.
- **Evidence Readiness Status Record**: run-level summary of whether meta/signature/validation stages are scientifically eligible.
- **Immune Effects Smoke Fixture**: minimal fixture data proving the `immune effects` command executes successfully.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `immune effects` executes successfully on a smoke fixture without hidden variable-scope failures.
- **SC-002**: Router/default evidence runs exclude sync stubs from execution by default.
- **SC-003**: Run summaries clearly separate operational execution from scientific analysis readiness.
- **SC-004**: A machine-readable readiness summary is produced for evidence-style runs.
- **SC-005**: Empty meta/signature states are surfaced as explicit blocked readiness outcomes.
- **SC-006**: One canonical analysis-ready evidence rerun path is documented for the next execution cycle.

