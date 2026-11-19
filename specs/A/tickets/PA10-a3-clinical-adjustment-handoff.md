# PA10: A3: clinical adjustment set and handoff rule (N14)

**Status:** Research, then your decisions. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
An adjusted association is only credible if the covariates are fixed before outcomes and actually estimable in each study. The A→B/C handoff rule decides which genes later papers inherit.

## Authority
`specs/A/SPEC_v2.md` §4.3; freeze register N14; `specs/A/A_TO_BC_HANDOFF.md`.

## Change
Fix the baseline clinical set and its inclusion rule per study, the post-meta ranking rule, and N14. Research (19 Nov) proposes `A3_CLIN_MINIMAL_V0_PROPOSED` (unsigned):
- The unadjusted contrast stays primary. An adjusted estimate is a per-study sensitivity.
- It is allowed only with at least 30 evaluable patients, at least 8 in the smaller response group, and covariates documented, at least 90% complete and varying.
- Covariates enter in a fixed order: prior ICI, specimen site, one burden variable (for example LDH), prior lines, age, sex. The cap is n/15, at most 3. Complete cases only.
- PD-L1 and tumour mutational burden are not covariates: PD-L1 measures the same immune signal, and mutational burden changes the question.

Only about 5–7 studies, mostly melanoma, would qualify; many tables could not be read, so those cells are UNKNOWN.

## Done when
Decision record signed; A-BIO config reads the set by named columns only.

## Needs from the user
Sign the adjustment set (or accept the proposed rule), the ranking rule and N14. Also decide two cohort flags raised by the research: GSE159067 includes ICI plus an anti-KIR antibody (not ICI-only); GSE218989 may overlap GSE135222 (shared Samsung lung cases).

## Depends on
—

## Research
`docs/research/A_TICKETS_20261119/clinical_covariates.md` (done 19 Nov).
