# Change 1 to A-RCT: PFS as the main endpoint (draft 2, 6 Nov 2026)

**Status: DRAFT 2. Not signed.** The user said "Yes, draft it" on 6 Nov 2026, after the Stage 1 audit (`docs/validation/A_RCT_FEASIBILITY_20261106.md`). It changes Part 4 of the signed 5 Nov amendment only. ORR stays Paper A's main endpoint family, and A-P2 stays its single formal primary. Draft 2 takes in the Astra review (`work_notes/coordinator_20261103/change1_review/final.txt`, outside Git). All thresholds below are coordinator proposals.

## Why

The signed main model is an ORR interaction. The CheckMate 025 RNA subset holds only 5 everolimus responders, so that model is unlikely to give the precision it needs. Penalisation could stabilise it but cannot supply missing information.

**Disclosure.** PFS replaces ORR for A-RCT after inspection of arm-specific response and PFS-status counts, before any survival time was read and before any feature–outcome analysis. This is a feasibility-informed amendment to a secondary analysis. ORR interaction testing is withdrawn. This change supersedes the Part 4 sentence "PFS is never a fallback" for this one decision. It is not outcome-blind, and the manuscript must not present PFS as the original endpoint. The counts and the accidental `Tumor_Shrinkage` load are logged in `DEVIATIONS.md` and the feasibility audit.

## What changes

| Item | Signed Part 4 | This change |
| --- | --- | --- |
| Main endpoint | ORR | PFS |
| ORR | Main model | Class counts by arm only. No interaction model |
| Score family | All eligible panels, focal score optional | One focal score, the others exploratory |

**OS is not included**, as a scope decision.

## Populations

Four populations are reported by arm:
1. **Candidates:** CheckMate 025 patients with RNA (130 everolimus, 120 nivolumab).
2. **Score-eligible:** candidates with finite values for every gene of the panel. Coverage tables cover 181 Braun patients, so an outcome-unlinked patient-level audit must confirm this for all 250.
3. **Endpoint-eligible:** valid PFS time and status. An ORR not-evaluable patient stays in if PFS is valid.
4. **Complete cases:** with all covariates.

Missingness is recorded by variable and arm, with the assumptions behind complete-case analysis. No imputation is added after results. If the checklist's stated loss limit is exceeded, the result is labelled exploratory.

## Scores

Scoring follows the Stage 2 contract on the deposited Braun scale, as custom expression features with their own method IDs, membership hashes, aliases (MB21D1 to CGAS, TMEM173 to STING1, the RIGI/DDX58 mapping) and missing-value rule. The A-BIO numerical freeze does not cover this use, so the contract is new.

Candidates under the strict rule: P_ANTIGEN_PRESENTATION, HOPE_18, M0, M2, M3, M4, M5 and M6.

Not eligible: AYERS_GEP_18 and M1_MOBILITY (CCL5 missing), Hallmark IFN-gamma (197 of 200 genes) and exact CYT (values are not TPM). The 90% rule does not rescue a panel here.

- **Focal score: M2_CYTOTOXICITY.** It is one of the four A-P2 features and it is complete in Braun. Its CD3 and CD8 genes mean it does not directly measure killing, and it does not replace CYT.
- **Exploratory:** the other seven panels, one interaction test each, BH FDR 10% across those seven. No manuscript-wide FDR claim.

## Model

Cox model, Efron ties, `survival` 3.8-6 (pinned). Arm is coded 0 for everolimus and 1 for nivolumab:

log HR(nivolumab against everolimus, at score z) = bA + bAS·z

Fitted as PFS ~ arm + score + arm × score + adjustment set.

- **Scaling.** The score z uses the pooled mean and sample SD of the score-eligible patients of both arms. The same scaling is reused in every sensitivity. A zero-variance panel is not eligible.
- **Estimand.** bAS, the change in the log hazard ratio per score SD, with a Wald 95% interval. An interval spanning zero is "inconclusive". Rank and convergence checks are reported.
- **Adjustment set.** MSKCC group and prior therapy, as categorical covariates, not strata. They were chosen for prognostic and design relevance, and after seeing the RNA-subset imbalance in prior therapies (42% and 29% with at least 2); that order is stated. The trial's real stratification factors are to be checked (gate 3). From memory, not confirmed in the repo: region, MSKCC risk and number of prior antiangiogenic regimens. Adjustment cannot restore randomisation after a problematic subset selection.
- **Sensitivities.** The unadjusted model on the same complete cases, and the unadjusted model on all endpoint-eligible patients.
- **Absolute results.** PFS at 12 months by arm and their difference, at z = −1, 0 and +1, averaged over the observed covariates of the complete cases, with bootstrap intervals and support checks. A seed stream is added to the register before release.

## Changing effects over time (mandatory sensitivity)

Hazards may not stay proportional with ICI, and a test cannot prove that they do. So this analysis is always reported, with no p-value trigger:

- One start–stop Cox model (`survSplit`, proper risk sets), with arm, score and arm × score allowed to differ before and after 6 months.
- Interval-specific estimates with uncertainty, and late-period event counts.
- Six months is a declared working choice, not an estimated change point. It is never tuned from these curves.
- Diagnostic plots and scaled Schoenfeld results for all terms.

The constant bAS is read as an average over follow-up. If the two periods differ materially, a constant near zero is not reported as "no modification", and the time-varying result is shown alongside it.

## Gates before release

1. **Endpoint specification from a source:** time origin and units, `PFS_CNSR` coding, the definition of progression and death, assessor, censoring rules, missed assessments, new treatment, analysis cutoff, and time and status validation. If the coding or the endpoint cannot be identified, A-RCT stops.
2. **Assessment schedule:** the same in both arms.
3. **Trial design:** assigned against received treatment in `Arm`, and exact stratification factors. An unavailable factor is listed.
4. **Specimens and processing:** the signed Stage 1 items on provenance, selection, QC and batches. Undocumented items qualify the result as exploratory. Demonstrated outcome-dependent selection or preprocessing stops the analysis.
5. **Prior exposure:** the workbook holds author signature scores (for example `Javelin`, `Merck18`), and the authors analysed these patients. The result is not independent of that work, and the prior-exposure audit records it.
6. **Register:** a register entry and a Part 4 release checklist.

## Precision

If `PFS_CNSR` = 1 marks an event, the subset has about 222 events (117 everolimus, 105 nivolumab). The rough interaction SE is 0.134. That gives about 80% power (two-sided 5%) for a ratio of hazard ratios near 1.46 per SD, or 0.69 in the other direction. Smaller effects have less power under these assumptions: unit score variance in the risk sets, adequate arm overlap, valid censoring, proportional hazards and little information lost. This is a hypothetical calculation that uses no score data. If the coding were reversed, there would be only 28 events and a detectable ratio near 2.89.

## Claim

If supported: "The estimated nivolumab-versus-everolimus PFS hazard ratio varied with the archival M2 expression score in this biomarker subset." This concerns conditional hazards, not absolute benefit or an individual treatment effect. The specimens are mostly archival, collected a median of about 1.5 to 2 years before trial therapy among patients with known timing. The result concerns kidney cancer after earlier therapy. It does not show that a gene causes response, and it does not establish a general ICI-specific mechanism.

## Signature

- [ ] Change 1, A-RCT endpoint
