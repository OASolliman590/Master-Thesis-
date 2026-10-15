# Paper C Scientific Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the approved C3/C2/C1 architecture, develop the paired `Q_M` versus `Q_E` primary contract, and publish a validated review-only specification kit without running perturbation effects.

**Architecture:** Add a dated decision and scientific report, a focused revision folder beside the historical Paper C package, machine-readable schemas/manifests, and standard-library validation tests. Preserve existing specifications and add pointers rather than deleting history.

**Tech Stack:** Markdown, Mermaid, JSON Schema Draft 2020-12, TSV, Python 3 standard library, GitHub review branch.

**Spec:** `docs/decisions/C_FRAMEWORK_20261015.md` and `specs/C/revision_20261015/README.md`

## Global Constraints

- Base branch is `main` at `a8278c776da7c6b096cc14139d729979db286b50`.
- Work only on `review/paper-c-scientific-revision-20261015`.
- Do not run perturbation effects or modify wet-lab experiments.
- C3 is approved; C2 is bounded discovery; C1 is secondary calibration.
- The paired endpoint is proposed until query/source gates close.
- Preserve historical files and decisions.
- Missing evidence is `UNKNOWN`, not inferred.

## Review Focus

- Query matching must prevent unequal programme/direction budgets.
- Independent biological units must not be replaced by genes, wells or cells.
- C1 wording must not imply comparative efficacy.
- Source manifests must not invent eligible or independent `N`.
- Regulatory and inventory claims must be molecule/formulation/date specific.

---

### Task 1: Record the scientific amendment

**Files:** create decision, revision report, scope and README.

- [ ] Write the approved framework and explicit non-authorisations.
- [ ] Record the 25-section scientific revision report.
- [ ] Verify the report contains no perturbation result or winning drug.
- [ ] Commit documentation.

### Task 2: Define scientific and statistical contracts

**Files:** protocol, novelty, source, query, drug, analysis, scorer, exposure, validation, pharmacology, integration, wet-lab and figure documents.

- [ ] Specify each evidence type, unit, estimand and claim ceiling.
- [ ] Define the paired sample-level endpoint and finite-set summary.
- [ ] Define C1/C2 numerical and identity boundaries.
- [ ] Cross-check every document against the decision.
- [ ] Commit contracts.

### Task 3: Add implementation architecture and machine-readable contracts

**Files:** software/readiness/questions, schemas, fixtures, manifests and tickets.

- [ ] Add closed JSON schemas and synthetic fixtures.
- [ ] Add source and decision manifests without invented outcomes.
- [ ] Add staged implementation tickets and release gates.
- [ ] Commit engineering package.

### Task 4: Add substantive validation

**Files:** `tests/test_revision_contracts.py`, audit and package hashes.

- [ ] Write contract, fixture, link, manifest and overclaim tests.
- [ ] Run the suite and inspect all output.
- [ ] Generate file hashes and rerun the full suite.
- [ ] Record exact Python/command/results.
- [ ] Commit validation evidence.

### Task 5: Publish review branch

**Files:** update `CONTEXT.md` and `specs/C/README.md` with non-destructive pointers.

- [ ] Verify branch diff and changed-file list.
- [ ] Verify the final branch head and tests.
- [ ] Open a draft pull request to `main`.
- [ ] Do not merge or enable auto-merge.
