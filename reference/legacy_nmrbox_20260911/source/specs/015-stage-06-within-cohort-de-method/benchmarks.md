# Benchmarks: Spec 015 — Stage 06 Within-Cohort DE

## Baseline (measure at M2)
| metric | command | baseline |
|---|---|---|
| DE wall time (21 PRE cohorts) | `time python -m pipeline.cli de run --contrast PRE_RESPONSE ...` | TBD |
| per-cohort peak RSS | `/usr/bin/time -l` on the largest cohort (gse218989, 355 samples) | TBD |
| n cohorts on Welch path (to be eliminated) | count `model_class==welch_t_test_log2` in current DE outputs | ~14 (est) |

## Regression budget
- Moderated limma adds an R subprocess per non-count cohort: **≤ +30%** DE wall time acceptable (R startup dominates small cohorts; batch where possible).
- Numerical: for verified-count cohorts the DESeq2 path is unchanged → results MUST be byte-identical to baseline (no regression).
- For migrated (Welch→limma) cohorts: results WILL change — quantify in the migration report, not a regression failure.

## Correctness validation (the real bar)
- **Simulated dataset** with known per-gene effect + known noise: limma/DESeq2 SEs must recover the true SE within tolerance; Welch SE demonstrably wrong at small n. This is the test that justifies the method change.
- Cross-check a count cohort run through both VST→limma-trend and DESeq2 — directions concordant, effect magnitudes correlated (r>0.9 on top genes).

## Measurement procedure
```
# baseline
grep -l welch_t_test_log2 results/<run>/PRE_RESPONSE/*.tsv | wc -l
time python -m pipeline.cli de run --contrast PRE_RESPONSE <args>
# post: confirm count-cohort byte-identity, capture migration delta
```
