# Integrated plan amendment — 29 October 2026

**Status: SIGNED by the user, 29 Oct 2026.** This adds to RC2 and the 16 Oct amendment; no earlier spec file changes. It records what was decided in chat on 29 Oct, plus the serious fixes from one Astra review (`REVIEW_ASTRA_HIGH.md`). It does not by itself start any response analysis; each analysis still needs its own release.

## What we decided

**Cohorts**
- Immunotherapy plus a non-immunotherapy drug: left out of the A/B response analyses and kept in the combination list (`docs/decisions/COMBINATION_COHORTS_20261029.md`).
- Dual immunotherapy: kept, with each patient tagged by drug class.
- Mixed studies: the immunotherapy-only arm feeds A/B, and the two arms are compared within the study.
- A study reserved for final testing stays protected as a whole family: all arms, timepoints and data types, in every paper.

**Paper A**
1. **A-P2 stays the single formal primary** (learned score vs CYT, AUROC on independent test patients). It runs only once there are enough independent development studies and a protected test set; otherwise it is reported as "not yet possible".
2. **Locked panels: the main biology result.** The 11 panels, with their caveats. The exact list of hypotheses is frozen before outcomes: composite scores, plus each M5 gene and each M6 regulator counted separately.
3. **Endpoint sensitivity.** The same score on the same patients under each response definition, reported as a paired difference, not "significant here, not there". It starts with CYT, then the locked panels.
4. **Genome-wide differential expression:** discovery only, with FDR. It is done per study, then combined per cancer and across all cancers.
5. **Equation:** the frozen A-P2 model is published as its equation (coefficients and normalisation). Linking it to PK/PD is future work.

**Paper A.1:** unchanged. It adds the within-study arm comparison for randomised mixed studies.

**Paper B**
1. **B-P stays the primary and is isolated.** TCGA-PRAD fit → CPC-GENE test, unchanged. Nothing from B-MX may alter it.
2. **B-MX (new, secondary).**
   - TCGA for the cancer types of the admitted A cohorts, plus prostate.
   - Matched RNA + methylation is the core; miRNA and RPPA are added where coverage allows.
   - MOFA+ / DIABLO are exploratory.
   - The gene list comes from Paper A's frozen results and is frozen before any TCGA analysis.
3. **Prostate transfer.** Score TCGA-PRAD with the frozen A programmes, looking within prostate tumours.
4. **B-V (new, secondary): checks the chain in the epigenetic-drug + ICI cohorts.**
   - Before vs after the epigenetic drug: GSE248014's entinostat lead-in, and the guadecitabine studies.
   - The randomised GSE343570, pembrolizumab ± vorinostat, as an exploratory check.
   - These cohorts never enter the A/B response analyses.

**Order:** A and B run in parallel. C follows; D stays deferred. Running in parallel does not skip any freeze or release gate.

## Rules from the review (each one keeps a result honest)

1. **Meta-analysis with few studies.**
   - 1 study: report it alone.
   - 2–3 studies: combine them tentatively (modified Knapp–Hartung method), and give no "prediction interval" for future studies.
   - Patient numbers never replace study numbers.
2. **Never mix effect types.** Count-model effects and log-expression effects are pooled only within their own type. Hedges' g is used only as a pre-declared cross-platform check.
3. **No leakage into the predictor.** A-P2 keeps its own feature rules. Differential-expression gene lists are not fed into it, unless the whole selection is repeated inside every training fold.
4. **"Equal cancer weights"** applies to A-P2 exactly as frozen. For the biology summaries, the weighting is stated explicitly.
5. **Endpoints.** Each clinical-benefit definition is its own endpoint, never pooled under one "binary" heading. Unknown durability does not count as non-response.
6. **Small or confounded cohorts.** Check that an adjustment model can be fitted at all before using it (GSE168204: 10 patients, 4 batches). If response can't be separated from batch, say it is not estimable.
7. **Methylation wording.** Results are "association supported", "inconclusive" or "not measured", never "methylation-controlled". The models predict expression from methylation without using the same RNA as input, and adjust for tumour purity.
8. **Prostate transfer.** "Low" must be relative to a stated reference, by default other prostate tumours. Low RNA is not HLA loss.
9. **B-V attribution.**
   - Only GSE248014's lead-in isolates the epigenetic drug alone. Other after-samples reflect both drugs.
   - HDAC inhibitors are not assumed to demethylate DNA.
   - Each gene's expected direction is fixed in advance; exclusion genes are not expected to rise.
   - The test is one change per patient, on a few pre-declared scores. Holm correction is used, and two-sided intervals are always shown.
   - With 7–18 pairs, only large effects can be detected, so a null result is "inconclusive".
   - The published results of these trials are already known, so this is called a pre-specified secondary analysis, not blind replication.
10. **GSE343570.** The molecular arm effect is estimated as the follow-up score adjusted for the baseline score. Response × baseline score is one exploratory interaction (Firth logistic regression).

## Honest status at signing

- Admitted: GSE168204 (10) and Hugo (26).
- Riaz (51) is waiting for the user's signature.
- A-P2 is not yet possible. It needs more independent response-rate (ORR) studies, for example IMvigor210, Liu or Gide once admitted, plus a protected test set.
- B-P's real CPC-GENE sample is about 72–114 patients, not 210.

## Signature

Signed by: omar soliman (thesis author), in chat ("Sign it")  Date: 2026-10-29
