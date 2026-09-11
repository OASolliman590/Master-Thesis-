# Feature Specification: Stage 04 — Expression Resolution & (SRA) Quantification

**Feature Branch**: `013-stage-04-expression-resolution-and-quant`
**Created**: 2026-05-30
**Status**: Draft (stub — full 6-file cycle pending)
**Scientific-priority rank**: supporting X1 (rank-1 family). Severity **S2/S3**.
**Input**: 2026-05-30 review §"Stage 04".

## Context Lock
`cmd_ingest_run` (cli.py L4007) is a **stub** — it writes `ingest_status="stub_ready"` per sample and does no quantification. Real expression enters via downloaded author matrices resolved by `resolve_primary_expression_path` (common/expression.py).

## Findings addressed
- **04a (S2/S3):** the stage advertises "ingest" but performs none → proximate cause of X1 (no uniform quantification); the 8 SRA-only cohorts (project memory) are uningestable without a FASTQ→counts path.

## Draft Functional Requirements
- **FR-001**: Reframe the stage honestly as **expression resolution** (selecting + validating the author matrix per cohort) and make spec-010 assay detection its responsibility, OR
- **FR-002**: Implement a real FASTQ→counts path (salmon/STAR+featureCounts) for SRA-only cohorts producing uniform `raw_counts`, unlocking the 7 recoverable RNA-seq cohorts (project memory) and giving a homogeneous-assay subset.
- **FR-003**: Whichever path: emit a per-cohort expression-provenance record (author-matrix vs re-quantified; tool + version) feeding `assay_type`.
- **FR-004**: Extract to `_04_expression`; tests; reproducibility bundle; runbook.

## Out Of Scope
- The FASTQ retrieval itself (a Stage 00 / dedicated SRA-FASTQ spec, per project memory).

> **Stub status:** plan/research/benchmarks/quickstart pending. Scope (resolution-only vs full quant) is a user decision when this cycle opens.
