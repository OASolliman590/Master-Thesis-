# Prostate immune state, TCGA response-profile analysis and randomised evidence (signed 5 Nov 2026)

**Status: SIGNED by the user on 5 Nov 2026 ("sign it"), draft 2, all four parts.** Signing releases no analysis: see "Rules for all parts". The user asked on 5 Nov 2026 to add the prostate immune-state analysis, expanded to all stages of the immune response and all cell types, to look for predisposed responders and non-responders among treatment-naive TCGA patients, and asked whether a better way exists to address causality in Paper A. Each part can be withdrawn alone.

Draft 2 takes in the Astra review of draft 1 (`work_notes/coordinator_20261103/amendment_0511_review/final.txt`, outside Git). Astra's recommendation: sign Parts 1, 2 and 4 after fixes; drop Part 3. The user signed Part 3 with the others, against that recommendation; it stays gated and is the first budget cut.

**What has been seen.** No association with response has been computed. Prostate single-cell QC, labels, compartment tables and pseudobulk exist under `results/B/sc_prostate`; their counts have been seen, but no stage result below has been analysed. TCGA and CPC-GENE are not loaded.

All thresholds and hours below are proposals by the coordinator, not values from a published source.

## Rules for all parts

**Signing does not release an analysis.** Each part needs its own release checklist, signed before its first outcome-linked step. The checklist fixes population, measurement, feature selection, estimand, covariates, missingness, multiplicity and reporting. Paper A's open gates (prior exposure, AIU verification) and Paper B's measurement gates still apply.

**Three levels of data access are kept apart:**
1. **Source audit (allowed now):** field names, definitions, availability, arm and specimen provenance.
2. **Aggregate class counts (allowed, recorded):** counting response classes reads response values, so each such count is logged as exposure in `DEVIATIONS.md` or the part's checklist.
3. **Feature–outcome summaries (forbidden before release):** any plot, table or test that joins a score, gene or methylation value with response.

**Precedence.** SC-3 was reinstated on 3 Nov, so older text saying it is cut no longer controls. SC-2, spatial work and single-cell A.1 stay excluded. No part here needs them.

## Part 1. B-STATE: prostate immune context across the cancer-immunity cycle (Paper B, descriptive)

**Question.** In untreated prostate tumours, what do cell shares and expression show at each stage of the anti-tumour immune response, in all cell types and not T cells only?

**Role.** A descriptive atlas organised by the stages of the cancer-immunity cycle (Chen and Mellman 2013). It does not locate where the cycle fails. RNA gives context for a stage; it does not measure the stage itself.

| Stage | Cells read | What is reported | Status of the stage itself |
| --- | --- | --- | --- |
| 1. Antigen release | Luminal/malignant epithelial | Innate-sensing and interferon expression (M3_VIRAL_MIMICRY). TCGA-PRAD mutation burden, separately | **Not assessed** |
| 2. Capture and presentation | Myeloid, by lineage where audited | Cell shares; presentation-related genes of M0_EXTRA_ANTIGEN_PRESENTATION, shown gene by gene | Capture and cross-presentation not assessed |
| 3. Priming | Not sampled | Nothing. Priming occurs mainly in lymph nodes | **Not assessed** |
| 4. Trafficking | Endothelial, myeloid, T/NK | M1_MOBILITY genes split into ligands, receptors and adhesion genes, each in its own lineage. No combined trafficking score | Cell movement not assessed |
| 5. Infiltration and barriers | All compartments | Recovered-cell shares, for compatible sampling only; M4_EXCLUSION genes in fibroblast/stromal cells | Spatial position not assessed |
| 6. Recognition | Luminal/malignant epithelial | Luminal/epithelial antigen-presentation machinery (P_ANTIGEN_PRESENTATION) | Recognition not assessed |
| 7. Killing | CD8 T and NK, by lineage where audited | Effector genes shown separately within lineage. No ranking of killing capacity from the M2 composite | Killing not assessed |
| Regulation | CD8, CD4, NK, myeloid, epithelial, fibroblast/stromal | Per-gene checkpoint expression (M5_CHECKPOINT_CANDIDATES); M4 genes; cell shares | Whether a brake is active not assessed |

B/plasma cells are reported as a cell share, with CXCL13 and CXCR5 as limited context.

**Data.**
- CELLxGENE hormone-naive prostate atlas (24 donors), as the prostate source.
- Baseline cohorts of the Lin 2026 atlas, as the reference from other cancers.
- TCGA-PRAD as bulk support, once loaded: quanTIseq fractions, panel scores and mutation burden.

**Method.**
- **Broad compartments are the main analysis.**
- **Lineage subdivision (amends the signed single-cell plan).** The plan excludes Lin's fine subtypes as targets because some were defined with panel genes. This part permits only audited lineage splits: CD4, CD8, NK, dendritic cells and macrophages. Label provenance and marker dependence are disclosed. Programme-defined states are never used, and no split counts as independent evidence about the genes that defined it.
- **Crosswalk.** One explicit table maps prostate labels to Lin labels, frozen before any stage result is examined. A lineage with no match is reported for its own atlas only. A split that does not exist is "not resolved".
- **Sampling.** Before comparing shares, record each study's enrichment or sorting. A CD45-enriched or sorted study gives no whole-tumour immune share.
- **After A-BIO and N14 are frozen.** The top A-BIO genes by the fixed SC-1 rule are read in the same way.
- **Signed single-cell rules carry over:** 15 cells, 5,000 UMI, 5 donors, log2(CPM+1) on the full library, 80% panel coverage, a missing-layer gene is missing, donor-level summaries, the 50 CPM detection rule, and no z-scoring across compartments.
- **Summary figure.** One row per stage, one column per study. Nothing is pooled across studies.
- Results are shown as distributions. **No cutpoint defines "cold", "inactive" or a "failed stage".** "Low" always names its study and lineage reference.
- **New gene sets.** Registry sets that are not frozen (T_CELL_STATE, MHC_II_PRESENTATION, TME_EXCLUSION_STROMA, TME_METABOLIC_SUPPRESSION) are not used.

**Limits.**
- Cell shares depend on tissue handling, and dissociation can under-represent some cells. A low share is not proof of few cells in the tumour.
- The prostate compartment does not separate tumour cells from normal luminal cells.
- Whether the prostate minor labels support the lineage splits is not yet checked.
- With 24 donors, rare types may fail the 15-cell or 5-donor rule. These are "not assessed", not low.
- Stages are linked, so one low reading does not locate a cause.
- The wording is "low programme expression", never "inactive cells".
- The atlas holds primary tumours only. There is no response comparison.

**Budget:** about 20 hours.

## Part 2. B-PROFILE: response-associated profile in naive TCGA tumours (Paper B, exploratory)

**Question.** Among treatment-naive TCGA tumours, does a high frozen RNA score go with a distinct bulk methylation pattern, in genes outside that score?

**Term.** A TCGA patient has no ICI response, so no TCGA tumour is called a responder. The term is "response-associated profile". "Predisposed responder" describes the aim and is not used as a result. The score is an RNA-profile ranking, never a response probability.

**Timing.** Only after the A-P2 equation, A-BIO and the Paper B measurement gates are frozen. It never reads IMvigor210.

**Method.**
1. **Transport.** Freeze the TCGA TPM route, identifiers, coverage, specimen rules and missingness, and a source-supported definition of treatment-naive and of primary tumour. Rebuild the four complete panel means on log2(TPM+1), then apply the full equation with its **training** means, SDs, coefficients and intercept. Do not restandardise within TCGA.
2. **Ranking.** Percentile-rank the linear predictor within each cancer. Report how TCGA feature distributions overlap the development data. Do not retune.
3. **Model.** For each Tier 1+2 gene not in any of the four score panels: promoter methylation ~ score + purity + copy number + global methylation, within each cancer. This removes direct score-membership overlap. It does not remove co-expression or shared immune programmes.
4. BH FDR 10% within each cancer.
5. **Required sensitivity:** add MethylCIBERSORT fractions, using the signed removal of tested-promoter probes, a frozen rule for fraction handling, and no rank-deficient model. Report attenuation with uncertainty, not whether significance "holds". Persistence does not prove tumour-intrinsic regulation, and attenuation does not prove composition.
6. TCGA-PRAD is scored the same way and reported as position within prostate only.

**Removed from draft 1.** The survival check. A score can be both prognostic and predictive, and a null would prove nothing, so it cannot show ICI specificity.

**Limits.** Tumours are mostly primary and untreated, and many ICI samples are metastatic. Score and methylation come from the same tumour at one time. No result is a prediction of ICI response.

**Budget:** about 25 hours. It joins the over-run cut order after multi-omics.

## Part 3. B-METHRESP: methylation and response in the same patients (Paper B, exploratory; review says drop)

**Question.** In ICI cohorts with methylation, does promoter methylation of a small fixed gene family differ between response classes?

**Review note.** Astra recommended dropping this part first: it is small, it is not new independent validation of published work in these cohorts, and its hours are likely too low. All of the following apply.

**Scope.** A new named analysis with its own contract. B-ICIM stays outcome-free, as signed. Cho and Krakow expansion and any pooling need explicit approval here, because the B-ICIM plan does not allow them.

**Endpoints.** ORR, clinical benefit and source-defined labels stay separate and are never pooled. The signed Jung label is clinical benefit, not ORR. Each cohort's endpoint is fixed from source definitions, not from field names.

**Genes.** The selection rule is frozen before Paper B results exist. The resulting list is hashed before any ICI outcome is linked. An empty list ends the analysis.

**Method.** Per-cohort unadjusted Hedges g and beta-value differences with uncertainty, as description only. No large adjustment model. A cohort needs at least 5 patients per class; otherwise "not estimable". Multiplicity is BH FDR 10% within cohort and endpoint family. Whether paired RNA is required is frozen in the checklist.

**Limits.** About 56 paired patients at most, so a null is "inconclusive". The Paper B ban on saying that methylation predicts ICI response stays.

**Budget:** about 8 hours for the analysis alone. Endpoint reconstruction and methylation processing would add to this.

## Part 4. A-RCT: randomised treatment comparison (Paper A, secondary)

**Why.** Every patient in A-BIO received ICI, so A-BIO cannot separate a marker of ICI benefit from a marker of better outcome under any treatment. A randomised comparison arm can address this.

**Data.** The Braun 2020 workbook, already held. Paper A uses its nivolumab arm and excludes the everolimus arm. CheckMate 025 randomised nivolumab against everolimus. Adding the excluded arm is recorded against the acquisition-close decision.

**Stage 1: feasibility audit (level 1 and 2 access only).** Confirm or stop:
1. S4A holds expression for the everolimus patients.
2. The source gives explicit CheckMate 025 identifiers and assigned treatment.
3. Specimens are pre-randomisation, with one specimen per patient. The evidence notes describe mostly archival tissue collected before earlier therapy, so the score may not show the immune state just before nivolumab.
4. Tissue selection and QC are documented. Report the path from randomised patients to RNA and to outcome, by arm. Inspect baseline differences. Balance alone cannot prove absence of bias.
5. The four expression batches: what defined them, how they align with trial and arm, and what the ComBat design preserved. No second correction is applied.
6. Responders and non-responders within each arm are enough for the planned model, by a precision assessment using hypothetical scenarios fixed before any score–outcome look. A floor on arm size is not enough.

If selection cannot be defended, the result is an exploratory interaction in the biomarker subset, with no causal wording. If items 1 to 3 fail, A-RCT is dropped.

**Stage 2: scoring contract, frozen before release.** Braun's values are log2 upper-quartile expression, ComBat-corrected, with a +21 offset. They are not TPM.
- Scores are computed on the deposited scale, with custom method names and complete-coverage eligibility. The numerical freeze's custom-mean rule covers A-BIO only, so this contract is new.
- Exact CYT is unavailable. A two-gene feature can be added only under a different name, with the user's approval.
- The eligible score family is listed exactly. Incomplete panels, including Hallmark IFN-gamma if incomplete, are excluded and not reduced.
- One focal score is named before results, or the whole family is called exploratory.

**Stage 3: analysis, after release.**
- logit P(ORR) = b0 + bA·arm + bS·score + bAS·arm·score, with arm coded explicitly and the score standardised once across eligible CheckMate 025 patients, not by arm.
- bAS is the change in the log treatment odds ratio per score unit. Also report predicted response probabilities and absolute treatment differences at fixed score values, with uncertainty.
- Separation handling, rank checks, the small-sample estimator and interval method, and missing-outcome handling are frozen in the checklist.
- BH FDR 10% across the eligible family, if no focal score is named. An interval spanning zero is "inconclusive".
- **PFS** enters only if registered before ORR results, with verified time origin, censoring, event adequacy, a proportional-hazards plan and its own multiplicity. Otherwise the scope is ORR only. PFS is never a fallback.

**Claim.** "On the odds scale, the score modified the difference between nivolumab and everolimus in this trial's biomarker subset." This is a narrow, named exception to Paper A section 9, and only if Stage 1 passes. It does not show that a gene causes response, and it does not establish a general ICI-specific mechanism.

**Unchanged.** A-P2, A-BIO and the numerical freeze do not change. Part 4 needs its own register entry before outcomes unlock.

**Budget:** about 15 hours, with Stage 1 as a short step that can stop the work.

## Budget note

The parts add about 68 hours (or 60 without Part 3). The analysis-modules plan already describes about 762 hours, so the total would be about 830 if these are all new work. This is planning arithmetic, not a measure of work left. The first cuts are Part 3, then Part 2.

## Not included

- **IMmotion150** (atezolizumab against sunitinib) could be a second randomised check. Paper A acquisition is closed, and the sunitinib arm was dropped, so reopening it is a separate user decision.
- **GSE343570** (pembrolizumab with or without vorinostat) stays the exploratory check signed on 29 Oct.
- **Mendelian randomisation** needs a large germline study of ICI response, which this project does not hold.
- **Gene-level evidence.** Paper C and the wet-lab plan provide perturbation and functional evidence under their own designs. Causality for one gene needs an intervention and controls that identify that gene's effect. Top A-BIO genes can be looked up in Paper C sources as orthogonal corroboration after A-BIO is frozen.

## Signature

Signed by the user on 5 Nov 2026 ("sign it").

- [x] Part 1, B-STATE
- [x] Part 2, B-PROFILE
- [x] Part 3, B-METHRESP
- [x] Part 4, A-RCT
