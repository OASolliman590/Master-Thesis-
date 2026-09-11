# Quickstart: Spec 026 — Analysis Design Contrast Registry

Build the design artifacts without running DE/meta:

```bash
python3.13 -m src.pipeline.cli design build \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --check-expression-readiness \
  --out results/analysis_design
```

Inspect planned analyses through the router without executing:

```bash
python3.13 -m src.pipeline.cli router run \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --analysis-registry results/analysis_design/analysis_contrast_registry.tsv \
  --analysis-membership results/analysis_design/analysis_contrast_membership.tsv \
  --dry-run \
  --out results/router_design_dry_run
```

Run one materialized analysis ID through DE during migration:

```bash
python3.13 -m src.pipeline.cli de run \
  --contrast PRE_RESPONSE \
  --analysis-id PRE_RESPONSE \
  --analysis-registry results/analysis_design/analysis_contrast_registry.tsv \
  --analysis-membership results/analysis_design/analysis_contrast_membership.tsv \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --out results/within_cohort_de_design
```
