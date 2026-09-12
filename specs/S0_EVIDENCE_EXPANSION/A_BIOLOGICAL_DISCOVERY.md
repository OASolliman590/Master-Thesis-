# A — Two separate products: biological evidence and prediction

**Proposed extension.** The selected A-P2 and existing final-test contrast in `../A/DISCOVERY.md` remain unchanged. This document does not create a second confirmatory paper-wide primary. Biological analyses are a prespecified discovery family until an explicit statistical release classifies their inferential status.

## Aim

Identify reproducible pretreatment immune-expression programmes associated with objective response to immune checkpoint inhibitors across independent cohorts; assess their predictive and biological transferability; and provide a prespecified clinical reference for investigating prostate immune deficits and epigenetic restoration.

## Product 1: response-associated biological effects

The unit is the eligible baseline patient, one outcome-independent selected specimen per patient under the source rule. CR/PR versus SD/PD is the existing ORR mapping, only where supported by original definitions. Different clinical outcomes remain separate. Non-ICI arms are not silently admitted as ICI cohorts.

Within each originating study and compatible treatment context, estimate gene/programme response associations using the actual measurement route. A generic transformed-expression model is:

`expression_g = intercept + beta_g * responder + predeclared baseline covariates + error`.

Count data instead use the corresponding count model with its source-appropriate normalization/offset. Covariates are selected from clinical/technical reasoning and availability, not univariate significance. Preserve adjustment set IDs; estimates targeting materially different conditioning sets must not be silently pooled. Small or rank-deficient strata are reported nonestimable; no forced multivariable fit.

Output every tested gene with canonical ID, effect, SE/interval, scale, sample counts, covariate set, estimability, original study and measurement provenance. Keep shrinkage estimates for presentation separate from the sampling estimate/SE used for inverse-variance synthesis. No SE back-calculation from a rounded or zero adjusted P-value.

### Synthesis contract

First synthesize within cancer and compatible regimen/endpoint/assay scale. Then examine cross-cancer transfer and heterogeneity. A possible reviewed model is `beta_gj ~ Normal(mu_g, se_gj^2 + tau_g^2)`, with REML heterogeneity estimation and an appropriately justified small-sample interval. Exact inference rules, minimum independent study support and fallback behaviour must be frozen before results; this kit does not invent a powered minimum N.

Do not combine log2(TPM+1) differences, count-model logFC, microarray intensity effects, standardized effects or protein NPX differences as one unlabeled quantity. Prefer assay-stratified effect synthesis; a standardized/rank-based cross-assay sensitivity needs its own estimand. Study-level P-value aggregation alone does not preserve direction or biological effect size.

Report study/cancer effect estimates, direction consistency, heterogeneity and influence; prediction intervals only where their estimation is defensible. A summary across a finite sampled collection is not a universal effect in all cancers. Independent originating studies, not accession count, support replication. A non-significant heterogeneity test is not proof of a shared effect.

Freeze feature universes, programme definitions, response contrasts and multiplicity families. Proposed control: BH FDR within the complete declared baseline gene-discovery family and separately within the declared programme family. Keep unestimable tests and reasons visible; implement any fixed-family placeholder policy explicitly, never as fabricated biological P-values. Selection on published significant genes alone is prohibited. Exploratory cancer/regimen subgroups remain labelled and fully reported.

### Programmes and cellular interpretation

Use source-defined gene sets with versions and full membership. Outcome-discovered modules, network construction and enrichment belong inside development data; freeze any learned weights before test access. Report the enrichment background, assay coverage and input-gene overlaps. Distinguish immune recruitment, antigen processing/presentation, IFN response, cytotoxicity and suppressive programmes without requiring every canonical programme to appear.

Link each gene/programme to measured cellular localization where available. A marker of immune-cell abundance may be a valid clinical association without being a tumour-cell drug target. The composition and spatial modules are specified in `CELLULAR_SPATIAL.md`; adjustment is a sensitivity under stated assumptions, not a test that automatically proves cellular causality.

## Product 2: locked pretreatment prediction

Retain the existing cohort-held-out nested elastic-net design and A-P2 paired independent-test AUROC comparison with CYT. Before implementation, use the expanded roster to verify the actual development/inner/outer/final-test structure and precision. Source expansion does not relax the final-test exposure policy.

All feature filtering, learned programme construction, imputation, scaling, tuning, thresholding and feature selection that affect prediction must be training-only. Every timepoint/lesion/cell from a reserved patient or overlapping originating study stays out of development. Published atlas response-DEGs derived from test patients may not choose the model's features.

Proposed supporting comparators: source-correct IFN-gamma/T-cell-inflamed GEP, an eligible local TIDE implementation and a current method such as COMPASS after availability, feature representation and training-overlap audit. They are proposed comparators, not fabricated executed benchmarks. Preserve CYT as the selected anchor. Compare on identical eligible test patients and show coverage; do not compare scores evaluated on different convenient subsets. [R11, R12]

AUC(f)-AUC(CYT) establishes discrimination relative to CYT. A model adding features to a CYT model would answer a different conditional incremental-information question and needs its own analysis specification. Calibration and clinical utility require separate support; high discrimination is not an ICI-versus-control treatment benefit.

## Development-only handoff to B/C

Export separate tables:

- `response_effects`: gene/programme association direction, uncertainty, cancer/regimen support, adjustment, coverage and heterogeneity.
- `frozen_predictor`: features, coefficients, scalers, score definition, version and training IDs.
- `biological_context`: immune function, cellular evidence, assay/source overlap and unresolved interpretation.
- `longitudinal_support`: development-only associations from A.1, with timepoint and selection limitations.

A gene's differential-expression direction is not the sign of its penalized coefficient. Neither is automatically the desired pharmacological perturbation direction. The clinical-reference handoff is frozen before final-test inspection. Independent-test results are attached as validation annotations, not used to rewrite the handoff. If a later discovery uses previously reserved data, it receives a new exploratory version and must not retroactively claim the previous test remains untouched.

## Readiness and figures

Source admission plus the exact statistical analysis plan must precede real fitting. Four-figure intent: (1) sources, pairing and cohort splits; (2) baseline gene/programme effects, context and replication; (3) frozen prediction/comparators and endpoint sensitivity; (4) qualified cellular/prostate handoff. A.1 may be a linked additional module rather than forcing every analysis into crowded panels. Final figure ownership must prevent duplicate publication of the same result.

Reference basis: processed-count and limma methods [R1,R2]; established immune prediction [R11,R12]; source and claim limits in the existing A specification. Numerical choices above are proposed study-design decisions, not findings from those references.
