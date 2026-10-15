# Three ensemble types, not one generic virtual patient label

**Supported virtual population:** parameterisations/weights calibrated to source-defined distribution targets with sampling/context information and held-out checks. Report which target margins/joints are reproduced and which remain unknown.

**Plausible parameter ensemble:** parameterisations compatible with measured constraints plus explicit assumptions. Its sample frequency is a computational design choice; it is not population prevalence.

**Set-valued uncertainty analysis:** all parameterisations/model structures satisfying specified constraints. A numerical sample approximates this set without defining a probability measure. This type underpins the primary estimand when weights are not identified.

## Workflow

1. Freeze target sources, statistics, scales, biological N and roles. Do not create individuals from public group means.
2. Declare parameter support/physiological constraints and known dependencies; separate aleatory population variability from epistemic uncertainty. Independent uniforms are assumptions, not a default patient distribution.
3. Build a candidate ensemble from the admissible region; log rejection causes, proposal design and parameter transformations.
4. For genuine population calibration, use a declared acceptance/weighting method and evaluate held-out targets. Nonnegative weights sum to one; `ESS=(sum w)^2/sum(w^2)`. Low ESS, extrapolating members and missing target coverage are reported, not fixed by cloning trajectories.
5. When only marginal targets exist, evaluate alternative plausible joint distributions/correlations and publish the effect on schedule conclusions. Their probabilities remain unsupported unless estimated from actual data.
6. Evaluate paired schedules on the same parameter members; hold out ensembles/alternative structures from optimisation. More virtual members reduce numerical Monte Carlo error, not biological uncertainty.

Core E3 is complete when the appropriate ensemble/set analysis is finished and honestly labelled. It does not require that a representative human population can be identified. In C-IDENTIFIABILITY, unresolved distributional assumptions are part of the result. Donor/culture variability in E_LAST can inform experimental populations, never automatically a human patient population.

No virtual N replaces original biological N. No modelled tumour size becomes ORR/PFS/OS without a validated endpoint mapping. Calibration to published survival summaries would require additional censoring/dropout/clinical contracts and is outside the initial core.
