# Tasks: Spec 024 — Stage 15 Reports

## Phase 0: Spec Kit Setup
- [x] T001 Promote `spec.md` from stub to active implementation cycle.
- [x] T002 Add `plan.md`, `research.md`, `benchmarks.md`, and `quickstart.md`.

## Phase 1: Audit - corrected framing
- [x] T003 Supersede stale TCGA-blocked review language with the T7-completed Stage 12 audit.
- [x] T004 Confirm TCGA report language remains prognostic-only.
- [x] T005 Confirm concordance/LOCO language remains internal robustness only.

## Phase 2: Contract lock
- [x] T006 Add report claim-boundary artifact contract: `report_claim_boundaries.tsv`.
- [x] T007 Add visualization manifest summary artifact: `figure_manifest_summary.tsv`.
- [x] T008 Add optional `report build --figure-root` input.

## Phase 3: Harden
- [x] T009 Update `cmd_report_build` to emit claim-boundary Markdown and TSV.
- [x] T010 Update `cmd_report_build` to summarize figure manifests and caption-lint failures.
- [x] T011 Add visualization status to `evidence_readiness_status.tsv` when figure manifests are supplied.

## Phase 4: Test
- [x] T012 Add unit coverage for claim-boundary and figure-manifest reporting.
- [x] T013 Run focused report/visualization/TCGA tests.

## Phase 5: Reproducibility
- [x] T014 Build final report bundle from the reviewed root and registry-filtered figure root.
- [x] T015 Record exact command and output paths in the reviewed root logs.

## Phase 6: Docs
- [x] T016 Update Stage 15 runbook or quickstart with the reviewed-root command.

## Phase 7: Sign-off
- [x] T017 Audit final report for prohibited language: TCGA validation, validated responder predictor, external validation where not supported.

## Task to FR Traceability
| FR | Tasks |
|---|---|
| FR-001 | T003, T004, T009, T017 |
| FR-002 | T006, T009 |
| FR-003 | T006, T009 |
| FR-004 | T002, T016 |
| FR-005 | T007, T008, T010, T011 |
| FR-006 | T006, T007, T009, T010 |
