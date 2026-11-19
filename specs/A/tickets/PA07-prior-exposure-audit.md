# PA07: Finish the prior-exposure audit (gate 3)

**Status:** Research, then your acceptance. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
Before the final test or any comparator claim, we must know which published models were trained or tuned on our cohorts, especially on IMvigor210. Otherwise a comparator could look good because it has already seen the test data.

## Authority
`specs/A/SPEC_v2.md` §11 gate 3; amendment 15 Nov §6; `docs/validation/PAPER_A_PRIOR_EXPOSURE.md` (PROPOSED_INCOMPLETE).

## Change
Fold the research findings into the audit TSV and report: Lin 2026 bulk roster, PredictIO cohort mapping, train/tune vs evaluate for each comparator. Keep UNVERIFIED where sources do not settle it. Research (19 Nov), from author code:
- **PredictIO** was trained on 14 studies, including IMvigor210, Riaz, Hugo, Liu, Van Allen, Braun, GSE135222 and the GSE165278 source family; Gide and Kim were used only for validation.
- **COMPASS** was trained on IMvigor210 in every checkpoint except the leave-IMvigor210-out one, and on Riaz, Hugo, Liu, Gide, Van Allen, Kim and GSE176307.
- **Subramanian 2023, TIDE, Ayers GEP and CYT** were not trained or tuned on any roster cohort.
- **Lin 2026:** the 19-cohort bulk roster is still not public. The code suggests bulk cohorts were scored only, not used to select genes.

Consequence: PredictIO and COMPASS can only be reported on IMvigor210 as models already trained on it, never as a fair comparison there.

## Done when
Every comparator × cohort cell has a status and a primary-source locator; the audit is marked ready for acceptance.

## Needs from the user
Accept the audit conclusion, including the proposal that PredictIO and COMPASS get no fair IMvigor210 comparison. For Lin 2026: someone with journal access reads the supplement for the 19-cohort roster, or the roster is accepted as UNVERIFIED.

## Depends on
—

## Research
`docs/research/A_TICKETS_20261119/prior_exposure_gaps.md` (done 19 Nov).
