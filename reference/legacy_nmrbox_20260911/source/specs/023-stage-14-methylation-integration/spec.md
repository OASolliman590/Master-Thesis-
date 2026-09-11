# Feature Specification: Stage 14 — Methylation Integration

**Feature Branch**: `023-stage-14-methylation-integration`
**Created**: 2026-05-30
**Status**: Draft (stub — deferred; full cycle pending)
**Scientific-priority rank**: deferred (epigenetic arm). Severity n/a yet.
**Input**: 2026-05-30 review §"Stage 14"; project memory (SRP609012 Bisulfite-seq held out of RNA arm).

## Context Lock
`cmd_methylation_integrate` (cli.py L9468). Deferred beyond spec 008. The one Bisulfite-seq cohort (SRP609012, Stomach — project memory) is correctly excluded from the RNA arm.

## Findings addressed
- This is the natural home for the epigenetic-mechanism layer that the thesis narrative leans on (DNA methylation at immune loci, retroelement derepression). Until opened, ensure the stub does not emit misleading partial outputs.

## Draft Functional Requirements (when opened)
- **FR-001**: Define the methylation data model (450k/EPIC array or WGBS/RRBS) and the integration question (methylation ↔ expression of Layer-4 epigenetic targets).
- **FR-002**: Keep methylation cohorts in a separate manifest; never mix into the RNA-seq DE/meta.
- **FR-003**: Extract to `_14_methylation`; tests; reproducibility bundle; runbook.

## Out Of Scope (until cycle opens)
- Everything — this remains deferred until the user opens it explicitly. Stub exists for cycle completeness only.

> **Stub status:** intentionally deferred. Do not implement without a user go-ahead.
