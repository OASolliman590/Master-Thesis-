# Feature Specification: Stage 15 — Reports

**Feature Branch**: `024-stage-15-reports`
**Created**: 2026-05-30
**Status**: Active implementation cycle
**Scientific-priority rank**: final (must reflect corrected framing). Severity **S3**.
**Input**: 2026-05-30 review §"Stage 15".

## Context Lock
`cmd_report_build` (cli.py L9509). Aggregates stage outputs into `pipeline_summary.md` and friends.

## Findings addressed
- **15a (S3):** reports MUST NOT present S1-affected numbers (mega/validation/TCGA "validation") without the corrected caveats. Report language must match the corrected scientific framing once specs 015/018/019/021 land.

## Functional Requirements
- **FR-001**: Reports MUST label TCGA analysis prognostic (not predictive) and the indirect-vs-mega concordance as cross-method robustness (not validation), consistent with specs 019/021.
- **FR-002**: Reports MUST surface, per result, the DE `model_class`, the `assay_type` mix, and the response-definition provenance mix, so a reader can see the methods behind a number.
- **FR-003**: Reports MUST carry a "methods limitations" section auto-populated from the per-stage caveats.
- **FR-004**: Extract to `_15_reports`; tests; reproducibility bundle; runbook.
- **FR-005**: Reports MUST ingest figure manifests from spec 025 when supplied and summarize figure counts plus caption-lint failures.
- **FR-006**: Reports MUST emit machine-readable claim-boundary and figure-summary TSV artifacts in addition to `pipeline_summary.md`.

## Acceptance Criteria

- `report build` writes `pipeline_summary.md`, `run_readiness_summary.tsv`, `evidence_readiness_status.tsv`, `multi_contrast_summary.tsv`, `report_claim_boundaries.tsv`, and `figure_manifest_summary.tsv`.
- TCGA language in the report is prognostic/projection only.
- Same-sample concordance language is internal robustness only.
- Visualization manifests are summarized when `--figure-root` is supplied.
- The evidence status table includes visualization status when figure manifests are available.
