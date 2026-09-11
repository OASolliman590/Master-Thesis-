# Feature Specification: Stage 13 — TCIA Overlay (Decommission / Confirm Disabled)

**Feature Branch**: `022-stage-13-tcia-overlay-decommission`
**Created**: 2026-05-30
**Status**: Draft (stub — full 6-file cycle pending)
**Scientific-priority rank**: cleanup. Severity S3.
**Input**: 2026-05-30 review §"Stage 13"; README/spec-007 (TCIA deprecated).

## Context Lock
`cmd_tcia_overlay` (cli.py L9438). Deprecated in spec 007; README says it is "not registered as an active CLI workflow."

## Findings addressed
- Confirm the overlay is fully decommissioned (not silently runnable) so no deprecated radiomics path can leak into reports.

## Draft Functional Requirements
- **FR-001**: Either fully remove `cmd_tcia_overlay` and its CLI registration, or gate it behind an explicit `--enable-deprecated` flag that prints a deprecation notice and is excluded from `run_full_pipeline.sh`.
- **FR-002**: Confirm no report/summary references TCIA outputs.
- **FR-003**: Document the decommission in CHANGELOG + runbook.

> **Stub status:** plan/research/benchmarks/quickstart pending. Likely the smallest cycle.
