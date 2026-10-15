# Separate development from evaluation

Each admitted object receives exactly one role for the current version: qualification, calibration, model selection, independent retrospective evaluation, prospective validation or contextual corroboration. Shared experiment/donor groups are handled consistently with the intended generalisation. Never split technical wells across these roles to manufacture independence.

## Retrospective data

When observations already exist or have been seen, they may calibrate a new version or support a genuinely unused held-out evaluation with transparent exposure history. A later timestamped model does not make existing observed outcomes prospective. All post-update conclusions identify the updated version; do not rewrite the frozen foundation.

## Proposed prospective kinetic primary

When compatible surface-HLA induction/recovery data and an independent future challenge are feasible, retain the v1 candidate:

```
d_j = sum_t w_t * [(Y_jt - prediction_baseline_jt)^2 - (Y_jt - prediction_dynamic_jt)^2]
Delta_PE = mean_over_independent_runs(d_j)
```

Y is the qualified assay-scale log2 positive fluorescence ratio to its matched reference, not receptor density. j is an independent culture preparation/run; donor structure is included when applicable. Weights/time grid, baseline conditioning, technical aggregation, comparator tuning, missingness, primary margin and uncertainty method are frozen before outcomes. A paired run-level/hierarchical analysis respects shared controls. Positive relative improvement alone is not adequacy: predeclare absolute-error and uncertainty-coverage checks.

This primary is **conditional and not approved by default**. If the actual data cannot support it, choose one other assay/functional estimand through a documented pre-outcome decision, or use descriptive/development-only analysis. Do not create multiple co-primary endpoints to avoid choosing. A prespecified functional schedule endpoint may instead be the single primary for an explicitly approved functional-only branch, not a post-result swap.

## New-version update

If model updating is needed, first report the frozen prediction-versus-observation result. Then fit the new version with a new role ledger and identifiability audit. Previously evaluated observations become development evidence for that new version. A new prospective validation claim requires another independent future challenge.

The extension endpoint tests the local measurement context. It does not retrospectively change the core's schedule-contrast primary, and it does not validate human tumour delivery or clinical benefit.
