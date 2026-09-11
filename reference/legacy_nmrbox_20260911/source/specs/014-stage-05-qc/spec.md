# Feature Specification: Stage 05 — QC (Enforcement & Assay-Aware Diagnostics)

**Feature Branch**: `014-stage-05-qc`
**Created**: 2026-05-30
**Status**: Draft (stub — full 6-file cycle pending)
**Scientific-priority rank**: low (strongest existing stage). Severity **S3**.
**Input**: 2026-05-30 review §"Stage 05".

## Context Lock
`cmd_qc_run` (cli.py L4028) — the strongest scientific stage: library size, zero-fraction, Cook's-distance leverage, PCA by response, sample-distance heatmap, housekeeping stability, and a global variance-partition / batch assessment.

## Findings addressed
- **05a (S3, CONFIRMED Step-4 audit):** `sample_outlier_flags.tsv` is written by `cmd_qc_run` and **read by nothing** — DE re-resolves samples independently. Outlier detection is **decorative**. The fix (FR-001) is a real, opt-in exclusion path.
- **05b (S2, minor):** global PCA concatenates raw matrices with `log2(x+1)` regardless of assay type (X1) — affects only the batch-severity diagnostic.

## Draft Functional Requirements
- **FR-001**: QC outlier flags MUST be consumable by DE (Stage 06) via an explicit, documented exclusion path; "flag-only" mode preserved but not the default-silent behaviour.
- **FR-002**: Global batch diagnostics MUST use the spec-010 `assay_type` to choose the correct transform per cohort before concatenation.
- **FR-003**: Extract to `_05_qc` (alongside `qc_plots`); tests; reproducibility bundle; runbook.

> **Stub status:** plan/research/benchmarks/quickstart pending.
