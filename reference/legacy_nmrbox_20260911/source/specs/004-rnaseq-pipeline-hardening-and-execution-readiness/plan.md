# Implementation Plan: RNA-seq Pipeline Hardening and Execution Readiness (v1)

**Branch**: `004-rnaseq-pipeline-hardening-and-execution-readiness` | **Date**: 2026-04-05 | **Spec**: `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/spec.md`  
**Input**: Feature specification from `specs/004-rnaseq-pipeline-hardening-and-execution-readiness/spec.md`

## Summary

Implement a hardening cycle that converts the current RNA-seq scaffold from exploratory-ready to execution-ready.

The cycle has four linked goals:

1. repair runtime correctness gaps
2. separate analysis-ready cohorts from sync stubs and blocked cohorts
3. make reports/readiness outputs scientifically truthful
4. define one canonical evidence rerun path for analysis-ready cohorts only

This cycle is intentionally incremental. It keeps the current discovery architecture and strengthens execution fidelity rather than redesigning the scientific framework.

## Technical Context

**Language/Version**: Python 3.11 primary; R hooks retained where already used  
**Primary Dependencies**: pandas, numpy, scipy, pytest, current repo-local R scripts  
**Storage**: file-based TSV/markdown artifacts under existing `results/`, `logs/`, and `reports/` structure  
**Testing**: pytest unit + integration smoke tests, plus new `immune effects` smoke coverage  
**Target Platform**: local workstation first, HPC-compatible command model second  
**Project Type**: hardening/refinement cycle for existing CLI scaffold  
**Constraints**: must preserve current CLI architecture, must not blur operational execution with biological readiness, must remain resume-friendly

## Constitution Check

Gates applied:

- **Truthfulness Gate**: report and readiness artifacts must reflect scientific eligibility, not just command execution.
- **Safety Gate**: documented commands must run without hidden scope/config failures.
- **Readiness Gate**: sync stubs and underpowered cohorts must not inflate discovery-stage success claims.
- **Continuity Gate**: preserve the current within-cohort-then-meta architecture and existing blocked-status design.

Gate status: **PASS**

## Workstreams

### Workstream A: Runtime Hardening

- repair `immune effects`
- audit stage handlers for local config resolution consistency
- add direct smoke tests for repaired commands

### Workstream B: Cohort Readiness and Routing Truthfulness

- introduce explicit cohort-readiness statuses
- exclude sync stubs from default execution
- preserve manual override behavior for exploratory runs

### Workstream C: Reporting and Readiness Artifacts

- add run-level readiness summary outputs
- update summary/report builder language to distinguish:
  - routed
  - analyzed
  - blocked
  - stub-excluded
- prevent empty-signature/underpowered-meta states from reading like successful biology

### Workstream D: Execution Cycle Definition

- define one canonical analysis-ready evidence rerun path
- document prerequisites and expected blocked vs success outcomes
- use the rerun to reassess whether the pipeline now produces a non-empty discovery signature

## Implementation Policies

### Policy 1: Sync stubs are not primary execution units

- `sync_stub` rows remain useful as inventory placeholders
- they are not counted as analyzed cohorts in default evidence runs
- they may be included only through explicit override flags

### Policy 2: Empty outputs are status, not success

- empty meta/signature outputs remain allowed as explicit artifacts
- they are interpreted as readiness blockers unless threshold criteria are satisfied

### Policy 3: Processed-matrix DE remains exploratory

- keep current processed-matrix DE available
- label it clearly as exploratory-grade in readiness-facing reports and docs
- reserve thesis-grade discovery claims for runs that pass the new readiness gates

## Artifact Policy

New or updated outputs in this cycle:

- cohort-readiness status artifact
- run-readiness summary artifact
- more explicit route/report status tables
- `immune effects` smoke-test coverage
- updated quickstart/tasks for the next execution cycle

