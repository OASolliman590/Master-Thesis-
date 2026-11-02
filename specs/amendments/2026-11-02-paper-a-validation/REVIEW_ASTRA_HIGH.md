# Astra (gpt-6-astra, high effort) review of the Paper A validation options, 2 Nov 2026

Read-only review, kept verbatim except that absolute paths were made repository-relative.

**VERDICT:** Freeze a simplified D: one small ridge model, study-held-out development, a limited 70/30 internal sensitivity, and one explicitly bladder-specific external primary; reject D’s z-scored CYT and “optimism gap” interpretation.

## ANSWERS

**Q1. Is D sound and better than B or C?**

**D’s structure is useful; D as written is not ready to freeze.** C can support a valid bladder-specific external evaluation. D adds information about transfer between studies, which matters for this thesis, but does not automatically make the final model better.

The user is **right** that leaving out the only kidney, gastric or bladder study removes that cancer from training. Such folds answer a harder, different question from predicting additional patients in represented settings. The user is **wrong** if a within-cohort split is presented as evidence of transfer to independent studies or cancers. Representing every cancer in training does not remove laboratory, treatment or ascertainment differences.

The coordinator is **right** to retain study-held-out evaluation and protect IMvigor210. Three corrections are necessary:

- Small test slices are generally **estimable but imprecise**, not automatically nonestimable. Rounded 30% slices contain approximately Braun **4 R/40 NR**, Hugo **4/4**, Van Allen **2/10**, and GSE145996 **2/1**. Seven—not six—cohorts have approximately 2–5 test responders.
- A pooled patient AUROC permits comparisons between different studies and can reward study-level response prevalence. Calculate AUROCs **within studies**, then average.
- Internal versus study-held-out performance is not a clean “optimism gap”: training sizes, cancer representation and distributions differ. Call it a **validation-setting contrast**, without a causal attribution.

**Frozen default:** leave-one-study-family-out development; **20 repeated stratified 70/30 splits** as secondary internal validation. With the fixed model below, inner tuning is unnecessary.

**Q2. Is one external bladder study acceptable?**

**Yes, for a narrow external claim.** One study cannot substantiate independent validation across four cancers. Equal-cancer weighting reduces legitimately to weight **1** for IMvigor210; the formula does not manufacture broader evidence.

**Frozen default:** amend A-P2’s wording to:

> Paired difference in ORR AUROC between the frozen learned score and the thesis-defined CYT comparator among eligible pretreatment IMvigor210 patients.

Report both AUROCs and their difference, with a **95% paired, outcome-stratified percentile bootstrap interval using 2,000 resamples**. This conditions on the fitted model and observed test cohort; it excludes uncertainty from model development and sampling future studies.

Require **at least 10 patients in each outcome class** for the formal external comparison; below that, report descriptive results only. This is an operational minimum, **not** evidence of adequate precision. Approximately 298 total patients alone cannot establish precision without responder counts and paired-score information. An interval spanning zero is inconclusive about superiority.

**Q3. Should Braun be protected?**

**No.** Keep its development designation, subject to measurement compatibility. Fourteen responders would give an uncertain kidney-specific external estimate, but saying it would be “useless” is unjustified. The stronger reason is that reserving the only kidney development study changes training coverage while offering limited precision.

Braun is already signed for development. A new reservation cannot erase any prior molecular–outcome inspection.

**Frozen default:** no second protected external cohort. Braun contributes to the predictor only if its expression representation qualifies; otherwise it remains available for appropriate per-study biology. Do not equate “development admission” with eligibility for every analysis.

**Q4. Is within-study gene z-scoring acceptable?**

**Not as D’s universal measurement solution.**

Gene-wise z-scoring can support a deliberately cohort-relative analysis, but:

- It removes between-study biological differences as well as technical offsets.
- Means and variances depend on tissue composition and response mixture.
- Small-study estimates are unstable.
- Standardizing an entire study before its 70/30 split uses held-out expression.
- Standardizing a new test cohort from its own distribution creates a cohort-adaptive procedure, requiring a different contract from the frozen training-derived transform.

Most importantly, **z-scoring GZMA and PRF1 changes CYT**. Standardizing the *completed CYT score* by a positive affine transformation preserves its within-study AUROC; standardizing its constituent genes generally does not.

**Frozen default:** retain the existing TPM-compatible measurement route, compute the four features below per patient, and standardize those features using **training-only means and SDs**. Preserve CYT as `sqrt(TPM_GZMA × TPM_PRF1)`, without an offset—the thesis variant documented in the [measurement contract](specs/A/ASSAY_PROCESSING_CONTRACT.md) and [source-divergence amendment](specs/amendments/2026-10-16-immune-programmes/AMENDMENT.md).

The memo’s **578 patients/161 responders are a candidate ceiling**, not a verified common-input sample. Count matrices need a justified TPM route; cohort-centred or ComBat-adjusted values cannot simply be declared equivalent. Incompatible cohorts stay in A-BIO. Do not invent TPM or rename a replacement comparator to preserve sample size.

**Q5. Is elastic net justified?**

**Possible, but not my default here.** There is no universal rule that 161 responders forbids a penalized gene-level model. Nevertheless, nine candidate studies, three singleton cancers, heterogeneous measurements and a 600-hour thesis budget make genome-wide feature selection an unnecessarily fragile main analysis.

Nor do “11 locked panels” automatically mean 11 valid scalar predictors: M5/M6 contain heterogeneous individual markers, and several scoring methods remain unresolved.

**Frozen default:** logistic regression with **four predictors and ridge/L2 regularization**. Use the existing memberships of:

- `P_ANTIGEN_PRESENTATION`
- `M2_CYTOTOXICITY`
- `M3_VIRAL_MIMICRY`
- `M4_EXCLUSION`

For each, calculate the unweighted mean of `log2(TPM+1)` over **all** listed genes. Name these **custom panel-expression features**, not validated activity scores. Require complete feature coverage; no available-gene averaging.

After training-only feature standardization, minimize:

\[
\text{mean patient logistic loss}+\frac{0.1}{2}\sum_{k=1}^{4}\beta_k^2.
\]

Leave the intercept unpenalized. Use equal patient weights, no class weighting, no interactions, no cancer/study indicators and **no hyperparameter search**. This fixed penalty is a conservative design choice, not a claimed optimum. It removes the need for nested tuning while retaining honest held-out evaluation.

**Q6. What conflicts with signed rules or simple mode?**

**Several substantive changes require an explicit amendment; the options memo is not authorization.**

- D’s gene-wise z-scoring conflicts with the frozen measurement, CYT and training-only preprocessing contracts.
- The narrower external population must be stated explicitly; development predictions cannot replace A-P2.
- My four-feature fixed-ridge proposal changes the signed gene-level elastic-net procedure.
- Simple mode says analysis is per study and forbids raw-expression merging. Explicitly permit pooling the **four derived patient features** for A-P2 while preserving separate source matrices and study-specific evaluation.
- Accepted cohort decisions must govern actual inputs. In particular, the [batch sign-off](docs/decisions/BATCH_SIGNOFF_20261101.md) specifies Gide’s provisional iAtlas representation and a without-Gide sensitivity; the memo’s recount3 description does not establish a completed 73-patient crosswalk.

**Frozen default:** one concise amendment covering these choices. Keep the registry and existing protections; do not recreate intake bureaucracy. Unknown software versions remain caveats. Wrong measurement scales and unresolved patient identity remain substantive problems.

## RECOMMENDED DESIGN

1. **One formal primary:** frozen model minus CYT AUROC in IMvigor210, weight **1**, evaluated once after model lock.
2. **Eligible development population:** verified ORR patients with compatible measurements, deduplicated across study families. Unknown responses are excluded, never recoded as NR. Require at least **three independent development families**, with every outer training set containing at least **20 R and 20 NR**.
3. **One learner:** the four custom panel features, fixed ridge penalty **0.1** on mean logistic loss, unpenalized intercept; no feature selection or tuning.
4. **Main development evaluation:** leave one complete study family out, refitting preprocessing and coefficients. Label results **INTERNAL_EXTERNAL**; identify singleton-cancer folds as joint study/cancer transport assessments.
5. **Development summary:** report study-specific paired AUROC differences, then equal-cancer/equal-study averages. If all nine qualify, each singleton-cancer study receives **1/4**, each melanoma study **1/24**. Freeze actual eligibility and weights before performance inspection.
6. **Internal sensitivity:** **20 stratified 70/30 repeats**, splitting patients within studies. Evaluate only studies with **≥10 R and ≥10 NR**, yielding at least approximately **3 test patients per class**. The supplied counts qualify seven studies, **147 R/382 NR**, before measurement exclusions. Smaller qualifying cohorts can contribute training data only.
7. **Internal reporting:** average within-study AUROCs using declared cancer/study weights. Report the repeat mean and SD as split variability—not a confidence interval from 20 independent experiments. Do not pool repeated predictions into an enlarged sample.
8. **Final fit:** use **100% of eligible development patients**; freeze features, transforms, coefficients and scoring equation before IMvigor210 access. Preserve the whole protected family across papers.
9. **Final uncertainty:** **2,000 paired stratified bootstrap resamples**, **95% percentile interval**, seed **20261102**. Label `UNTOUCHED_FINAL_TEST` only if the exposure audit supports it; report negative results unchanged.
10. **Scope ceiling:** A-BIO and A-P1 remain secondary. No genome-wide predictive challenger, calibration project or added external-cohort hunt in the default plan. Failure of predictor compatibility leaves A-P2 unavailable, not replaced by a favourable secondary.

## RISKS

- **Compatible sample size is smaller than advertised.** Mitigation: verify the measurement route before numerical roster freeze; retain incompatible studies for appropriate biology.
- **Study, cancer and treatment effects are entangled.** Mitigation: show individual-study results and label singleton-cancer transport explicitly; avoid attributing failures to cancer alone.
- **Patient overlap or historical exposure breaks independence.** Mitigation: group overlap-connected families and audit final-test exposure across all papers.
- **Tiny cohorts and repeated splits invite false precision.** Mitigation: disclose class counts, flag whole-study estimates below 10 per class as very imprecise, and never treat repeats as new patients.
- **Feature definitions or models change after disappointing results.** Mitigation: freeze one equation and its preprocessing prospectively; later revisions require separately labelled evaluation.

## WHAT THE PAPER CAN AND CANNOT CLAIM

**Can claim**

- How one frozen, compact model discriminates observed ORR relative to CYT in IMvigor210, with conditional uncertainty.
- How that learning procedure performs across the admitted development studies and within represented study settings.
- Which prespecified biological associations are supported, contradictory or inconclusive in their measured contexts.

**Cannot claim**

- Independent pan-cancer validation, cancer-specific clinical readiness, or calibrated response probabilities.
- That an internal–external performance difference measures pure optimism.
- Treatment benefit, causal immune mechanisms, or information conditional on CYT merely from a higher AUROC.
- Prostate ICI-response prediction, or biological validation from software tests.
