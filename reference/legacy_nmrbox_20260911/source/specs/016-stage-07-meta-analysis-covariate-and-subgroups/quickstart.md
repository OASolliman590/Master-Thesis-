# Quickstart: Spec 016 — Stage 07 Meta Analysis

```bash
python -m pipeline.cli meta run \
  --contrast PRE_RESPONSE \
  --de-dir results/de \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --out results/spec_016_meta \
  --knapp-hartung
```

## Expected outputs
- `meta_effects.tsv`
- `meta_single_cohort.tsv`
- `meta_regression_cancer_group.tsv` (when enough cohorts)

## Checks
- No off-contract inputs pass the common-scale guard.
- `meta_single_cohort.tsv` contains explicit `meta_basis=single_cohort` rows.
