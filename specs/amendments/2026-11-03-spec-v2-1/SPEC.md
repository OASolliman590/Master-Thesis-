# Spec v2.1: composition, naive-to-ICI bridge, single-cell placement (3 Nov 2026)

**Status: SIGNED by the user on 3 Nov 2026, with SPEC v2.1 of A, A.1 and B ("I sign all three").** Decisions: `docs/wayfinding/SPEC_V2_1_20261103/MAP.md` (grilling rounds 1-2). Evidence: `docs/research/SPEC_V2_1_EVIDENCE_20261103.md`. The edited sections live in `specs/A/SPEC_v2.md` (4.3, 4.4, 8, 10-12) and `specs/B/SPEC_v2.md` (2, 6, 8-10).

## Problem Statement

The v2 specs left three gaps. Paper A described immune programmes without asking how much of them is cell infiltration, and its only composition handle was an RNA-derived adjustment of RNA outcomes, which is circular. Paper B measured methylation–expression association in untreated TCGA tumours but never connected it to the ICI-treated tumours that Paper A studies. And the single-cell data, already downloaded and qualified, were nearly invisible in the specs.

## Solution

- **Paper A, A-COMP:** quanTIseq (primary) and CIBERSORTx LM22 relative (secondary, after registration) fractions in 12 linear RNA-seq cohorts, related descriptively to response (also as added value over CYT/GEP) and to the 11 programmes. Never a predictor, an A-P2 input or a covariate; the RNA-derived adjustment in A 4.3 is removed.
- **Paper B, naive-to-ICI bridge:** (a) module preservation of TCGA Tier 1+2 modules in ICI cohorts with at least 40 patients, raw and with purity and the immune axis removed; (b) percentile position of ICI tumours in the same cancer's TCGA distribution, recount3 subset as the main analysis; (c) concordance of TCGA methylation coefficients with frozen A-BIO response effects, after A-BIO is frozen.
- **Paper B, composition:** quanTIseq primary (shared version with A), CIBERSORTx secondary, MethylCIBERSORT secondary (methylation-state relations and cross-modality agreement with quanTIseq).
- **Single-cell:** its own section in A and B and its own PDF chapter. New in B: each methylation-associated gene is labelled tumour-intrinsic, infiltrate-expressed, mixed or below detection from the prostate reference.

## User Stories

1. As the thesis author, I want composition fractions for every eligible Paper A cohort, so that I can say how much of each programme tracks infiltration.
2. As the thesis author, I want each fraction's response association reported as added value over CYT and GEP, so that I do not present one immune axis twice.
3. As an examiner, I want fractions never used as covariates for RNA outcomes, so that adjusted effects are not circular.
4. As an examiner, I want quanTIseq and CIBERSORTx fractions labelled as different quantities (share of tumour versus share of immune cells), so that they are not confused.
5. As the thesis author, I want the Paper B prostate genes linked to ICI-treated tumours, so that Paper B speaks to the ICI setting without claiming prediction.
6. As an examiner, I want the bridge to be outcome-free except for the frozen A-BIO lookup, so that no test set is reused.
7. As an examiner, I want position comparisons made on one processing pipeline, so that processing differences are not read as biology.
8. As the thesis author, I want a methylation-based composition estimate compared with the RNA-based one, so that composition is checked across data types.
9. As a reader, I want to see where the single-cell data are and what each atlas is used for, so that its role is clear.
10. As an examiner, I want each methylation-associated gene labelled by its expressing compartment, so that infiltrate signals are not read as tumour silencing.
11. As the thesis author, I want CIBERSORTx reported as "not run" if I do not register, so that its absence does not block anything.
12. As the supervisor, I want the added hours and the cut order stated, so that the plan stays within budget.

## Implementation Decisions

- One pinned quanTIseq version and option set (TIL10, lsei, tumour mode, mRNA scaling) shared by both papers; input is non-log TPM from the A-P2 TPM routes; array mode only for CPC-GENE, labelled.
- Fractions are computed and compared within cohort; synthesis uses the A-BIO per-study effect machinery (Hedges g, REML with modified Knapp–Hartung, BH FDR 10%).
- A-COMP cohorts: Riaz, Hugo, GSE168204, Liu, Gide, Van Allen, GSE135222, GSE176307, Kim, GSE145996, GSE165278, GSE218989. Excluded: arrays, NanoString, targeted panels, Braun, IMvigor210.
- Bridge pairs: melanoma cohorts → SKCM, GSE176307 → BLCA, Kim → STAD, lung cohorts → LUAD/LUSC; KIRC, HNSC, LIHC reported as "no linear ICI cohort". Pairs and the single-cell attribution rule are frozen before unblinding.
- No single-cell data are used as a deconvolution reference or benchmark; SC-2 stays cut.
- Budget: Paper A +15 hours; Paper B about 210 hours (was 180). Over-run cuts: multi-omics, then bridge position (b), then deconvolution secondaries.

## Testing Decisions

- Test behaviour at the highest seam, the build command that writes per-cohort fraction tables: a synthetic TPM matrix with known mixtures recovers the expected ranking; log-scale input is refused; IMvigor210 is refused; excluded representations are refused with a reason.
- The bridge is tested on synthetic matrices: identical structure gives high preservation, permuted genes give low preservation; the concordance step refuses to run while A-BIO is not frozen.
- Prior art: `tests/a_p2/test_build.py` (input build, scale checks, refusal of the final test).

## Out of Scope

Single-cell deconvolution or pseudobulk benchmarking (SC-2), single-cell response testing (SC-3), methylation imputation from expression, composition analyses of on-treatment change (A.1), new data acquisition, spatial data.

## Further Notes

Finotello 2019 already analysed GSE91061 with quanTIseq, so the Riaz composition result is not independent of that report. The Lin 2026 signature validation cohorts must be audited for overlap with ours and IMvigor210 (Paper A gate 3).
