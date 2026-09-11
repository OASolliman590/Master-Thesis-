# Feature Specification: Stage 03 — Manifest Build

**Feature Branch**: `012-stage-03-manifest-build`
**Created**: 2026-05-30
**Status**: Draft (stub — full 6-file cycle pending)
**Scientific-priority rank**: supporting. Severity S3.
**Input**: 2026-05-30 review §"Stage 03".

## Context Lock
`cmd_manifest_build` (cli.py L3100). Consults the patient manifest (spec 007) before the global table; logs divergences.

## Findings addressed
- **03 (S3):** verify it propagates the new spec-010 fields (`assay_type`, `response_definition_id`, `timing_provenance`) end-to-end and does not silently default them; divergence logging must cover the new fields.

## Draft Functional Requirements
- **FR-001**: Manifest build MUST carry through `assay_type`, `response_definition_id`, `timing_provenance` without defaulting; missing values are explicit errors or flagged, not blanks.
- **FR-002**: Divergence log MUST include assay/response/timing mismatches between patient manifest and global table.
- **FR-003**: Extract to `_03_manifest`; tests; reproducibility bundle; runbook.

> **Stub status:** plan/research/benchmarks/quickstart pending.
