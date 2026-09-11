# Paper B — immune deficits, epigenetic evidence and composition

Controlling scope amendment: [A/B reconciliation](../../docs/decisions/AB_IMMUNE_BARRIERS_20260911.md). User-approved scientific direction; no new real-data analysis release.

## Aim and evidence architecture

Which clinically relevant immune functions are deficient in defined prostate tumour contexts, which deficits have reproducible epigenetic correlates, and which candidates warrant restoration testing? The patient-data study nominates potentially reversible barriers; reversibility requires perturbation evidence and functional/clinical utility requires further validation.

| Component | Data and comparison | Required output / limit |
|---|---|---|
| Clinical reference from A | Frozen discovery product and source-correct fixed signatures; pretreatment ICI cohorts | Response-association/stability evidence; no prostate response probabilities without validation |
| Prostate immune deficits | Qualified TCGA/CPC/independent prostate expression; within-prostate contrasts; qualified LUAD secondary | Program-specific expression and coverage with effect/uncertainty under frozen scale/contrast; lineage differences do not prove immune barriers |
| Epigenetic associations | Paired promoter methylation/RNA; source-backed chromatin/domain context where available | Direction-preserving associations with prespecified adjustment; negative associations alone do not prove silencing |
| Fixed APM transport module | Existing TCGA-trained/CPC-frozen baseline versus extended model | B-P external Delta_R2, paired errors and uncertainty; supports molecular prediction, not causal drug response |
| Alternative explanations | Composition, purity, available genetic/CNA context and disease/treatment metadata | Sensitivity results, unsupported/missing evidence explicitly retained |
| B-to-C nomination | Separately frozen TCGA-only discovery rule and source evidence | Candidate genes/functions, sign, uncertainty, assay/cellular context, alternative explanations; no CPC-driven feature selection |

Retain one primary eight-gene APM proposal, three planned secondaries (Ayers, full IFNG Hallmark, HOPE), M0-M6 and the broader approved-immunotherapy target evidence panel. No automatic all-positive composite. HOPE's prognostic origin is not ICI-response validation. A-derived discovered genes are a separate versioned product, not an automatic expansion of P.

Each broader analysis requires a machine-readable contract before execution: source/version/hash, cell/disease context, membership, signs/weights, scale, comparison, covariates, missingness, effect/uncertainty method, multiple-testing family and validation dataset. No new numerical thresholds, primary endpoint or score is selected by this amendment. Source feasibility work may proceed immediately.

## MethylCIBERSORT placement and implementation contract

Status: named composition sensitivity, not yet implemented or fully source-qualified. W3 supplies specimen-linked methylation; W4 prepares independently specified composition estimates; W8 runs sensitivity comparisons; W7 plots them. W5/W6's current primary baseline remains unchanged.

1. Verify the official implementation, version/license/access, reference matrix and its supported cell types. Verify prostate-context suitability and required probes/build/platform overlap; a tool name alone does not establish an executable reference.
2. Pin all permitted source/reference bytes, input units and preprocessing. Separate assay QC from outcome-driven selection. A fixed external reference can be applied per sample; any learned preprocessing/reference construction must exclude held-out patients.
3. Emit one specimen-linked fraction table with cell type, estimate, reference, quality flags and missing/unsupported categories. Do not assume a fraction identifies functional state or spatial exclusion. Do not invent absent cell classes.
4. Compare relevant expression patterns with composition estimates and, where independently supported, alternative measurements. Check overlap between deconvolution CpGs and promoter predictors and disclose shared-assay dependence.
5. Run separately specified composition-adjusted association/prediction sensitivities on clearly reported patient populations. Do not silently substitute these fractions for the frozen primary purity measure. Fractions are compositional; the eventual statistical contract must address collinearity/constraints, not include every fraction plus an intercept indiscriminately.
6. Report unadjusted and adjusted evidence without interpreting attenuation as proof of confounding or persistence as proof of tumour-cell causality. Composition may also be downstream of tumour signalling. State the causal assumptions and uncertainty.

These estimates help distinguish 'few relevant cells' from other explanations of weak bulk expression. They cannot establish tumour-cell intrinsic repression; malignant-cell data and perturbations remain separate evidence. See [original method](https://www.nature.com/articles/s41467-018-05570-1).

## Revised four-figure scientific outline

1. Cohort/assay coverage and clinically anchored immune-function map, distinguishing A-derived and predefined programs.
2. Prostate program deficits and epigenetic associations, with cellular composition and other supported alternatives; no universal hot/cold label inferred from one score.
3. Fixed APM model validation: internal development and independent external Delta_R2 with uncertainty. These are separate evidence panels, never pooled cohorts.
4. Candidate barrier evidence table/plot for C: clinical association, prostate deficit, epigenetic context, composition sensitivity and validation strength. Preserve missing and contradictory evidence; no invented composite ranking.

Every graph retains the plain-language explanation and source-table requirements. W7 may generate a partial report for the completed APM module, but must not label this entire scientific figure plan complete while other contracts/data are unavailable.
