# Wayfinder: Paper A meta-analysis module and standard RNA/single-cell analysis (3 Nov 2026)

Local map. This effort may span more than one session, so the tickets below can be mirrored to GitHub issues once the user approves the spec.

## Destination

A signed spec (published with to-spec) for two analysis modules:
1. **A-META:** a molecular meta-analysis for Paper A, synthesised per cancer and per immunotherapy class (gene- and programme-level), built on per-study effects.
2. **Standard analysis:** typical bulk RNA-seq analysis (QC, PCA, differential expression, enrichment, scoring) and single-cell analysis (QC, normalisation, PCA/UMAP, compartments, pseudobulk) for the signed cohorts and atlases.

The spec names the codebases we reuse, the module seams in `tools/`, the tests, and what stays out.

## Notes

Skills: research, wayfinder, improve-codebase-architecture (with codebase-design), grilling, domain-modeling, to-spec. Lean process. Signed constraints:
- A-BIO settings D4-D6: Hedges g; REML with modified Knapp–Hartung; three endpoint families never pooled; NB GLM (DESeq2 or edgeR) or limma; BH FDR 10%; synthesis only within an effect type.
- Raw expression is never merged across studies.
- IMvigor210 is UNTOUCHED_FINAL_TEST in every module.
- Single-cell plan (signed 2 Nov): descriptive only; no single-cell-reference deconvolution (SC-2). SC-3 (single-cell response testing) was cut there and is reinstated by this effort.
- Genome-wide lists never feed A-P2.

## Tickets

| Ticket | Type | Blocked by | Status |
| --- | --- | --- | --- |
| M1 Which codebases exist for ICI molecular meta-analysis (per cancer, per drug class) and for standard bulk/single-cell analysis? | research | none | closed |
| M2 Where do the new modules attach in `tools/`, and which shared logic must move first? | research (architecture walk) | none | closed |
| M3 What does "per immunotherapy" mean: drug target, mono vs dual, line of therapy? Which strata are estimable? | grilling | M1 | closed |
| M4 Which units are meta-analysed: panels, single genes (genome-wide), pathways? Which effect sizes? | grilling | M1 | closed |
| M5 What does "typical analysis" include per data type, and how does it relate to the signed single-cell limits? | grilling | M1 | closed |
| M6 Language and runtime: R (Bioconductor) vs Python, and the bridge | grilling | M1, M2 | closed |
| M7 Write the spec and publish it | task | M3-M6 | closed |

## Decisions so far

- M2 architecture walk: the loader interface lacks typed cancer, normalised drug class and measurement representation; TPM routes, aliases, panel scoring and response labels sit inside a_p2's build(); no R bridge exists. Candidates: cohort view (strong), shared representation and scoring module (strong), R bridge adapter, per-study effect + synthesis modules, pseudobulk in the loader layout. Report: architecture-review-20261103-analysis.html (temp dir).
- M1 research: [ANALYSIS_CODEBASE_SURVEY_20261103.md](../../research/ANALYSIS_CODEBASE_SURVEY_20261103.md). metafor matches the signed method (escalc SMD, rma REML + test="adhoc"); PredictioR is the layout reference (per-study → meta → per-cancer/per-treatment) but uses REML without KH and pools small groups as "Other"; statistics in R 4.6/Bioc 3.23 with renv, called by Rscript subprocess; DESeq2 or edgeR + limma + fgsea + singscore + immunedeconv; Lin atlas stays in R (no h5ad conversion), prostate h5ad in scanpy.
- M3 (Q1-Q2): drug-class strata anti-PD-(L)1 (main), anti-CTLA-4, dual (low-k, labelled); two one-way stratifications plus a melanoma cancer × drug table; subgroup test only with k ≥ 10.
- M4 (Q3-Q4): units are genes (genome-wide), the 11 panels and pathways; synthesis effect is Hedges g of within-study log expression; per-study DE kept as within-study output; gene synthesised only with k ≥ 3.
- M5 (Q5, partial): bulk per-study QC, PCA, DE, fgsea, panel correlations. User addition: save every per-dataset output on the SSD, and plan presentation and visualisation in the papers, for A and B.

## Not yet specified

None. (Figures settled in Q14-Q15; A-COMP fractions enter A-META as one more unit family.)

## Out of scope

New data acquisition; raw-read reprocessing of all studies (rejected earlier as too risky); cell-level (non-pseudobulk) response tests; touching IMvigor210.
