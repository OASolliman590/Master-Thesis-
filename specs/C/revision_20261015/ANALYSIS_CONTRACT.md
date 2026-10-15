# Proposed primary and statistical analysis contract

## Status

This document develops the user-approved paired independent-measured `Q_M` versus `Q_E` endpoint. It is **proposed, not released for biological execution**. Query and source gates must close first.

## Primary estimand

For each admitted independent experiment, score the desired restored state for the matched queries in every biological sample using a full-universe directional rank score.

Let:

- `S_i(Q_M)` be the sample-level desired-state score for the methylation-supported query;
- `S_i(Q_E)` be the score for the matched expression-only query;
- `D_i = S_i(Q_M) - S_i(Q_E)`.

For source `s` and prespecified contrast `j`, fit the source-specific limma model:

`D ~ treatment + declared_covariates + declared_blocking_terms`.

The coefficient `delta[s,j]` for the treatment contrast is the primary contrast-level estimand.

### Interpretation

- `delta > 0`: treatment shifts `Q_M` further toward the desired state than `Q_E`.
- `delta = 0`: no relative methylation-query advantage.
- `delta < 0`: the expression-only query shifts further toward the desired state.

Always report the treatment effects for `S(Q_M)` and `S(Q_E)` separately. A positive difference does not count as restoration if both component effects move away from the desired state.

## Sample-level scoring

Primary sample-level scoring uses directional rank-based scoring equivalent to the prespecified `singscore` contract:

- rank the complete measured gene universe within each sample;
- score `desired_up` and `desired_down` genes with declared direction;
- normalise for query size according to the pinned implementation;
- compute programme scores first;
- combine common eligible programmes with equal weights;
- do not rerank only query genes.

The exact package version and numerical fixtures must be pinned before release. An independently implemented scorer requires parity.

## Query fairness and coverage

Within each source:

- `Q_M` and `Q_E` have identical programme/direction quotas;
- each query must have at least 80% measured coverage in every included programme-direction block;
- the absolute coverage difference between queries must not exceed 10 percentage points in a block;
- sources failing coverage are secondary or blocked;
- a common-measured-gene sensitivity is prespecified but may not replace the primary silently;
- absent genes remain absent; imputation from external expression is prohibited.

Coverage thresholds are design proposals to be confirmed outcome-blind during source admission.

## Experimental unit

The independent biological replicate, culture day, organoid, donor or declared experiment block is the inferential unit. Genes, cells, wells, technical replicates and collapsed signatures are not independent units.

Primary source admission requires at least three independent biological replicates/blocks per arm. Two-replicate studies may provide descriptive secondary evidence.

## Complex designs

- paired samples use the pairing/block in the design;
- repeated measures use a declared correlation/block model;
- shared-control contrasts are fitted jointly or supplied with a valid covariance matrix;
- technical replicates are collapsed before inference;
- combination arms are excluded from the primary unless the exact factorial contrast is separately registered;
- time courses require a declared response-by-time estimand and do not create independent studies per time point.

## Study-level aggregation

For study `s`, combine non-overlapping primary experiment blocks with equal prespecified block weights. Shared-control estimates require generalised least squares using the fitted covariance. The resulting `delta_s` is one original-study contribution.

The finite-set source-equal summary is:

`Delta_Q = mean_s(delta_s)`.

`Delta_Q` describes the admitted study collection. It is not a population-average drug effect, treatment-class effect, ICI-sensitisation effect or clinical benefit.

### Minimum evidence gate

- fewer than three independent originating studies: no confirmatory cross-study primary; report contrasts descriptively;
- three or four: report `Delta_Q`, study effects and leave-one-study-out range without a broad population claim;
- five or more: the same finite-set primary remains; a random-effects model may be a secondary sensitivity if heterogeneity is estimable.

## Multiplicity

There is one paper-level primary family: the paired `Delta_Q` comparison.

Secondary families are declared separately:

- programme-specific paired effects;
- mechanism-class strata;
- cell/model strata;
- C1 three-compound query-specificity analyses;
- candidate-specific independent validations;
- immune-context and functional endpoints.

Use Benjamini–Hochberg within each declared secondary family. No threshold is selected after seeing outcomes.

## Missingness

- missing genes are handled only through the coverage policy;
- missing sample metadata blocks admission until resolved;
- missing evidence in candidate integration is `UNKNOWN`, not zero;
- an unavailable source is not a negative experiment;
- no outcome-based complete-case selection.

## Sensitivity analyses

Prespecify before outcome access:

1. programme-specific `delta` effects;
2. common-measured-gene matched query sensitivity;
3. weighted versus unweighted query sensitivity if B supplies defensible weights;
4. one-sided versus bidirectional programme handling where biologically applicable;
5. exclusion of studies with only three replicates;
6. leave-one-study-out summaries;
7. alternate but frozen normalisation within each source.

## Claim ceiling

The primary can support a statement about **relative desired-direction molecular responsiveness of two frozen patient-derived queries in measured prostate perturbation experiments**. It cannot establish comparative drug efficacy, class superiority, immune killing, ICI synergy or clinical benefit.
