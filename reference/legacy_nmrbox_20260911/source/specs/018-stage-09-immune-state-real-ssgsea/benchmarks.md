# Benchmarks: Spec 018 — Stage 09 Immune State

## Baseline (measure at M2)
| metric | command | baseline |
|---|---|---|
| immune score wall time (21 cohorts) | `time python -m pipeline.cli immune score ...` | TBD (Python rank-mean is fast) |
| ssGSEA via GSVA wall time | per-cohort `Rscript scripts/ssgsea_gsva.R` | TBD (R + GSVA slower) |

## Regression budget
- GSVA ssGSEA is heavier than the rank-mean proxy: **wall-time increase is expected and acceptable** (correctness over speed). Budget: keep total Stage-09 under ~10 min for 21 cohorts; batch cohorts and cache per-cohort scores keyed on expression-file checksum.
- Scores WILL differ from the proxy (that's the point) — not a regression; validate against GSVA reference instead.

## Correctness validation (the real bar)
- ssGSEA scores from the wired pipeline MUST equal direct `GSVA::gsva(ssgseaParam(...))` on the same input within numerical tolerance.
- Layer-4: all 8 sets present and scored on ≥1 fixture cohort; membership unit-tested.
- Sanity: T_CELL_INFLAMED_GEP_18 (L1) should rank responders > non-responders on a known cohort (directional check).
