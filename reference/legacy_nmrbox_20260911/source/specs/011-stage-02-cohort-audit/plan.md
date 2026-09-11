# Plan: Spec 011 — Stage 02 Cohort Audit

## Architecture
- Keep Stage-02 entrypoint at `cmd_cohort_audit`.
- Consume optional Stage-01 artifacts:
  - `assay_detection.tsv`
  - `response_definition.tsv`
- Emit explicit inclusion semantics per cohort (`audit_status`, `include_decision`, `reason`).

## Milestones
- **M1** Document baseline audit outputs and downstream use.
- **M2** Lock vocabulary and exclusion policy from D0/D1 (dedup/drop/assay exclusions).
- **M3** Harden gates and wire Stage-01 provenance.
- **M4** Add/extend unit tests for exclusion and curation behavior.
- **M5** Runbook + changelog sign-off.

## Dependencies
- Upstream: spec 010 (assay + response provenance).
- Downstream: Stage 03 manifest build and all analysis stages that consume filtered cohorts.

## Rollback
- All changes are contract-level audit gating and TSV status outputs; no committed `results/` rewrites.
