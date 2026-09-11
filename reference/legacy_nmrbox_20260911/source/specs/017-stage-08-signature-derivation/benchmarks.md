# Benchmarks: Spec 017 — Stage 08 Signature Derivation

## Baseline

Measure after selecting the current corrected run root.

| metric | command | baseline |
|---|---|---|
| signature derivation wall time | `python -m pipeline.cli signature derive ...` | TBD |
| rows in corrected meta table | inspect selected run root | TBD |
| eligible `analysis_id` count | inspect contrast registry | TBD |
| Tier 1/Tier 2/Tier 3 gene counts | derive with frozen thresholds | TBD |
| LOCO folds emitted | derive with LOCO enabled | TBD |

## Regression budget

- Signature derivation should remain lightweight relative to DE/meta-analysis.
- Thresholding must be deterministic for a fixed input table and config.
- Adding LOCO manifests may increase output size but should not rerun Stage 06/07 by default.

## Correctness validation

- A mixed-scale meta fixture must block with a clear error or blocked audit.
- A fixture with known FDR/effect/cohort-count values must assign tiers deterministically.
- Every emitted row must include `analysis_id`, `effect_scale`, `evidence_tier`, `module_id`, and `run_root`.
- Same-sample concordance labels must remain internal robustness labels, never external validation labels.
