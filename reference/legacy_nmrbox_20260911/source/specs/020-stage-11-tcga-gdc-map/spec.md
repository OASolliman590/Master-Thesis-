# Feature Specification: Stage 11 — TCGA / GDC Mapping

**Feature Branch**: `020-stage-11-tcga-gdc-map`
**Created**: 2026-05-30
**Status**: Draft (stub — full 6-file cycle pending)
**Scientific-priority rank**: supporting (data-prep for Stage 12). Severity S3.
**Input**: 2026-05-30 review §"Stage 11/12".

## Context Lock
`cmd_tcga_map` (L9057), `cmd_tcga_naive_map` (L7268), `cmd_tcga_naive_manifest` (L7378). Builds the TCGA expression/survival map + naive (treatment-naive) inclusion manifest consumed by Stage 12 projection.

## Findings addressed
- Data-prep correctness underpins the Stage 12 prognostic framing (12a): the "naive" inclusion is what makes the prognostic interpretation coherent — verify it actually restricts to treatment-naive / standard-care samples and that gene-ID space matches the signature (Ensembl trimming at L9221).

## Draft Functional Requirements
- **FR-001**: The naive-inclusion manifest MUST be documented and verified to exclude post-ICB/confounded samples; its definition feeds the prognostic-vs-predictive framing (spec 021).
- **FR-002**: Gene-ID harmonisation between signature space and TCGA expression MUST be explicit (no silent dropping); report overlap counts.
- **FR-003**: Extract to `_11_tcga_map`; tests; reproducibility bundle; runbook.

> **Stub status:** plan/research/benchmarks/quickstart pending.
