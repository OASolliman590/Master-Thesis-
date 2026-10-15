# Paper D Source and Contract Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use a TDD, task-by-task execution workflow with independent review before integration.

**Goal:** Implement the first approved Paper D source/contract packet: D-R02, D-R03, D-R05 and D-R07.

**Architecture:** Add small, focused source identity, condition/feature/control/overlap validators and a pure arithmetic evaluator. Reuse existing repository provenance/checksum patterns after an explicit reuse audit. Keep scientific data, model inference, and simulation outside this first packet.

**Tech Stack:** Python 3.11-compatible standard library where feasible; JSON Schema/TSV contracts; existing repository test conventions.

**Spec:** `specs/D/revision_20261015/`

## Global constraints

- preserve historical D files;
- exact D1 theta and fixed comparator;
- fail closed on unknowns/fallbacks;
- synthetic fixtures are labelled and prove software only;
- no model inference, large download, GPU job, controlled access, or real scoring;
- all cells remain nested within their biological unit;
- no branch merge or issue closure.

## Task 1 — reuse audit

Inspect existing source/manifests/checksum utilities and tests. Produce a reuse matrix with exact paths, callers, risks and disposition before adding duplicate code.

## Task 2 — source and condition schemas

Write failing tests for invalid source status, missing biological unit, unsupported dose/time, alias collision and unknown overlap. Implement the minimum validators and typed errors.

## Task 3 — feature/control contracts

Write failing tests for duplicate genes, missing genes, wrong order, incompatible transform and global-control fallback. Implement exact-order and matched-control validation.

## Task 4 — D1 evaluator

Write independent hand-calculated tests for positive, negative and zero theta; equal drug/condition/replicate weighting; unequal cell counts; empty `K_c`; missing prediction; and required-condition failure. Implement pure functions with no I/O dependency.

## Task 5 — registry/reporting integration

Produce deterministic eligibility and arithmetic receipts with input/config/code hashes and explicit incomplete status. Run scoped and project regressions, then submit bounded diff and evidence to the integrator.
