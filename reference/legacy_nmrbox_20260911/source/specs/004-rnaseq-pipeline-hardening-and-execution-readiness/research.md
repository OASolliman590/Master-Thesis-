# Research Notes: RNA-seq Pipeline Hardening and Execution Readiness (v1)

## Purpose

Capture the review-locked decisions that should govern the next implementation cycle before another evidence run is attempted.

## Locked Decisions

### Decision 1: Preserve architecture, harden readiness

- **Decision**: keep the current study-preserving architecture (`within-cohort DE -> meta -> signature -> validation`) and do not redesign it in this cycle.
- **Why**: the main problem is readiness and truthfulness, not architectural direction.

### Decision 2: Sync stubs must not inflate execution summaries

- **Decision**: sync-stub cohorts are inventory placeholders and must be excluded from default execution/report success counts.
- **Why**: current summaries can overstate biological execution breadth.

### Decision 3: Empty signature is a blocker state

- **Decision**: empty signature output remains technically allowed as an artifact, but it is interpreted as a blocked readiness outcome.
- **Why**: an empty signature is useful for debugging/reporting, but it is not a successful biological result.

### Decision 4: `immune effects` must be smoke-tested directly

- **Decision**: do not rely on indirect confidence from other stages; add a dedicated smoke path for `immune effects`.
- **Why**: review found that the command likely depends on undefined locally scoped variables.

### Decision 5: Processed-matrix DE remains exploratory in this cycle

- **Decision**: keep the current processed-matrix DE path, but mark it explicitly as exploratory-grade.
- **Why**: this cycle is about execution safety and truthfulness first, not a full statistical redesign.

### Decision 6: Readiness summary becomes a first-class artifact

- **Decision**: each evidence-style run should emit a machine-readable readiness summary.
- **Why**: the next execution cycle needs an auditable answer to “what really ran” versus “what was merely routed.”

## Review Findings That This Cycle Responds To

- `mega_analysis` can be skipped because too few cohorts are truly eligible
- `signature derive` can finish with a header-only artifact
- validation can be structurally wired but biologically empty
- evidence reporting currently mixes analysis-ready and sync-stub cohorts in a misleading way
- at least one immune-state command path is not yet runtime-safe

## Non-Goals

- redesigning the thesis hypothesis
- replacing the current DE/meta architecture
- rewriting all processed-matrix statistics in this cycle
- turning TCGA into the main execution focus for this hardening pass

