# Paper A validation and predictor amendment, 2 Nov 2026

**Status: DRAFT for signature.** Built from `OPTIONS.md` and Astra's high-effort review (`REVIEW_ASTRA_HIGH.md`), on the user's instruction of 2 Nov 2026 ("Yes, write it"). It amends the A-P2 parts of `specs/A/PREDICTION_ANALYSIS.md`, `specs/A/VALIDATION_AND_SPLITS.md` and `specs/A/SCIENTIFIC_AIM_AND_CLAIMS.md`, and the 29 Oct integrated plan. Everything not named here is unchanged: A-BIO, A-P1, the locked panels as the main biology result, endpoint rules, combination exclusions and the protected final-test family. It authorises no analysis by itself; the numbers below are frozen when this is signed.

## Why it changes
- The user proposed a 70/30 patient split within every cohort, so that every cancer is represented in training.
- The ORR class counts (161 responders across 9 candidate studies; six are melanoma, and kidney, gastric and bladder have one study each) make a gene-level elastic net and per-study 30% test slices fragile.
- The design below keeps cross-study evaluation, adds the user's split as a secondary check, and narrows the external claim to what one test study can support.

## 1. Primary (A-P2, redefined)
**The paired difference in ORR AUROC between the frozen learned score and CYT among eligible pretreatment IMvigor210 patients.**
- IMvigor210 has weight 1; the equal-cancer weighting reduces to this one study, and the claim is bladder-specific.
- It is evaluated once, after the model, features, transforms, coefficients and scoring equation are frozen and recorded.
- Uncertainty: 2,000 paired, outcome-stratified bootstrap resamples, 95% percentile interval, seed 20261102. This interval conditions on the fitted model and the observed test cohort.
- The formal comparison needs at least 10 patients in each ORR class; below that, it is descriptive only. An interval that spans zero is inconclusive about superiority.
- The label UNTOUCHED_FINAL_TEST is used only if the exposure audit supports it. A negative result is reported unchanged.
- Braun is **not** protected. It stays in development if its measurement qualifies (section 3).

## 2. The learner (replaces the gene-level elastic net)
- **Features (4):** for each patient, the unweighted mean of log2(TPM+1) over **all** listed genes of each of four locked panels (`specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json`):
  - `P_ANTIGEN_PRESENTATION`, 8 genes (membership sha256 81d26587…);
  - `M2_CYTOTOXICITY`, 12 genes (106d5c31…);
  - `M3_VIRAL_MIMICRY`, 13 genes (0004a1b2…);
  - `M4_EXCLUSION`, 13 genes (a28d559a…).
  These are named **custom panel-expression features**, not validated activity scores. Complete gene coverage is required; there is no available-gene averaging. `M2_CYTOTOXICITY` contains GZMA and PRF1, the CYT genes, so the learned score partly overlaps CYT; this is stated with every result.
- **Model:** logistic regression with an L2 (ridge) penalty, minimising the mean patient logistic loss plus (0.1 / 2) × Σ β², with an unpenalised intercept.
- Features are standardised with **training-set means and SDs only**.
- Equal patient weights, no class weighting, no interactions, no cancer or study indicators, and **no hyperparameter search**. The penalty 0.1 is a fixed, conservative choice, not a tuned optimum, so no nested tuning is needed.
- **CYT** stays `sqrt(TPM_GZMA × TPM_PRF1)` without an offset (`specs/A/ASSAY_PROCESSING_CONTRACT.md`). No gene-wise z-scoring is applied, because that would change CYT.

## 3. Who can train it (measurement compatibility, verified before the roster is frozen)
- Eligible: verified ORR baseline patients with a TPM-compatible representation, deduplicated across study families. Unknown response is excluded and never recoded as non-response.
- Expected status (to be confirmed per source):

| Cohort | Representation | Expected A-P2 status |
| --- | --- | --- |
| liu2019 | TPM | eligible |
| riaz_gse91061, hugo_gse78220 | author FPKM (complete feature universe needed) | eligible via FPKM→TPM if the universe is complete |
| vanallen2015 | RPKM/FPKM (unclear) | verify |
| gse145996 | FPKM | eligible via FPKM→TPM if complete |
| kim2018 | recount3 counts | needs a documented count→TPM route (effective lengths) |
| gide2019 | iAtlas log2 upper-quartile (signed 1 Nov rule) | not TPM: ineligible unless the recount3 crosswalk is completed |
| braun2020 | log2 upper-quartile, ComBat within study | not TPM: ineligible unless source TPM is found |
| gse176307 | log2(1+x), median-centred | not TPM: ineligible unless source values are found |

- Cohorts that fail stay in A-BIO and the locked-panel biology. A wrong scale is never "fixed" by renaming, and no TPM is invented.
- At least **three independent development families** are needed, and every leave-one-out training set must contain at least **20 responders and 20 non-responders**. Otherwise A-P2 is reported as unavailable, not replaced by a secondary result.

## 4. Development evaluation (secondary, labelled INTERNAL_EXTERNAL)
- **Main:** leave one complete study family out; preprocessing and coefficients are refitted without it. Single-study-cancer folds are labelled as joint study-and-cancer transfer.
- Report the study-specific paired AUROC differences, then equal-cancer and equal-study averages. Eligibility and weights are frozen before any performance is seen; if all nine qualified, each single-study cancer would weigh 1/4 and each melanoma study 1/24.
- **The user's split, as a sensitivity:** 20 repeated, response-stratified 70/30 patient splits **within** studies. Only studies with at least 10 responders and 10 non-responders are evaluated; smaller cohorts contribute training data only.
  - AUROCs are computed within studies and then averaged with the declared weights. Patients are never pooled across studies into one AUROC.
  - The repeat mean and SD are reported as split variability, not as a confidence interval. Repeated predictions are never pooled into a larger sample.
- The difference between the internal and study-held-out results is called a **validation-setting contrast**, not an optimism measure: training size, cancer representation and distributions all differ.

## 5. Final model
Fitted on 100% of eligible development patients. Its equation (feature definitions, training means and SDs, coefficients, intercept) is recorded and published, as the 29 Oct plan requires. It is then evaluated once on IMvigor210.

## 6. Simple-mode clarification
Raw expression is still never merged across studies. Pooling is allowed only for the **four derived patient-level features** used by A-P2; source matrices stay separate, and evaluation stays within study.

## 7. Claims
**Can claim:** how one frozen, compact model discriminates ORR relative to CYT in IMvigor210, with conditional uncertainty; how the procedure performs across the development studies and within represented settings; which prespecified biological associations are supported, contradictory or inconclusive.

**Cannot claim:** independent pan-cancer validation; cancer-specific clinical readiness; calibrated response probabilities; that an internal-versus-external gap measures pure optimism; treatment benefit or causal mechanism; information beyond CYT from a higher AUROC alone; prostate ICI response prediction.

## 8. Still open (separate decisions, not in this amendment)
The A-BIO details: the locked-panel effect measure, endpoint families, and the genome-wide differential-expression method and FDR (decisions D4 to D6 of 2 Nov).
