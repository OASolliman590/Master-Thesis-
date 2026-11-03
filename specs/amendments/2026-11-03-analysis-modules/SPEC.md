# Analysis modules: A-META and standard bulk/single-cell analysis (3 Nov 2026)

**Status: SIGNED by the user on 3 Nov 2026 ("I sign it"), including the reinstatement of SC-3.** Decisions: `docs/wayfinding/ANALYSIS_MODULES_20261103/MAP.md` (grilling Q1-Q15). Evidence: `docs/research/ANALYSIS_CODEBASE_SURVEY_20261103.md`. Architecture review: five candidates, all adopted, pseudobulk last. Signed constraints carried: A-BIO D4-D6, three endpoint families never pooled, raw expression never merged across studies, IMvigor210 UNTOUCHED_FINAL_TEST, single-cell-reference deconvolution (SC-2) stays cut. **SC-3 (single-cell responder versus non-responder DE) is reinstated by the user on 3 Nov 2026**, amending the signed single-cell plan; it needs the user's signature with this spec, genome-wide lists never feed A-P2.

## Problem Statement

Paper A's A-BIO describes per-study panel effects and a synthesis, but there is no module that does it, and no gene- or pathway-level synthesis stratified by cancer and by immunotherapy class. There is also no standard per-dataset analysis (QC, PCA, differential expression, enrichment) for the bulk cohorts of Papers A and B, nor for the two single-cell atlases. The loader does not return cancer, drug class or measurement representation in a typed form, and the TPM, alias, scoring and response-label logic sits inside one A-P2 function, so each new analysis would copy it. Nothing in `tools/` calls R, although the methods that match the signed plan are R packages.

## Solution

1. **Groundwork.** A cohort view returns, for each signed cohort, expression, clinical rows and typed metadata: cancer, normalised drug class (anti-PD-(L)1, anti-CTLA-4, dual), measurement representation (unit, transform, platform) and endpoint families. A shared representation and scoring module provides TPM routes, the alias table, frozen panel scores, singscore pathway scores and endpoint labels; A-P2 becomes a caller.
2. **R bridge.** One adapter runs pinned R scripts (R 4.6, Bioconductor 3.23, renv) by `Rscript --vanilla`, exchanging TSV + JSON, recording input, script and output hashes and `sessionInfo()`. A fake adapter serves the tests.
3. **Per-study effect + synthesis (A-META).** For each study, endpoint family and unit (gene, panel, Hallmark pathway, A-COMP fraction), the effect module returns Hedges g with SE and n (R minus NR, within-study log expression). The synthesis module runs metafor `rma(method = "REML", test = "adhoc")` per stratum:
   - per cancer; per drug class (anti-PD-(L)1 main; anti-CTLA-4 and dual labelled low-k); a melanoma cancer × drug table; then across cancers with the stated weighting;
   - subgroup difference (meta-regression F test) only when k ≥ 10;
   - k = 1: the study effect alone; k = 2: both effects plus a tentative pooled estimate, no prediction interval; fixed-effect sensitivity (Jackson 2017);
   - genes synthesised only with k ≥ 3; BH FDR 10% within each family (genes, panels, Hallmark pathways, fractions), per stratum and endpoint family.
   - Pathways: (i) singscore Hallmark (50) per sample → Hedges g → synthesis (formal); (ii) fgsea on the meta-analysed gene ranking, Hallmark and Reactome (descriptive).
4. **Standard bulk analysis per dataset (A and B).** QC (library size, detected genes, outliers), PCA (DESeq2 vst for counts, log scale otherwise; coloured by response, batch, site, platform), DE (DESeq2 for integer counts; limma-trend for log TPM/FPKM, arrays and NanoString; within-study batch as a covariate), fgsea on the DE ranking, panel correlation matrix. Paper B datasets (TCGA-PRAD, CPC-GENE, 8 comparators, ICI methylation cohorts): methylation QC (beta distributions, detection failures), PCA of methylation and of expression, immune-score distributions; no tests beyond the signed B spec.
5. **Standard single-cell analysis.** Prostate h5ad in Python (scanpy): QC, normalisation, HVG, PCA/UMAP, Leiden, marker check of author labels. Lin atlas in R (qs2 + Seurat; never converted to h5ad): QC audit, marker check, compartment expression. Pseudobulk (raw UMI sums per patient × compartment) is written as a cohort view so the bulk QC/PCA code runs on it.
7. **SC-3: single-cell responder versus non-responder DE (reinstated, exploratory).**
   - **Unit:** the patient (independent biological unit), never the cell. Baseline, ICI-only samples; one specimen per patient; pseudobulk per patient × broad compartment with the signed thresholds (NA below 15 cells or 5,000 UMI).
   - **Eligible cohorts:** at least 3 responders and 3 non-responders with an eligible profile in that compartment. On the atlas table: RECIST (HNSC_vanderLeun, SKCM_this study, BCC_Yost), pathology ± RECIST (TNBC_Shiao, SKCM_Plozniak, CRC_Chen ICI-only arm if counts allow). Too few or no usable metric: HCC_Guo, CRC_Li, HNSC_Luoma, HCC_Ma, PCa_Hawley.
   - **Response metric families never mixed:** RECIST; pathological response; **T-cell expansion** (BRCA_Bassez1, BRCA_Bassez2, HNSC_Franken) is analysed separately and labelled "expansion", never "response", because it is not a clinical outcome.
   - **Per cohort and compartment:** DESeq2 on pseudobulk counts (design ~ response), BH FDR 10% within cohort × compartment; plus the 11 panels, M5/M6 genes and compartment cell fractions as Hedges g.
   - **Across cohorts:** the A-META effect and synthesis modules, within one metric family and one compartment, with the same small-k labels (k = 1 alone, k = 2 tentative).
   - **Guards:** exploratory and supporting; never selects or changes bulk features, A-META gene sets or A-P2; overlap with bulk cohorts (head and neck vs GSE159067) and with Lin 2026's own analyses is reported as non-independent; with 4-24 patients per arm only large effects are detectable, and a null is "inconclusive".
6. **Outputs and presentation.** Every per-dataset output goes to the SSD at `Master_Thesis/results/<A|B>/<dataset>/{qc,pca,de,scores,gsea}/` with a manifest; A-META outputs to `results/A/meta/`. Patient-level files stay off Git; patient-free summaries and figures are copied to the repo `results/`.

## User Stories

1. As the thesis author, I want one per-study effect for every gene, panel, pathway and fraction, so that all syntheses use one effect type across platforms.
2. As the thesis author, I want syntheses per cancer and per drug class, so that I can see whether response biology differs by context.
3. As an examiner, I want anti-CTLA-4 and dual results labelled low-k, so that tiny strata are not over-read.
4. As an examiner, I want k = 1 and k = 2 strata reported by a rule fixed in advance, so that small strata are handled consistently.
5. As an examiner, I want endpoint families never pooled, so that ORR and clinical benefit are not mixed.
6. As the thesis author, I want a subgroup-difference test only with enough studies, so that I do not claim differences from noise.
7. As the thesis author, I want gene-level FDR within each stratum and family, so that discoveries are controlled.
8. As the thesis author, I want Hallmark pathways meta-analysed formally and Reactome enrichment shown descriptively, so that pathway claims have one formal source.
9. As the thesis author, I want a QC, PCA and DE report for every dataset, so that I can show the data are sound before synthesis.
10. As an examiner, I want PCA coloured by response, batch, site and platform, so that confounding is visible.
11. As the thesis author, I want DESeq2 for counts and limma for other scales, so that each study is analysed on its own scale.
12. As an examiner, I want within-study batch in the design and never a cross-study correction, so that between-study differences are handled by the meta-analysis.
13. As the thesis author, I want the Lin atlas processed in R without conversion, so that 1.5 million cells do not break a converter.
14. As the thesis author, I want pseudobulk profiles in the same layout as bulk cohorts, so that QC and PCA code is reused.
15. As the thesis author, I want single-cell responder versus non-responder DE per compartment, so that I can see in which cell types response-associated genes differ.
15b. As an examiner, I want that analysis at patient level, within one response metric, labelled exploratory, so that pseudoreplication and metric mixing are avoided.
16. As the thesis author, I want every output saved per dataset on the SSD with a manifest, so that I can find and reproduce any figure.
17. As a reader, I want patient-free summaries in Git and patient-level files outside it, so that privacy rules hold.
18. As the thesis author, I want drug class normalised from the many raw labels, so that strata are correct.
19. As the thesis author, I want A-P2 to use the shared scoring module, so that its features do not change when the code is reorganised.
20. As a maintainer, I want R calls to go through one adapter with a fake, so that Python tests run without R.
21. As a maintainer, I want R and Bioconductor versions pinned, so that results are reproducible.
22. As an examiner, I want IMvigor210 refused by every new module, so that the final test stays untouched.
23. As the thesis author, I want a figure plan for both papers, so that analysis outputs map to the manuscript.

## Implementation Decisions

- **Modules:** cohort view (deepened loader interface); representation and scoring; R bridge (real and fake adapters); per-study effect; synthesis; bulk standard analysis; single-cell standard analysis (Python adapter for h5ad, R adapter for qs2); pseudobulk writer emitting a cohort view.
- **Cohort view contract:** expression matrix (feature × patient), clinical rows, and typed fields `cancer`, `drug_class` (controlled vocabulary: ANTI_PD_L1_AXIS, ANTI_CTLA4, DUAL_PD1_CTLA4, OTHER_EXCLUDED), `representation` (unit, transform, platform), `endpoint_families`. Values come from the field map and REGISTRY; an unmapped raw drug label is an error, never a guess.
- **Effect contract:** one row per study × endpoint family × unit: g, SE, n_R, n_NR, representation, drug-class stratum, cancer. Panels and pathways need complete gene coverage (alias table applied).
- **Synthesis contract:** effect table + stratum definition → estimate, 95% CI, τ², I², k, p, BH q, label (`single_study`, `tentative_k2`, `low_k`, `standard`). metafor `escalc(measure = "SMD")`, `rma(method = "REML", test = "adhoc")`; `mods = ~ stratum` only with k ≥ 10.
- **R side:** scripts for DESeq2, limma, metafor, fgsea (msigdbr), singscore, immunedeconv (quanTIseq, shared with A-COMP), and the Lin atlas QC/pseudobulk; one `renv.lock`.
- **Python side:** orchestration, cohort view, Hedges g inputs, scanpy for the prostate atlas, figures.
- **Storage:** SSD `results/` tree as above, one manifest per dataset folder (inputs, script hashes, package versions, outputs).
- **Paper A figures:** (1) cohort overview: studies × cancer × drug class × platform with n; (2) panel forest plots per cancer and per drug class; (3) gene-level volcano (pooled g vs FDR) and heatmap of study-level g for top genes; (4) Hallmark meta-analysis with fgsea; (5) A-P2 ROC and ΔAUROC; (6) single-cell compartment dot plot; (7) SC-3 per-compartment responder versus non-responder effects (heatmap of g by cohort × compartment for the panels, with metric family marked). Supplement: per-dataset QC + PCA + DE volcano grid; A-COMP.
- **Paper B figures:** (1) design; (2) primary ΔR² per gene with CIs and the median; (3) cold versus hot across cancers; (4) naive-to-ICI bridge; (5) composition and single-cell labels. Supplement: per-dataset methylation and expression QC/PCA.
- **Budget (estimate):** groundwork 12 h; R bridge 6 h; effect + synthesis 15 h; gene and pathway meta 15 h; per-dataset bulk analysis A and B 25 h; single-cell standard analysis 12 h; SC-3 12 h; pseudobulk view 6 h; figures 15 h; about 117 h in total, on top of the v2.1 budget (about 645 h). Cut order if needed: Reactome enrichment, then the melanoma cancer × drug table, then cross-cohort SC-3 synthesis (per-cohort SC-3 stays).

## Testing Decisions

- Test external behaviour through each module's interface only, with synthetic fixtures; no patient data in tests.
- Cohort view: every signed cohort returns a cancer, a controlled drug class and a representation that match REGISTRY; an unknown drug label fails; IMvigor210 is refused.
- Representation and scoring: the existing 40 a_p2 tests move to this interface; A-P2 features are byte-identical before and after the move.
- Effect: Hedges g, SE and n match hand-computed values on a toy cohort; incomplete panels are refused.
- Synthesis: the fake R adapter returns canned metafor output for unit tests; one integration test runs real metafor on a fixed table and matches published metafor examples to 1e-6; k = 1 and k = 2 labels; families and endpoint families never mixed.
- R bridge: hashes and `sessionInfo()` recorded; a failing script raises with its stderr.
- Bulk analysis: DESeq2 and limma choice follows the representation; outputs land in the right `results/` folder with a manifest.
- Single-cell: pseudobulk sums equal cell-level UMI sums on a toy object; NA below 15 cells or 5,000 UMI.
- SC-3: the unit is the patient (a toy object with many cells per patient gives the same n as patients); different response metrics are never combined; T-cell expansion is never labelled response; cohorts below 3 per arm are refused with a reason.
- Prior art: `tests/a_cohorts/test_loader.py` (tmp runtime, IMvigor lock), `tests/a_p2/test_build.py` (pure helpers).

## Out of Scope

Single-cell-reference deconvolution (SC-2); cell-level (non-pseudobulk) responder tests; raw-read reprocessing (nf-core); cross-study batch correction; WGCNA in Paper A; conversion of the Lin atlas to h5ad; any use of IMvigor210 outside the A-P2 final step; changes to the signed A-P2 model.

## Further Notes

PredictioR (bhklab) is the layout reference, but its REML without Knapp–Hartung and its "Other" pooling are not copied, and its licence (GPL-3 vs MIT) is unresolved, so no code is reused. Bareche 2022 and Litchfield 2021 code have no licence and are read only.
