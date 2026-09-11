# Implementation Plan: Spec 024 - Stage 15 Reports

## Goal

Harden the final report layer so it summarizes corrected RNA-seq pipeline outputs without overstating scientific claims.

The report is a thesis-facing evidence map, not a new analysis stage. It must preserve the corrected interpretation boundaries established by specs 019, 021, 025, and 026.

## Inputs

- Corrected run root: `results/analysis_id_runs_t7_20260607_stage07_scale_provenance`
- Registry-filtered figure root: `figures/analysis_id_runs_t7_20260607_stage07_scale_provenance_registry_filtered`
- Stage 10 validation/robustness summaries
- Stage 12 TCGA prognostic projection outputs
- Spec 025 figure manifests and caption sidecars

## Outputs

- `pipeline_summary.md`
- `run_readiness_summary.tsv`
- `evidence_readiness_status.tsv`
- `multi_contrast_summary.tsv`
- `report_claim_boundaries.tsv`
- `figure_manifest_summary.tsv`

## Design

1. Keep `cmd_report_build` as the user-facing command.
2. Add optional `--figure-root` so report builds can consume Spec 025 outputs without making figures mandatory.
3. Emit a machine-readable claim-boundary TSV covering TCGA, concordance, and signature interpretation.
4. Summarize every supplied `figure_manifest.tsv`, including total figures, TCGA figure counts, concordance figure counts, and caption-lint failures.
5. Add visualization readiness to `evidence_readiness_status.tsv` when figure manifests exist.

## Non-Goals

- Do not rerun differential expression, meta-analysis, immune scoring, or TCGA projection.
- Do not label TCGA as ICB response validation.
- Do not convert discovery signatures into validated predictors.
- Do not hide missing external validation.

## Sign-Off Gate

The final report bundle is acceptable only if:

- TCGA wording is prognostic/projection only.
- Concordance wording is internal robustness only.
- Figure caption lint failures are zero.
- External validation status is explicit.
