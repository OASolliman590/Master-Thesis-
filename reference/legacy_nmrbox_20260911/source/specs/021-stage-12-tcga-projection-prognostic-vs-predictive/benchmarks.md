# Benchmarks: Spec 021 — Stage 12 TCGA Projection

## Correctness Benchmarks
- `signature_score_z` column emitted and non-degenerate for non-constant scores.
- Survival stats record `model_covariates` contract.
- TCGA framing remains prognostic-only across status/report artifacts.
- Optional Layer-4 vs Thorsson outputs emit valid rows when subtype input is supplied.

## Performance Benchmarks
- z-scoring adds negligible overhead versus baseline projection.
- Optional layer-4 association cost scales with number of gene sets and projects.
