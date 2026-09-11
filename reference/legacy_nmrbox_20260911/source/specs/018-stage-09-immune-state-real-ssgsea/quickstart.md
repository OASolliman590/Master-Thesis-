# Quickstart: Spec 018 — Stage 09 Immune State

## TL;DR
```bash
# ssGSEA now uses real GSVA (scripts/ssgsea_gsva.R), not the rank-mean proxy:
python -m pipeline.cli immune score \
  --sample-manifest configs/sample_manifest_curated.tsv \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30 \
  --gene-set-registry configs/immune_gene_sets_registry.tsv \
  --out results/spec_018
```

## What changed
- **Real ssGSEA.** `cmd_immune_score` dispatches to `scripts/ssgsea_gsva.R` (GSVA). The `ssgsea_rank_mean_python` backend is gone; method label is now `gsva_ssgsea`. Fails loudly if R/GSVA missing (no silent proxy).
- **ESTIMATE/EPIC** are wired to `scripts/estimate_scores.R` / `epic_scores.R` (real scores) or removed — no more `IMMUNE_SCORE_proxy_deprecated`.
- **Layer-4 complete.** All 8 epigenetic sets (PRC2_IMMUNE_TARGETS, SWI_SNF_ICB, DNMT_IMMUNE_LOCI, HISTONE_WRITERS_ICB, EPIGENETIC_CHECKPOINT, RETROELEMENT_SENSING, T_CELL_EXHAUSTION_EPIGENETIC, T_CELL_MEMORY_EPIGENETIC) ship and are scored.
- **Composition = mediator (D5).** Deconvolution outputs feed the Stage-06 mediation analysis; they are NOT used to adjust DE by default.

## Verify
```bash
# ssGSEA pipeline output equals direct GSVA on the same input:
Rscript scripts/ssgsea_gsva.R --expr <cohort_expr.tsv> --gmt inputs/gene_sets/T_CELL_INFLAMED_GEP_18.gmt --out /tmp/ref.tsv
# compare /tmp/ref.tsv to results/spec_018/ssgsea_scores.tsv for that set
```

## Where to look next
- Source audit confirming the real scripts exist: `docs/reviews/pipeline_scientific_review_2026-05-30.md` (Step-4 section).
- spec 015 (consumes deconvolution as mediator), spec 021 (Layer-4 vs Thorsson).
