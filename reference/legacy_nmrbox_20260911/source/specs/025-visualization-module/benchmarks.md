# Benchmarks: Spec 025 — Visualization Module

## Baseline (measure at M2)
| metric | command | baseline |
|---|---|---|
| current scattered plot time (qc + meta forests) | part of `qc run` / `meta run` | TBD |
| full `viz build` wall time | `time python -m pipeline.cli viz build --results-root <run> --out figures/` | TBD |

## Regression budget
- `viz build` is offline and re-runnable; budget **≤ 5 min** for the full thesis figure set on the 21-cohort run.
- Determinism is the hard requirement: same inputs → identical PNG bytes (modulo metadata timestamp). Test by double-render + checksum (allow timestamp chunk).

## Notes
- Figures are I/O + render bound; parallelize per-figure if needed.
- No numerical results are produced here (rendering only), so there is no scientific regression budget — correctness = "reads the right (corrected) source + correct label."
