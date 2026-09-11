# Quickstart: Spec 015 — Stage 06 Within-Cohort DE

## TL;DR
```bash
# DE now routes by spec-010 assay_type onto a harmonized log2 scale + one uniform model:
python -m pipeline.cli de run \
  --contrast PRE_RESPONSE \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --out results/spec_015
```

## What changed vs the old behavior
- **No more magnitude guess.** Transform is decided by `assay_type` (spec 010), not `max<50 & median<25`.
- **No more default Welch t-test.** Non-count cohorts now use moderated limma (`eBayes`, `trend=TRUE`); verified counts use DESeq2/edgeR/voom. All emit `log2fc + se + model_class` on a common log2 scale.
- **Methylation/unreadable cohorts are hard-excluded** (no longer silently coerced).
- **Composition is NOT adjusted by default** — infiltration is a mediator (D5); the primary signature is composition-unadjusted (total effect).

## How to read the output
- `model_class` names the exact method per cohort.
- `se` is a true standard error on the log2 scale → safe for Stage-07 inverse-variance meta.
- `results/spec_015/de_model_migration.md` lists every cohort whose model changed and the effect on its top genes — review before running Stage 07.

## Verify count cohorts didn't regress
```bash
# verified-count cohorts (e.g. gse91061) should match the prior DESeq2 output exactly:
diff <(sort old/PRE_RESPONSE/gse91061_melanoma_pd1.tsv) <(sort results/spec_015/PRE_RESPONSE/gse91061_melanoma_pd1.tsv)
```

## Where to look next
- `docs/reviews/study_design_decisions_2026-05-30.md` (D2 harmonize-then-uniform, D5 mediator).
- spec 016 (meta input guard), spec 018 (deconvolution for the mediation secondary).
