# Paper A validation design: options memo, 2 Nov 2026

**Status: for review (Astra, high), not a decision.** Requested by the user on 2 Nov 2026 ("rethink the approach and review with astra high"), after the user proposed training on about 70% of patients from each cohort and testing on the other 30%, because "due to different cancers" a held-out-study design leaves cancers out of training.

## What is fixed already
- Signed A-P2 (spec `specs/A/PREDICTION_ANALYSIS.md`, `VALIDATION_AND_SPLITS.md`, 29 Oct amendment): paired AUROC difference, frozen learned score minus CYT, on ORR, on independent test patients, averaged with equal cancer weights and equal study weights within cancer. The spec says patient-random folds cannot replace the cross-study design.
- IMvigor210 (bladder, anti-PD-L1, about 298 ORR-evaluable) is the locked, untouched final test.
- A-P2 needs whole-transcriptome RNA-seq with ORR. Panels, arrays and non-ORR cohorts feed only the biology results (A-BIO, locked panels).

## Candidate A-P2 cohorts (ORR-evaluable baseline patients; class counts are permitted for precision planning)
| Cohort | Cancer | R | NR | Unknown |
| --- | --- | ---: | ---: | ---: |
| liu2019 | melanoma | 41 | 61 | 0 |
| gide2019 | melanoma | 40 | 33 | 0 |
| gse176307 | bladder | 16 | 71 | 1 |
| braun2020 | kidney | 14 | 133 | 34 |
| hugo_gse78220 | melanoma | 14 | 12 | 0 |
| kim2018 | gastric | 12 | 33 | 0 |
| riaz_gse91061 | melanoma | 10 | 39 | 0 |
| vanallen2015 | melanoma (anti-CTLA-4) | 7 | 32 | 1 |
| gse145996 | melanoma | 7 | 3 | 0 |
| **Total** | 4 cancers | **161** | **417** | |

Six of nine are melanoma. Kidney, gastric and bladder have one study each. Representations differ: recount3 counts (Riaz/Hugo sensitivity, Gide, Kim), TPM (Liu), FPKM (Riaz/Hugo author, Van Allen, GSE145996), log2 upper-quartile ComBat (Braun), log2(1+x) median-centred (GSE176307).

## Options
**A. Signed design.** Nested leave-one-study-out development across the 9 studies; one final model refit on all of them; tested once on IMvigor210 (optionally also a protected Braun). Every development study gets an out-of-study prediction. Weakness the user raised: when a single-study cancer (kidney, gastric, bladder) is held out, the model has never seen that cancer.

**B. User's proposal: 70/30 patient split within every cohort.** Train on 70% of every cohort; test on the pooled 30%. Strength: every cancer is in training. Weaknesses: the test shares lab, platform, processing and selection with training (internal validation, usually optimistic in ICI work); per-study 30% slices hold 2-5 responders in 6 of 9 cohorts (Braun about 4, Van Allen about 2, GSE145996 about 2), so per-study and per-cancer AUROCs are not estimable; it no longer matches the signed A-P2 estimand.

**C. Hybrid: B for development + IMvigor210 untouched.** As B, plus the single external IMvigor210 test as the independent claim.

**D. Coordinator's revised recommendation: leave-one-study-out as the main development estimate, a within-study split as a secondary internal estimate, and IMvigor210 as the untouched external test; Braun back in development.**
1. Main development estimate: nested leave-one-study-out, as in the signed spec. Each held-out study is scored by a model trained on all other studies. For single-study cancers this estimates transfer to an unseen cancer, and is labelled so.
2. Secondary internal estimate (answers the user's concern): repeated stratified patient splits within each development study (for example 70/30, 100 repeats, inner tuning only on the 70%), pooled across studies with study-stratified AUROC. It shows how much better within-study performance looks than cross-study performance: the optimism gap, which is informative in itself. Studies with fewer than 10 responders or non-responders contribute to training only.
3. Final model: refit on all development patients (every cancer represented), tested once on IMvigor210, which stays UNTOUCHED_FINAL_TEST and is the only independent claim. Bladder is then represented in training by GSE176307.
4. Braun is not protected: with 14 responders it is too small to be a useful separate test, and it is the only kidney RNA-seq cohort for training.
5. Cross-study comparability: standardise each gene within each study (z-score of log-expression) for the learner and for CYT alike, instead of forcing every source into log2(TPM+1). This needs an explicit measurement amendment.

## Questions for the reviewer
1. Is D statistically sound and better than B or C for this data? If not, what would you freeze instead?
2. Is a single external test (IMvigor210, one bladder study) an acceptable independent A-P2 claim, given equal-cancer weights reduce to that one study? Should A-P2 be redefined, and how?
3. Should Braun be protected as a second external test despite 14 responders?
4. Within-study z-scoring for cross-study learning: acceptable? Risks (composition differences, class imbalance shifting the mean, small studies)?
5. With 161 responders across 9 studies, is an elastic-net learner justified at all, or should A-P2 compare a smaller frozen model (for example the locked panels as features) against CYT?
6. Anything in D that conflicts with the signed rules or the simple-mode amendment.
