# Paper A data acquisition closed, 2 Nov 2026

**Decision by the user in chat on 2 Nov 2026 ("Yes, close it").**

## What is closed
Acquisition of bulk ICI response cohorts for Paper A. The roster below is frozen before any A-P2 development run or A-BIO response analysis, as the signed validation amendment requires (`specs/amendments/2026-11-02-paper-a-validation/AMENDMENT.md`).

## The roster at close (`docs/cohorts/REGISTRY.tsv`)
- **20 cohorts signed for development, 1,257 patients:** riaz_gse91061, hugo_gse78220, gse168204, liu2019, gide2019, braun2020, vanallen2015, gse135222, gse136961, gse218989, gse159067, gse93157, gse67501, gse122220, gse111636, gse176307, kim2018, gse165278, gse145996 and gse140901.
- **1 locked final test:** imvigor210 (UNTOUCHED_FINAL_TEST).
- **A-P2 inputs:** 7 TPM families, 408 patients (139 responders, 269 non-responders); `docs/decisions/A_P2_MEASUREMENT_20261102.md`.

## What was not pursued, and why
- **21 open candidates** were marked "not pursued at Paper A acquisition close": immotion150, pmid33806963, snyder2014, jerby_arnon_bulk, cui_puch, snyder2017, nathanson, amadeus, chen2016, limagne, schalper, gse343570_mono, gse202069, gse215011, gse126045, gse305240, gse305511, prjna564119, srp609012, gse181815 and gse165745. Reasons: small size, unverified response labels or identity, overlap with signed families (Snyder/Nathanson with gse165278), or low gene coverage (gse165745). gse343570 stays in Paper B's signed B-V plan; only its monotherapy arm as a Paper A cohort is not pursued.
- **8 controlled-access cohorts were dropped** (user decision 2 Nov): miao2018, ucla_srp230414, imvigor010, immotion151, su2c_mark, grasso, pemdac and lee2020.
- **Excluded, parked or on hold** cohorts keep their recorded reasons.
- The legacy 117-study list is fully reconciled: `docs/research/reconcile_117/`.

## Kept for Paper B (not part of Paper A acquisition)
gse213145, gse264158, gse119144 and gse126043 belong to the signed B-ICIM secondary (`specs/amendments/2026-11-02-paper-b-ici-methylation/AMENDMENT.md`). Paper B's own data (TCGA-PRAD, CPC-GENE, the prostate single-cell references, PCCAT) are handled when Paper B resumes.

## Reopening rule
After this date a new Paper A cohort can be added only with a written reason, recorded here, and only for analyses not yet run. It can never be added after an analysis that would include it has been seen, and never into the locked final test.
