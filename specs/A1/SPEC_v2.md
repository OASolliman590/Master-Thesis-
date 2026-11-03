# Paper A.1: consolidated specification v2.1, 3 Nov 2026

**Status: DRAFT v2.1 for signature.** v2.1 (3 Nov): no change to A.1's design; the version number is aligned with Papers A and B. Paper A's composition analysis (A-COMP) is baseline only and is not applied to on-treatment change. It consolidates the A.1 kit of 15 Oct (`specs/A1/`: LONGITUDINAL_ANALYSIS, PAIRING_CONTRACT, TIMEPOINT_ONTOLOGY, contrast_registry.tsv) with the later signed decisions:
- integrated plan, 29 Oct: within-study arm comparison for randomised mixed studies;
- single-cell plan, 2 Nov: single-cell A.1 cut, bulk A.1 kept;
- Paper A acquisition close, 2 Nov.

It also takes in the evidence review of 2 Nov (`docs/research/SPEC_REVISION_EVIDENCE_20261102.md`). The older files keep the full technical detail.

## 1. Question
**Which immune programmes change during ICI treatment, and does the within-patient change differ between eventual responders and non-responders?**

**Central estimand,** within one qualified study and window: Δ = E[X_on − X_pre | R] − E[X_on − X_pre | NR], the response-associated differential change (RESPONSE_TIME_INTERACTION). It is not a randomised ICI effect and not a parallel-trends estimate. "Significant in R but not in NR" is never used as evidence of a difference.

## 2. Data
- **Source:** signed Paper A cohorts that also hold on-treatment tumour RNA from the same patients. Every pair needs a source-supported patient, specimen and day link, built by the deterministic pairing algorithm in `PAIRING_CONTRACT.md`.
- **Candidate roster (to verify at the A.1 freeze; nothing counted yet):**
  - **Riaz GSE91061:** pre and on-nivolumab biopsies, ipilimumab-naive and ipilimumab-progressed strata. recount3 counts are pinned.
  - **Gide 2019:** on-treatment (EDT) runs; 14 matched by the title rule, which the user has not yet accepted for A.1.
  - **GSE165278:** 7 pre and 15 post-ipilimumab samples. Patient pairing is to check.
  - **GSE145996:** 3 samples collected after the anti-PD-1 start (196-694 days).
  - **GSE168204:** pre/post status to check.
- **Protected and excluded:** IMvigor210, in every modality and timepoint; combination cohorts; dropped controlled-access sources.
- **Randomised mixed studies:** the ICI-only arm against the combination arm, compared within the study (signed 29 Oct).

## 3. Windows and timing
- No universal early or late cutoff. Each study's window is registered before any outcome look: index event, lower and upper day bounds (or a verified source category), tie rule, lesion and platform policy.
- The exact day distance between baseline and follow-up is recorded for every pair. Pairs outside the window are excluded, with reasons.
- Progression, regimen-change and after-stop biopsies are never treated as scheduled on-treatment samples.

## 4. Features analysed
- The 4 A-P2 panel features plus CYT, on the same TPM route as A-P2 where available.
- The 11 locked panels (each with complete coverage), and the individual M5 and M6 genes, on each source's own scale.
- No genome-wide change analysis in the default plan (it is optional, with FDR, if time allows).

## 5. Statistical analysis
- **Two-timepoint route (primary):** for complete pairs, d = X_on − X_pre on one declared scale, then d = α + β·R + prespecified covariates (not including the baseline value).
  - β estimates the central estimand Δ, the unconditional difference in mean change (as in `LONGITUDINAL_ANALYSIS.md`).
- **Baseline-adjusted sensitivity (ANCOVA):** the same model with X_pre added. Its coefficient is the response difference in change **conditional on baseline**, a different estimand.
  - The two diverge when baseline expression differs by response class and the baseline coefficient is non-zero (Lord's paradox). That is expected here, because Paper A hypothesises baseline differences.
  - Both are reported and labelled. The ANCOVA result is never presented as Δ.
- **Repeated-measures route** (more than one follow-up window): expression ~ response × window + (1 | patient), with an implementation that supports the needed weights and degrees of freedom (`LONGITUDINAL_ANALYSIS.md`).
- **Synthesis:** per study first. Studies are combined only when regimen, window and scale are compatible, with the signed small-k rules (1 study alone; 2-3 tentative, modified Knapp–Hartung, no prediction interval).
- **Multiplicity:** Holm across the pre-declared panel family within each synthesis family; individual M5/M6 genes are exploratory (BH FDR 10%). Two-sided intervals are always reported.
- **Small samples:** with 7-40 pairs per study, only large effects are detectable, and a null is "inconclusive".

## 6. Bias controls (from the evidence review)
1. Explicit day windows per study (published papers rarely state them).
2. Attrition reporting: patients with a baseline but no on-treatment biopsy, by response class. Survivorship and early-progression bias are stated.
3. Lesion site: same-lesion pairs preferred where the design supports it; a different-lesion pair is labelled, with a same-lesion sensitivity where estimable.
4. Regimen stratification: monotherapy versus dual ICI, and ipilimumab-naive versus ipilimumab-progressed (Riaz) are analysed separately.
5. Composition: a change in immune programmes may reflect infiltration rather than within-cell change. This is stated, never resolved by the bulk data alone.

## 7. Claims
**Can claim:** response-associated differential change of named programmes in specified studies and windows, with uncertainty.

**Cannot claim:** that ICI caused the change; a randomised treatment effect, except within randomised mixed studies; mechanism; anything from a cross-sectional on-treatment R-versus-NR comparison presented as change.

## 8. Budget and implementation
- About 60 researcher-hours.
- Implementation reuses `tools/a_cohorts` and the A-P2 TPM routes. A small `tools/a1` builds the pairs and fits the models (not started).
- The A.1 roster and windows are frozen in `specs/A1/contrast_registry.tsv` before any outcome look.

## 9. Open gates
1. Verify the on-treatment roster and each pair's day distance (Riaz, Gide EDT, GSE165278, GSE145996, GSE168204).
2. Decide on accepting the Gide EDT crosswalk (14 runs).
3. Register windows per study.
4. Freeze the Hallmark IFN-gamma membership (shared with Paper A).
