# Quickstart: Spec 011 — Stage 02 Cohort Audit

```bash
python -m pipeline.cli cohort audit \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --assay-detection results/intake/assay_detection.tsv \
  --response-definition results/intake/response_definition.tsv \
  --out results/spec_011_audit
```

## Expected outputs
- `cohort_audit.tsv`
- `cohort_audit_summary.tsv`

## Checks
- `gse126044` duplicate alias is excluded with explicit reason.
- `gse165278` is excluded with no-responder reason.
- `methylation_beta` / `unreadable` assay cohorts are excluded.
