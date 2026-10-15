# Proposed single core estimand: the supported schedule-contrast set

This replaces the v1 primary prospective local surface-HLA prediction endpoint. That kinetic endpoint is reserved for E_LAST. The definition below is a design recommendation; compound, antibody, numerical schedule, horizon, context and margin still require a recorded scientific decision before fitting/ranking.

## Scientific target

For a prespecified epigenetic-first schedule A and concurrent schedule B, does the accessible evidence support a consistent difference in modelled tumour burden, or do equally admissible models predict different conclusions? No sequence is assumed best. Reverse/pulse schedules are secondary, not extra co-primary endpoints.

For context c, model structure m and parameters theta, let T_s(t;theta,m,c) be viable target tumour number (or a consistently defined model burden with a justified unit), T0>0 the common baseline, and H>0 the common global observation horizon. Define:

```
J_s(theta,m,c) = (1/H) * integral_0^H T_s(t;theta,m,c)/T0 dt
Delta(theta,m,c) = J_A(theta,m,c) - J_B(theta,m,c)
I_D(c) = {Delta(theta,m,c): (theta,m) satisfies the prespecified evidence and model contracts}
```

J and Delta are dimensionless. Negative Delta favours A on this **model-level burden endpoint**, not clinical response or survival. The single primary estimand is the identified/admissible set I_D for the frozen contrast and context. Report its components and extremes; an interval hull may hide disjoint regions and must be labelled accordingly.

No population expectation is silently added. A calibrated distribution-specific expectation is secondary and requires its own supported target population. Core set-based inference remains usable when population weights or correlations are not identified.

## Fair comparison

Both arms use the same documented agents, total administered amount per agent, number of administrations, global start/end accounting and observation horizon. Explicitly record epigenetic/antibody start times, pulse widths, washouts, drug-free intervals and prior history. If A uses a lead-in, the pre-antibody period counts in its tumour burden and exposure. No hidden negative-time dosing.

Dose matching is not proof of exposure matching. Compare AUC over the common horizon, peak/occupancy exposure and residual tail after H. If pharmacokinetics make equality impossible, call the contrast dose-matched, exposure-different and include a separately defined exposure-standardised sensitivity; never alter an arm's dose after seeing outcomes. Reject claimed pure sequence comparisons with unresolved dose/duration differences.

## Evidence-set construction

Build from original-study-resolved public observations and explicit prior/hypothesis strata. Use a source-appropriate likelihood region or documented measurement/summary-error constraints; do not invent SD or certainty. Fit/no-fit criteria, tolerances, source weights and alternative structures are frozen before schedule comparison. The set includes plausible adverse immune effects and no-priming alternatives when not ruled out by evidence. An empty set is incompatibility, not efficacy. Unknown bounds stay unresolved or mathematically unbounded.

Under C-SCHEDULING, use actual temporal/function evidence to constrain the set. Under C-IDENTIFIABILITY, prove or quantify which contrast values remain compatible with available measurements. Nonidentifiable parameters do not automatically mean a nonidentifiable schedule contrast: that implication must be tested for this estimand.

## Decision interpretation

A strictly negative certified upper bound supports A only within the stated model/evidence domain; a strictly positive lower bound supports B. An interval containing zero supports no robust direction at that resolution. A practical-equivalence margin epsilon is a separately justified, predeclared model-scale tolerance; without it, do not claim biological equivalence from a nonsignificant contrast.

Finite multistart searches supply sampled extrema, not certified global bounds. Report optimization gaps, unsearched structures, solver error and sensitivity to prior bounds. Unless a global envelope is proved, use 'robust within the examined domain', not 'robust for all admissible models'. Confidence/credible intervals and deterministic feasible sets must not be conflated.

## Analysis and missingness

Biological units remain those in original public studies; simulated members/timepoints are not independent patients and do not generate biological p-values. Missing measurements remain missing; public-source exclusions are recorded before outcome modelling. Never impute a missing schedule arm as its model prediction and then validate against it. Independent public predictions and observed values are reported at their original assay scale, with source-level uncertainty.

A failed primary contrast remains a result. Changing endpoint, context or schedules after inspecting model outcomes requires a new version and retains the old analysis. No original-data availability affects core eligibility or conclusion.
