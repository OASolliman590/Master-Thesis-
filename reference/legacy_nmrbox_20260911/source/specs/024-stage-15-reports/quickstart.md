# Quickstart: Spec 024 - Stage 15 Reports

## Build The Reviewed-Root Report

```bash
python3.13 -m src.pipeline.cli report build \
  --results-root results/analysis_id_runs_t7_20260607_stage07_scale_provenance \
  --figure-root figures/analysis_id_runs_t7_20260607_stage07_scale_provenance_registry_filtered \
  --out reports/analysis_id_runs_t7_20260607_stage07_scale_provenance \
  --run-manifest results/analysis_id_runs_t7_20260607_stage07_scale_provenance/logs/report_build_stage15.yaml
```

## Expected Outputs

- `reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/pipeline_summary.md`
- `reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/run_readiness_summary.tsv`
- `reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/evidence_readiness_status.tsv`
- `reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/multi_contrast_summary.tsv`
- `reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/report_claim_boundaries.tsv`
- `reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/figure_manifest_summary.tsv`

## Interpretation Rules

- TCGA rows are prognostic/projection context only.
- Concordance and nested LOCO rows are internal robustness only.
- Discovery signatures are not validated predictors unless held-out ICB-treated cohorts support them.

## Quick Audit

```bash
rg -n "TCGA.*validation|validated responder|external validation" \
  reports/analysis_id_runs_t7_20260607_stage07_scale_provenance/pipeline_summary.md
```

Any hit must be manually reviewed before thesis use.
