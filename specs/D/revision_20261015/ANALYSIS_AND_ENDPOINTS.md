# Analysis and endpoints

## Controlling D1 primary — preserved exactly

Target population: the finite set of eligible, independently measured human prostate cell-context responses to checkpoint-supported chemical drug–dose labels at the compatible documented collection duration.

Let:

- `D` be the frozen eligible drug set;
- `C_d` the eligible condition set for drug `d`;
- `R_c` the independent biological replicate units for condition `c`;
- `G` the complete frozen ordered checkpoint output gene space;
- `delta_crg` the measured treated-minus-matched-control effect for replicate `r`, condition `c`, gene `g`, using equal biological-replicate weighting;
- `S_crg` the frozen model prediction using the exact matched control inputs;
- `K_c` the eligible non-test training contexts for the exact supported drug–dose–duration label;
- `B_cg` the equal-context mean measured response across `K_c` (the fixed same-supported-drug–dose–duration comparator).

For model `m` in `{B,S}`:

`L_m(cr) = (1/|G|) * sum_g (delta_crg - m_crg)^2`

The primary estimand is:

`theta = (1/|D|) * sum_d [ (1/|C_d|) * sum_c [ (1/|R_c|) * sum_r { L_B(cr) - L_S(cr) } ] ]`

Positive `theta` favours the model. Drugs receive equal weight, then conditions, then biological units; cell counts do not determine weights. Report both constituent losses. No test-derived feature selection, per-gene standardisation, inverse-variance weighting, nearest-dose substitution, or outcome-selected comparator may alter the primary.

If `K_c` is empty, the condition is blocked; it cannot silently switch comparator.

## D2-PAIR primary candidate — not yet frozen

Preferred endpoint: held-out **specific viable tumour loss or viable tumour count at the qualified assay timepoint**, with independent experiment/donor as the unit. Primary comparison: calibrated spatial model versus the prespecified nonspatial count/ODE baseline and minimal rule-only spatial baseline.

A D2 primary requires a dated amendment before confirmatory outcomes are inspected. The 48-hour endpoint in the current wet-lab protocol is a candidate, not proof that the assay is qualified.

## Secondary metrics

D1: perturbation discrimination, DE direction, programme/pathway error, calibration, distributional distance, failure coverage, and replicate positive-control/data-ceiling analysis.

D2: tumour-burden error, killing error, calibration, spatial contact/neighbourhood metrics, composition error, and interval coverage.

Global expression MSE alone is insufficient.
