# Wayfinder: spec v2.1 (3 Nov 2026)

Local map only. The journey fits one session, so no GitHub issues are opened; each ticket below is resolved in this file.

## Destination

Signed-ready SPEC v2.1 for Papers A, A.1 and B and a rebuilt PDF, covering three user requests of 3 Nov 2026:
1. Paper A: add a cell-composition analysis (quanTIseq; CIBERSORTx if access is obtained) on the RNA-seq cohorts, descriptive, never a covariate for RNA outcomes.
2. Paper B: include Paper A's ICI RNA-seq cohorts next to the TCGA comparators and measure the association between them.
3. Make the single-cell data visible: where it sits in A and B.

## Notes

Skills: research, grilling, domain-modeling (via grill-with-docs), to-spec. Lean process (one review at most, no loops). Signed constraints that bound the answers:
- Single-cell plan (signed 2 Nov): single-cell is descriptive only; SC-2 (deconvolution with a single-cell reference) is cut permanently; SC-3 response testing is cut.
- IMvigor210 is UNTOUCHED_FINAL_TEST in every analysis.
- Paper B claim ceiling: no ICI-response prediction in prostate.
- Paper A 4.3: composition adjustment is a separate sensitivity (superseded by T2: removed).

## Tickets

| Ticket | Type | Blocked by | Status |
| --- | --- | --- | --- |
| T1 What evidence supports quanTIseq/CIBERSORTx on our cohorts, cohort linking, single-cell roles? | research | none | closed |
| T2 What does the Paper A composition analysis relate fractions to (response? programmes? both), on which cohorts? | grilling | none | closed |
| T3 Is quanTIseq in A consistent with the SC-2 cut? | grilling | none | closed |
| T4 What does "association between TCGA and our cohorts" mean in Paper B (estimand), and does it touch outcomes? | grilling | T1 | closed |
| T5 Where does single-cell appear in the v2.1 specs and PDF? | grilling | none | closed |
| T6 Write v2.1 specs and rebuild the PDF | task | T2-T5 | closed |

## Decisions so far

- T1 research: [SPEC_V2_1_EVIDENCE_20261103.md](../../research/SPEC_V2_1_EVIDENCE_20261103.md). quanTIseq needs linear TPM; fractions are compared within cohort only; TIL10 shares almost no genes with our panels, but fractions and programmes form one immune axis; module preservation is the cleanest outcome-free bridge, run also after removing purity/immune axis; methylation imputation from expression is circular and rejected; single-cell labels genes as tumour-intrinsic or infiltrate-expressed.
- T2 (round 1, Q1-Q3): Paper A composition relates quanTIseq fractions to response (Hedges g, reported as added value over CYT/GEP) and to the 11 programmes; supporting only, never a predictor or A-P2 input; 12 linear RNA-seq cohorts on the A-P2 TPM routes. The RNA-derived composition adjustment in A 4.3 is removed.
- T3 (Q4, Q8): consistent with the SC-2 cut, since quanTIseq uses its own fixed signature; no single-cell pseudobulk benchmark.
- T4 (Q5, Q6): quanTIseq primary in both papers, one version; CIBERSORT(x) and MethylCIBERSORT added as secondaries; the naive-to-ICI bridge uses all three of structure, position and concordance.
- T5 (Q7): single-cell gets its own section in each spec and its own PDF chapter, including tumour-intrinsic vs infiltrate labelling of Paper B genes.
- T6: specs written (change spec issue #25), PDF rebuilt; all three v2.1 specs signed by the user on 3 Nov 2026. Map complete.

## Not yet specified

None. (The bridge budget was settled in round 2: its own 22-hour line.)

## Out of scope

New data acquisition (Paper A acquisition closed 2 Nov); spatial data (user choice 2 Nov); single-cell response testing (SC-3 cut).
