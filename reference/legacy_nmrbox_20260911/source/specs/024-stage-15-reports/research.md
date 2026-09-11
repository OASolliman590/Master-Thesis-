# Research Notes: Spec 024 - Stage 15 Reports

## Scientific Framing

The final report is the place where execution success can accidentally become claim inflation. The corrected upstream design separates:

- discovery signatures from validated predictors;
- TCGA prognostic projection from ICB-response validation;
- internal concordance/LOCO robustness from external validation;
- broad visualization diagnostics from registry-filtered thesis figures.

## Report Contract

The report layer should make claim boundaries visible in both Markdown and TSV form. This makes the final thesis text easier to audit and makes downstream manuscript/report drafting less dependent on memory.

## Visualization Contract

Spec 025 figure manifests already carry `scientific_note` and framing fields. Spec 024 should not re-interpret figures; it should summarize whether the figure set passed caption linting and where each manifest lives.

## Current Reviewed Root

The current report-ready root is:

`results/analysis_id_runs_t7_20260607_stage07_scale_provenance`

The thesis-facing figures should use the registry-filtered figure root:

`figures/analysis_id_runs_t7_20260607_stage07_scale_provenance_registry_filtered`

The earlier broad-manifest figure root is diagnostic only because it can include cohorts that the analysis registry excludes.

## Risks

- Reports may cite stale review notes that said TCGA was blocked before the T7 download.
- Figure summaries may accidentally include broad-manifest figures instead of registry-filtered figures.
- External validation may be implied when the only available evidence is internal LOCO robustness or TCGA prognosis.

## Mitigations

- Supersede stale TCGA-blocked notes with the T7 audit.
- Require `--figure-root` to point to the registry-filtered figure root for thesis-facing report builds.
- Emit `report_claim_boundaries.tsv` and include the same boundaries in `pipeline_summary.md`.
