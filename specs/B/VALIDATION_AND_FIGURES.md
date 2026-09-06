# B validation and four-figure evidence plan

**Primary decision, 6 September 2026:** B-P external prediction improvement is selected. The paired CPC-GENE Delta_R2 below is the single primary; B-R is historical and cannot replace a null result without an explicit amendment. Program/U/Q, eligibility, purity comparability and precision remain open gates. [Decision record](../../docs/decisions/B_PRIMARY_BP_20260906.md).

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** This is an evidence requirement, not a report of successful validation. ANALYSIS.md controls the estimand and transforms.

## Validation boundaries

TCGA is the sole fitting/tuning domain. CPC-GENE is one external cohort, not 210 independent studies. The external target population is the source-backed paired specimen population with complete approved baseline variables; its eventual definition and representativeness must be settled without examining prediction errors. The current 73 clinical code candidates are not yet confirmed matched specimens. No result across these cohorts alone establishes transport to metastatic disease, ICI-treated patients or other assay technologies.

Assign all samples/reanalyses from a patient to one development fold. Five-by-five nested CV estimates development performance; its repetitions or folds are not independent clinical cohorts. Feature missingness selection, scaling, zero-variance handling and alpha tuning must be refitted within each applicable training fold. Eligibility affected by fitted probe coverage is recorded by fold, and f0/f1 always share the same validation patients. Final probe sets, mappings, coefficients, alpha values and transform statistics are frozen on TCGA before external error evaluation.

Permitted external inspection before lock: accession provenance, sample identities, assay annotations, gene/probe existence, missingness and covariate availability needed for a predeclared eligibility mask. Prohibited: using external endpoint values, outcome distributions, correlations, prediction errors or subset performance to select features, transformations or primary population. Such metadata access is logged; external expression file access is distinguishable from computing/analyzing its endpoint. Independent reviewer approval of the frozen artifacts precedes the first external evaluation.

Primary validation is the paired external Delta_R2 in ANALYSIS.md, with both individual R2 values, paired SSEs, SST, n and the fixed-model paired-bootstrap interval reported. Do not replace a negative primary result with a better secondary score. Calibration plots are diagnostic; their fitted slopes/intercepts do not recalibrate reported predictions. Platform-specific performance and covariate overlap are descriptive with intervals, not alternative primary tests.

## Mechanistic and transport checks

- Comparable non-RNA purity and age/grade adjustment support a limited incremental-information claim. Gene-level CNA, immune/stromal composition and processing differences remain alternative explanations; ploidy is not locus-specific copy number. Include CNA sensitivity only with a verified same-specimen source, and label the changed eligible population.
- Evaluate positive and negative promoter associations; assess domain annotations separately. [Guo et al.](https://doi.org/10.1016/j.cell.2023.05.028) supplies a prostate hypomethylation/repression counterexample. It prevents a universal “more methylation means less expression” narrative; it does not dictate the sign of this proposed eight-gene predictor.
- Malignant-cell versus immune-cell expression localisation requires an independently identified prostate reference and cell annotation provenance. RNA cell-origin evidence does not establish methylation in the same cell or the effect of a drug. This source is currently unspecified; mark the claim unavailable if it cannot be verified.
- The within-sample rank scale must undergo an outcome-independent annotation/mapping audit and a documented transport argument. [Foroutan et al.](https://doi.org/10.1186/s12859-018-2435-4) supports sample-wise scoring, not proof that this custom module has equal measurement properties in RNA-seq and these two arrays. A different scale requires a pre-test amendment.
- PRAD/LUAD is secondary and explicitly combines tissue-lineage and immune-state differences. It cannot validate prostate ICI response. Preserve within-PRAD analyses as a separate contrast rather than calling concordance a causal control.

## Four required figures

| Figure | Required panels and unit | Scientific evidence / stopping implication |
|---|---|---|
| 1. Cohort and assay accountability | Patient flow from metadata counts to paired eligible cases; specimen/reanalysis graph; gene/probe and covariate coverage by platform; source-backed overlap exclusions. Unit: patient, with sample counts separately labelled. | Demonstrates genuine external independence and what n means. Unresolved focus pairing or missing program coverage blocks the primary analysis; the figure must never use 497/210 as final n. |
| 2. Molecular signal and competing explanations | TCGA program distributions on the fixed scale; signed promoter–expression associations with intervals/FDR; non-RNA purity and available CNA/composition sensitivities; domain annotation counterexamples. Unit: patient; gene/probe summaries identify multiplicity families. | Establishes what is associated with the program, with both directions visible. Bulk associations alone cannot support tumour-cell silencing. |
| 3. Locked external incremental prediction | Paired external predictions for f0/f1, observed versus predicted on identical axes; Delta_R2 and its interval, individual R2/SSE/SST/n; diagnostic calibration and platform/covariate support. Unit: independent external patient. | Carries the one primary result, including a null/negative result. No external tuning, favourable subset selection or replacing R2 with correlation. |
| 4. Thesis bridge and limits | Secondary within-PRAD versus PRAD/LUAD signed results; independently sourced cell-origin evidence if available; frozen TCGA-only B-to-C query with direction/provenance and non-overlap with external selection. | Shows the drug-prioritisation input and scope ceiling. Missing orthogonal data are a visible gap; C drug ranks are not substituted for B patient validation. |

All panels must be reproducible from exported patient-safe result tables and a manifest; no illustration may imply ICI clinical benefit. If optional sources fail, narrow panels and claims through an amendment instead of manufacturing substitutes.
