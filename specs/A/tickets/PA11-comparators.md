# PA11: Comparators with exact published scoring

**Status:** Blocked: PA07. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
A comparator is fair only with its exact published rule, on the same patients, labelled with any prior exposure.

## Authority
`specs/A/SPEC_v2.md` §7; `specs/A/COMPARATOR_REGISTRY.md`.

## Change
Implement or correct each admissible comparator to its published rule, and mark the others as not implementable. Research (19 Nov):
- **CYT:** Rooney's Methods use a 0.01 offset, sqrt((GZMA+0.01)(PRF1+0.01)). The project's frozen CYT has none but keeps the ID `CYT_Rooney_TPM_v1`. The frozen formal comparator is not changed here; the label or wording is fixed (see Needs).
- **Ayers/Cristescu GEP and TIS:** blocked. The weights are only in a supplement that also holds patient-level trial data; both are NanoString assays, so any RNA-seq version is a port.
- **PredictIO and Subramanian 2023:** cohort-level procedures (GSVA within cohort, then a difference or clustering), not fixed per-sample rules. Subramanian's author script does not run as written.
- **Lin 2026:** blocked. No gene list, weights or code are public.

Apply the registry wording fixes listed in the note.

## Done when
Known-answer tests from each author's own example where available; registry updated with exposure labels from PA07.

## Needs from the user
Admit or refuse each comparator. Decide on CYT: keep the frozen no-offset rule and rename it (for example `CYT_TPM_no_offset_v1`), with a manuscript note that it differs from Rooney 2015. Adopting the offset would change a frozen value and needs an amendment.

## Depends on
PA07

## Research
`docs/research/A_TICKETS_20261119/comparator_rules.md` (done 19 Nov).
