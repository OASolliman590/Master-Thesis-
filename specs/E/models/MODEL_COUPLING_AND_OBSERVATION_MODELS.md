# Coupling, observations, events and numerical contract
> **v2 operating contract:** Core numerical evidence is external public evidence. References to culture, assay, donor or experimental data below mean source-attributed published measurements in core, not a requirement to generate local data. Original project integration is exclusively E_LAST after core release. Core profiles and release gates are defined in CORE_COMPLETION_CONTRACT, not legacy D01–D14 labels. Technical observation/identity restrictions apply unchanged.


## Module interfaces

`ExposureTrajectory`: context/analyte/matrix/binding basis, time unit, concentration unit, draw IDs, events, source/run hashes and uncertainty class. `PDStateTrajectory`: measured or latent state names/units, reference normalization, context and matching draw IDs. `InteractionTrajectory`: target/effector counts, function/checkpoint states, actual volume and observation map. `PopulationOutput`: parameter-draw lineage, weights, scenarios and model-structure ID. Reject incompatible units/context rather than silently converting.

E1→E2 exports uncertainty draws preserving correlations and source dependencies. E2→E3 exports predictions and parameter uncertainty separately from between-unit variability. A single shared source parameter must not be independently resampled in each module. Source-curve and source-summary dependencies are retained.

## Assay-specific observation functions

**qPCR:** retain raw Cq/Ct, target/reference assays, efficiency evidence, detection limits and technical repeats. Under validated equal doubling efficiencies, log2 relative expression corresponds to negative delta-delta Cq; otherwise use the justified efficiency-specific transformation. Reference stability is a qualification criterion. Model raw/normalized log scale with propagated target/reference and shared-control covariance, not arbitrary fold change as absolute concentration. Undetected targets are censored/missing under a prespecified assay rule, not assigned an invented Ct.

**Flow:** preserve FCS where permitted, gating version, compensation, laser/filter/settings, viability and tumour/immune gates, event counts and calibration controls. Median/mean fluorescence and transformed summaries are distinct. A compatible public observation may use a log2 positive qualified surface-HLA fluorescence ratio to its matched vehicle/bridge reference; this is not the v2 core primary. The optional E_LAST kinetic primary may use this scale only after separate qualification. No copies/cell claim. Add batch/run effects and reference covariance. Percent-positive data require gate/denominator and an overdispersed binomial or suitable fraction model; absolute counts require counting calibration and sampled volume.

**Western:** retain images, unsaturated range, loading/total reference, quantification and batch. A log normalized intensity can map to relative protein P with an assay scale/batch term; densitometry is not molar concentration. Saturation or missing bands is not a zero-protein observation without a validated limit.

**Secreted factors:** observed concentration equals amount/actual volume with assay error. To model secretion, use an amount balance including production per relevant viable cell, loss/consumption, sampling removal and dilution. Concentration alone does not identify a secretion rate.

**Function:** viable target counts can use a Poisson/negative-binomial or other qualified count likelihood with sampled-fraction correction; choose overdispersion from evidence. Death fractions require a valid target denominator and dependence/overdispersion. Mixed LDH/metabolic signals need a qualified multi-population observation function or remain contextual; never label them target count. Cytostasis, death and effector viability have separate observables.

**PK/engagement summaries:** map exact analyte/statistic/scale. Individual lognormal concentration error is not automatically a likelihood for aggregate mean profiles. Unknown SD/SE/N remains unknown with sensitivity, not fabricated precision. Fitted/predicted source curves support reconstruction, not independent biology.


## Concrete likelihood candidates and admissibility

For an individual positive PK measurement, `log(y) ~ Normal(log(Cpred), sigma_log^2)` is a candidate; a below-quantification contribution is `Pr(y<L)=Phi((log(L)-log(Cpred))/sigma_log)` only under that selected error model and valid limit. An additive-plus-proportional alternative is evaluated when supported. This likelihood is not automatically used for a reported group mean.

For known arithmetic sampling SD s and independent biological N, an aggregate mean can use `ybar ~ Normal(mu, s^2/N)` under the corresponding assumptions; with a reported SE use SE^2, not another division by N. Unknown SD/SE/N remains unresolved. Geometric means and correlated repeated aggregate measurements require their actual transformed statistic/covariance or declared sensitivity, not this formula by default.

For qPCR normalized log2 response z, a candidate is `z ~ Normal(log2(M)+b_run+b_batch, Sigma_qPCR)` with reference/technical covariance propagated. For qualified surface fluorescence ratios, `z ~ Normal(log2(P)+b_batch, Sigma_flow)`. For Western log ratios, `z ~ Normal(log(P)+b_batch, Sigma_WB)`. Normalization constants and offsets are fixed from assay qualification, not chosen to make negative/background signals loggable.

Target counts can use `Y ~ NegBin(mu=qsample*T, dispersion=k)` with variance `mu+mu^2/k` when overdispersion is supported; qsample is a measured sampling/counting fraction. Fractions can use an appropriately clustered binomial/beta-binomial likelihood with the actual denominator. Counted cells/events are measurements nested within biological runs, not independent biological replicates. Secreted concentration maps to the predicted amount/volume with its qualified assay likelihood and censoring limits.

## Events and initial conditions

Piecewise integration stops at every dose/infusion boundary, medium change, washout, cell addition/removal and sampling event. Store pre/post-event ordering explicitly for coincident measurements. Medium replacement uses documented retained fraction rho and volume; rho=0 only if justified. Do not hide washout by resetting the PD state. Repeated sampling changes volume/amount when material is removed. Initial values derive from baseline/previous dosing or a justified steady state; normalize only on the declared assay scale.

## Solver and numerical validation

Canonical new engine candidate is SciPy solve_ivp, with stiff methods BDF/Radau evaluated for the released structure (O11). Select tolerances after state scaling; a proposed starting numerical test configuration is rtol=1e-6 with state-specific atol, but it is not a frozen biological setting. Tighten tolerances and refine event handling until changes are negligible relative to the prespecified observation/prediction precision. Record solver/version/method/tolerances/Jacobian/max-step/events/status.

Test positivity, fractional bounds, mass balance where applicable, zero-dose/no-effector/no-ligand limits, exact bolus/infusion/washout timing, conservation across volume changes and upstream parity. Never “fix” negative states by clipping without investigating equations/numerics. Solver success is not model validity. These production ODE/parity tests are specified for later packets, not claimed executed by the contract-only checks in this draft.
