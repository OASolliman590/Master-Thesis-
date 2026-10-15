# Scientific aim, estimands and claim ceiling

## Population and experimental unit

The target is the finite set of independently admitted ICI-treated study populations with an eligible pretreatment tumour transcriptome and source-supported objective-response endpoint for the same index treatment episode. The experimental unit is the patient, not a sequencing column, lesion, publication or accession. Scope is retrospective association/discrimination; transport beyond the frozen collection requires separate evidence.

## A-P2: selected primary

For test study j, d_j = AUC_j(frozen learned score, ORR) - AUC_j(fixed CYT, ORR), with identical eligible patients and direction fixed before evaluation. If K cancers and m_c studies in cancer c are frozen, D = sum_c (1/K) sum_{j in c}(1/m_c)d_j. This defines a finite-study estimand, not an inverse-variance random-effects treatment effect. Both component AUROCs and d_j are reported; conditional uncertainty is described in PREDICTION_ANALYSIS.md. No favourable threshold is required.

## A-BIO: distinct secondary evidence product

For each assay-compatible study and gene/programme, estimate the pretreatment difference associated with observed ORR, retaining response definition, adjustment set, effect scale, SE/interval, N, context and estimability. Compatible-context synthesis tests reproducibility; inconsistent effects remain visible. The scientific question is not 'which nonzero elastic-net coefficients are mechanisms'.

## A-P1: secondary endpoint sensitivity

For fixed CYT and identical category-evaluable patients, delta_j = AUC_j(CYT,DCR) - AUC_j(CYT,ORR). A single independently evaluated frozen learned score may be added. The contrast holds the score fixed; endpoint-specific refitting would answer another question. Category composition is reported alongside the difference.

## Secondary/exploratory structure

Programme effects and context-specific biological synthesis are prespecified secondary analyses. Additional published comparators, composition sensitivity, matched modalities and qualified prostate characterization are separately labelled supporting analyses. Clinical covariates and calibration are conditional, not default extra primaries. A1 analyses have their own contrast registry and do not alter the A-P2 feature set after final-test access.

## Permitted and prohibited conclusions

Permitted: a programme is associated with response in specified contexts; a frozen model discriminates observed response with stated uncertainty; cross-study direction is consistent or contradictory; a prostate tumour shares a molecular state. Prohibited: ICI causes a programme change from a single-arm response comparison; a model coefficient is a causal target; untreated TCGA has observed ICI response; drug class is superior because molecular R/NR separation is larger; an expression–methylation association proves tumour-intrinsic silencing. A null A-P2 leaves valid A-BIO intact. A nonestimable A-P2 is reported as such, not replaced by the most favourable secondary.
