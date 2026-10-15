# Risk register

| Risk | Consequence | Mitigation / stop rule |
|---|---|---|
| no D1-compatible prostate ground truth | historical primary cannot run | publish formal feasibility/no-go; do not force bulk/L1000 into native input |
| unknown model training overlap | false independent-test claim | block independent label; resolve lineage or use as development only |
| unknown-label/control fallback | control-like output misread as prediction | fail closed before upstream call |
| metric insensitive or dominated by common response | misleading model ranking | strong baselines, perturbation discrimination, positive controls/data ceiling |
| molecular-to-function nonidentifiability | arbitrary behaviour coefficients | measured-driver D2 first; staged calibration and ablation |
| pseudoreplication | invalid uncertainty | patient/donor/experiment as unit; cells nested |
| unqualified ICI axis | false negative/positive | receptor/ligand/blocking qualification and matched controls |
| residual drug toxicity | apparent immune killing | washout/recovery and tumour-only controls |
| unsupported compartment/state | fabricated TME claim | return `UNSUPPORTED`; add only with data |
| calibration/test reuse | optimistic validation | shared-experiment ledger and frozen split |
| D/E double modelling | duplicated scope and leakage | formal interface and ownership table |
| negative result suppressed | publication bias and scope drift | negative result completes evaluation; deployment claim restricted |
| licence ambiguity | unlawful redistribution | role-specific rights review and manifest-only sharing |
| compute overreach | irreproducible/unfinished work | staged CPU-first plan; explicit budget approval |
