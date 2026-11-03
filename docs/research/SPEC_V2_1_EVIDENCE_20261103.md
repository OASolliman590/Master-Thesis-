# Spec v2.1 evidence, 3 Nov 2026

Focused literature and documentation check for three spec v2.1 questions: (1) bulk immune deconvolution in the Paper A ICI cohorts, (2) linking the Paper B TCGA methylation–expression association to ICI cohorts that have no methylation data, and (3) what single-cell data can and cannot do for both papers. Literature facts come from PubMed records and, where stated, PubMed Central full text (source: PubMed; DOI links given with each claim). Tool facts come from official documentation or source files, with the URL given. Claims I could not confirm from a primary record are marked **UNVERIFIED**. No cohort data were downloaded or opened. The only files fetched were the public quanTIseq signature files and the column header of the public UXM atlas file, both listed in §1.4 and §3.3.

---

## 1. quanTIseq and CIBERSORTx on bulk ICI expression

### 1.1 Input requirements

**quanTIseq** (Finotello 2019, PMID 31126321, [doi:10.1186/s13073-019-0638-6](https://doi.org/10.1186/s13073-019-0638-6)) estimates fractions of ten immune cell types plus an "Other" (uncharacterised) fraction from bulk RNA-seq. It was validated against simulated data, flow cytometry and IHC. Requirements and options, from the official docs (<https://icbi.i-med.ac.at/software/quantiseq/doc/>) and the paper's full text (PMC6534875):

- Input is a tab-delimited matrix with gene symbols in the first column. The docs require it to be "on non-log scale" and in TPM. The full pipeline starts from FASTQ and quantifies with Kallisto, so supplying pre-computed TPM is a departure from the validated path. The paper warns that it "might show lower accuracy on pre-computed expression data".
- `--tumor=TRUE` drops signature genes that are aberrantly high in TCGA tumours. The docs "highly recommend" it for tumour data.
- `--arrays=TRUE` is the microarray mode. It turns off gene removal, so the full 170-gene matrix is used, because arrays "often lack some signature genes". The paper describes preprocessing array data back to natural scale and quantile-normalising it.
- `--mRNAscale=TRUE` (the default, and recommended) divides fractions by per-cell-type mRNA-content factors derived from PSMB2. **Only `--method=lsei` estimates "Other"**, and only lsei gives fractions of all cells. The robust-regression methods give fractions of immune cells only.
- The paper presents the output as absolute fractions, comparable both between samples and between cell types. The immunedeconv documentation (<https://omnideconv.org/immunedeconv/articles/immunedeconv.html>) likewise lists quanTIseq, EPIC and CIBERSORT absolute mode under "both". It notes that CIBERSORT absolute mode "generates a score in arbitrary units", that plain CIBERSORT supports between-cell-type comparison only, and that MCP-counter, xCell and TIMER support between-sample comparison only. The same page states the shared input contract: TPM, "not log-transformed", HGNC symbols.

**CIBERSORTx** (Newman 2019, PMID 31061481, [doi:10.1038/s41587-019-0114-2](https://doi.org/10.1038/s41587-019-0114-2); protocol chapter Steen 2020, PMID 31960376, [doi:10.1007/978-1-0716-0301-7_7](https://doi.org/10.1007/978-1-0716-0301-7_7)):

- Mixture files must be "in linear space (not log2) without negative or missing values". Signature and mixture "should be normalized identically" (protocol chapter). Missing signature genes are "generally acceptable".
- The paper describes the method as "independent of expression profiling platform or tissue preservation state". The protocol lists microarray mixtures as valid input, and the paper analysed NanoString data "with batch correction in non-log linear space" (full text, PMC6610714).
- **B-mode** adjusts the *mixture* toward a bulk-sorted, microarray or SMART-seq signature. **S-mode** adjusts the *signature* when it comes from droplet/UMI scRNA-seq. Batch correction needs at least 3 mixture samples, and the authors recommend at least 10, so corrected fractions depend on which cohort they were computed in.
- LM22 is "a microarray-derived signature matrix" for 22 immune cell types. Its gene count is not stated in the chapter (**UNVERIFIED** here).
- The official tutorial pages require sign-in (<https://cibersortx.stanford.edu/tutorial.php> returned only the login and terms text). The exact definition of CIBERSORTx absolute mode is therefore **UNVERIFIED** from a primary CIBERSORTx source. The only statement I have is immunedeconv's description of CIBERSORT (not x) absolute mode quoted above.
- Terms: free for non-commercial use only; data are uploaded to the Stanford server unless the Docker version is used.

### 1.2 Published links between pretreatment deconvolved fractions and ICI response

| Study | Method | Finding relevant to us |
|---|---|---|
| Finotello 2019 (PMID 31126321) | quanTIseq | Anti-PD-1 melanoma RNA-seq: 51 pre- and 58 on-treatment samples, 65 patients; GEO GSE91061 in data availability. Pretreatment **B cells higher in responders (p = 0.02)**; M1 higher but not significant. CD8 difference was on-treatment only (p = 0.03), "not apparent from baseline samples". In-house cohort (21 pretreatment samples): no significant difference (p > 0.09). The authors call for larger samples. |
| Newman 2019 (PMID 31061481) | CIBERSORTx with scRNA reference | Pretreatment melanoma (Van Allen n = 37, Nathanson n = 24, Chen n = 26): imputed PDCD1+/CTLA4+ CD8 T-cell levels associated with response in all three cohorts. This is a cell-*state* signal, not a plain fraction. |
| Helmink 2020 (PMID 31942075, [doi:10.1038/s41586-019-1922-8](https://doi.org/10.1038/s41586-019-1922-8)) | MCP-counter (relative scores) | B-cell markers were the top DE genes between responders and non-responders, corroborated by MCP-counter in melanoma and RCC ICB cohorts. Neoadjuvant setting. |
| Litchfield 2021 (PMID 33508232, [doi:10.1016/j.cell.2021.01.002](https://doi.org/10.1016/j.cell.2021.01.002)) | Gene-level meta-analysis (>1,000 patients, 7 tumour types) | Clonal TMB was the strongest predictor, followed by TMB and **CXCL9 expression**. CCR5 and CXCL13 were T-cell-intrinsic markers. Deconvolution is not described in the abstract (**UNVERIFIED** whether used). |
| Bareche 2022 (PMID 36055464, [doi:10.1016/j.annonc.2022.08.084](https://doi.org/10.1016/j.annonc.2022.08.084)) | 37 published expression signatures plus TMB, >3,600 patients, 12 tumour types (predictIO) | 21/37 signatures were predictive across tumour types. The abstract reports signatures, not deconvolved fractions (**UNVERIFIED** whether deconvolution was part of the analysis). If the spec's "Bareche 2022" means a different paper, it was not found under author Bareche Y. |
| Salgia 2026 (PMID 42849919, [doi:10.1136/jitc-2026-015849](https://doi.org/10.1136/jitc-2026-015849)) | Immune deconvolution in IMmotion151 and HCRN-GU16-260 (RCC) | Memory and class-switched memory B cells were higher in ICB responders, and naive B cells were higher in non-responders. |
| Lin 2026 (PMID 42679812, [doi:10.1016/j.ccell.2026.08.007](https://doi.org/10.1016/j.ccell.2026.08.007)) | scRNA atlas: 441 samples, 241 patients, 10 entities; 77 subtypes | The on-treatment *transition* predicted outcome better than baseline state. The 59-gene signature was validated on **1,383 baseline tumours from 19 cohorts**. Which cohorts were used is **UNVERIFIED**; see §2.4. |

Across these studies, the baseline fraction signals are modest and cohort-specific (B cells, CD8 T-cell states). The strongest baseline expression signals are single genes or programmes such as CXCL9 and IFN-γ-related genes, not deconvolved fractions. The early quanTIseq analysis found the CD8 difference on-treatment, not at baseline.

### 1.3 Pitfalls

1. **Cross-platform comparability.** Neither tool makes fractions comparable *across* RNA-seq, microarray and NanoString as they are run in practice. quanTIseq's array mode uses a different gene set (170 vs 153 genes) and different preprocessing. CIBERSORTx batch correction is fitted per mixture set. NanoString panels cover only a subset of TIL10 or LM22 genes; per-cohort coverage must be measured, as no panel list was checked here. **Treat fractions as within-cohort variables and combine across cohorts only through stratified or meta-analytic models.**
2. **TPM provenance.** Only 7 cohort families have TPM. FPKM→TPM rescaling is fine in principle, because TPM is FPKM rescaled to sum to 10⁶ per sample. Counts→TPM needs gene lengths. Microarray "TPM" does not exist. Avila Cobos 2020 (PMID 33159064, [doi:10.1038/s41467-020-19015-1](https://doi.org/10.1038/s41467-020-19015-1)) found that deconvolution works best "in linear scale", that normalisation choice has "a dramatic impact on some" methods, and that leaving a present cell type out of the reference "leads to substantially worse results". The last point matters for melanoma (melanocytic tumour cells) and for prostate.
3. **mRNA-content scaling.** quanTIseq's scaling and EPIC's renormalisation (Racle 2017, PMID 29130882, [doi:10.7554/eLife.26476](https://doi.org/10.7554/eLife.26476)) convert mRNA proportions into cell proportions using fixed per-cell-type constants. Activated or proliferating cells in responders break that assumption. Scaling can be switched off as a sensitivity analysis.
4. **Absolute vs relative.** quanTIseq-lsei and EPIC give fractions of all cells, with the remainder "Other". CIBERSORT/x relative mode gives fractions of the immune compartment only. Testing "CD8 fraction" from CIBERSORTx relative mode and from quanTIseq answers different questions: share of immune cells vs share of the tumour. quanTIseq's "Other" is roughly 1 − immune and is collinear with tumour purity, which matters for Paper B's purity covariate.
5. **Known weak cell types.** quanTIseq's authors report weaker agreement for Tregs, B cells and M2 macrophages, and a heuristic Treg correction for collinearity with CD4 T cells. Sturm 2019 (PMID 31510660, [doi:10.1093/bioinformatics/btz363](https://doi.org/10.1093/bioinformatics/btz363)) found high accuracy only "for well-defined cell-type signatures" across seven methods.

### 1.4 Circularity with cytotoxicity and IFN-γ scores (TIL10 gene check)

I downloaded `TIL10_signature.txt` (170 genes × 10 cell types), `TIL10_rmgenes.txt` (17 genes) and `TIL10_TCGA_aberrant_immune_genes.txt` (17 genes) from the official repository (<https://github.com/icbi-lab/quanTIseq>, `quantiseq/deconvolution/`). I intersected them with the gene sets already verified in `SIGNATURE_GENE_SETS_20261028.md`:

| Programme (verified source) | Genes | In TIL10 (170 / 153 RNA-seq default) |
|---|---|---|
| T cell-inflamed GEP, 18 genes (Cristescu 2018, PMID 30309915) | 18 | **CD8A only** |
| CYT (GZMA, PRF1; Rooney 2015, PMID 25594174) | 2 | none |
| TIDE CTL markers (CD8A, CD8B, GZMA, GZMB, PRF1; Jiang 2018, PMID 30127393) | 5 | CD8A, CD8B |
| Ayers preliminary 10-gene IFN-γ set (PMID 28650338, [doi:10.1172/JCI91190](https://doi.org/10.1172/JCI91190)) | 10 | none |
| Litchfield markers (CXCL9, CXCL13, CCR5) | 3 | none |

**Gene-level overlap is minimal.** The CD8 T-cell column is anchored by CD8A and CD8B (signature values about 538 and 690 vs ≤ 7 in the other columns), plus EOMES and KLRD1 shared with NK. The circularity is therefore **biological, not lexical**. A tumour rich in CD8 T cells raises CD8A/B (driving quanTIseq CD8) and GZMA/PRF1/IFNG targets (driving CYT, GEP and IFN-γ) together. Removing shared genes does not make the two measures independent. Consequences:

- Do not present "quanTIseq CD8 fraction" and "CYT" or "GEP" as independent predictors, or claim that one *explains* the other.
- If both enter one model, report their correlation in every cohort and use a pre-registered hierarchy (e.g. fraction first, then programme residualised on fraction), or treat them as one immune axis.
- The real independence test is incremental value: does a fraction add to CXCL9 or GEP within cohort? Litchfield's ranking (TMB > CXCL9) suggests the bar is high.

---

## 2. Linking the TCGA methylation–expression association to ICI cohorts without methylation

### 2.1 Design A: define methylation-associated (repressed) immune genes in TCGA, then score them in ICI cohorts

- **What it can claim:** "genes whose TCGA expression is explained by promoter methylation beyond purity, CN and global methylation (ΔR²) form an expression score; is that score associated with response?" It cannot claim that methylation predicts response, because no methylation is measured in the ICI cohorts.
- **Main confound:** composition. Bacolod 2019 (PMID 31202362, [doi:10.1016/bs.acr.2019.03.007](https://doi.org/10.1016/bs.acr.2019.03.007)) found CpG–immune-infiltration relations across TCGA tumour types that were *not observed* in cancer cell lines. Many immune-gene methylation–expression links in bulk tumours are therefore infiltrate signals. Fröhlich 2020 (LAG3, PMID 32861198, [doi:10.1016/j.ebiom.2020.102962](https://doi.org/10.1016/j.ebiom.2020.102962)) showed region-dependent LAG3 methylation differences between monocytes, B, CD4, CD8 and Treg cells, melanocytes and melanoma lines. In tumours, LAG3 methylation tracked infiltrates and an IFN-γ signature, and it was associated with PFS in an ICB cohort (n = 118).
- **Prior art for the direct route (methylation measured in ICI cohorts):** Anichini 2025 (PMID 40682094, [doi:10.1186/s13046-025-03474-9](https://doi.org/10.1186/s13046-025-03474-9)) defined four melanoma methylation classes (EPICA cohort, validated in TCGA). In 28 adjuvant-ICB pretreatment lesions, DEM/LOW lesions had longer RFS than INT/CIMP. Its LOW-vs-CIMP immune and differentiation features were tumour-intrinsic and were retained in cell lines. Several TCGA-SKCM methylation "signatures" (e.g. Guo 2019, PMID 31169496, [doi:10.7554/eLife.44310](https://doi.org/10.7554/eLife.44310)) only *correlate* with ICB-related signatures and were never tested in treated patients. They are not evidence of transfer.
- **Defensible if:** (i) the gene set and scoring rule are frozen from TCGA before any ICI expression is opened; (ii) the score is computed within cohort with a rank-based or z-scored method that tolerates platform gene loss, and per-cohort gene coverage is reported; (iii) the primary model adjusts for an infiltration axis (CXCL9, GEP or quanTIseq CD8), so the result is incremental over immune contexture; (iv) the gene set is split into tumour-intrinsic and infiltrate-expressed genes using scRNA data (§3.1).

### 2.2 Design B: compare co-expression structure (module preservation) between TCGA and ICI baseline tumours

- The method is from Langfelder 2011 (PMID 21283776, [doi:10.1371/journal.pcbi.1001057](https://doi.org/10.1371/journal.pcbi.1001057)). Preservation statistics do not require modules to be re-detected in the test network, and the authors found it "advantageous to aggregate multiple preservation statistics" into summary statistics (Zsummary). The usual interpretation thresholds were not checked against the paper text in this pass (**UNVERIFIED**).
- **Strengths:** outcome-free, so it uses no response labels and is safe to run on all non-locked cohorts. It tests whether the TCGA gene–gene structure behind the Paper B finding exists in treated, mostly metastatic ICI tumours. This is a cleaner bridge than Design A.
- **Pitfalls:** (i) immune genes co-vary because of infiltration gradients, so preservation can be driven entirely by composition. Run it also on partial correlations or residuals after regressing out purity/"Other" and the main immune fractions. (ii) Small cohorts give noisy correlations, so permutation-based Z needs reasonable n per cohort (pre-specify a minimum). (iii) NanoString and array cohorts contain only part of each module, so restrict to the shared genes and report coverage. (iv) No published TCGA→ICI module-preservation application was found in this pass (**UNVERIFIED** whether one exists).

### 2.3 Design C: impute methylation from expression

- The literature found goes the other way. TDimpute (PMID 32649756, [doi:10.1093/gigascience/giaa076](https://doi.org/10.1093/gigascience/giaa076)) imputes RNA-seq *from* methylation. geneEXPLORE (PMID 32127627, [doi:10.1038/s41598-020-60845-2](https://doi.org/10.1038/s41598-020-60845-2)) predicts expression from cis and trans methylation and reports that long-range methylation explains about 50% of expression variance on average. Melody-G (Jin 2026, PMID 42744826, [doi:10.1038/s41467-026-76744-5](https://doi.org/10.1038/s41467-026-76744-5)) infers cell-type methylation from scRNA embeddings, for normal tissues and unseen cell types, not tumours. A validated expression→tumour-methylation imputer for 450K promoters was **not found** (**UNVERIFIED**).
- **Not defensible as a primary analysis.** Imputed methylation is a deterministic function of the same expression matrix, so it adds no information and makes any "methylation predicts response" claim circular. At most it could be an exploratory sensitivity analysis.

### 2.4 Cross-cutting pitfalls

1. **Locked test set.** IMvigor210 must not inform gene selection, scoring rules, module definitions, deconvolution settings or thresholds. A further risk is **indirect exposure** through external signatures. Lin 2026 validated its 59-gene signature on 19 baseline cohorts (n = 1,383). If IMvigor210 or our development cohorts are among them, any Lin-derived signature has already been tuned on them. Check the cohort list in Lin 2026 before adopting any Lin-derived score (**UNVERIFIED** here).
2. **Treatment-naive vs pretreated.** TCGA tumours are untreated at resection. Some ICI cohorts include patients after prior ICI or targeted therapy, which can remodel methylation and immune contexture. Stratify or adjust by prior-therapy flag.
3. **Primary vs metastatic and biopsy site.** TCGA-PRAD is primary, while ICI cohorts are largely metastatic biopsies, some from lymph nodes, which inflates immune fractions. Record biopsy site and include it, or restrict to non-nodal sites as a sensitivity analysis.
4. **Cancer-type mismatch.** Paper B's discovery is PRAD, but the ICI cohorts are mostly melanoma, lung, kidney and bladder. The transfer has to use the cross-cancer TCGA comparators (SKCM, LUAD, LUSC, KIRC, BLCA, HNSC, STAD, LIHC) matched to the ICI cohort's tumour type, not PRAD-derived genes.
5. **Platform.** Same as §1.3(1): within-cohort scoring, gene-coverage reporting, and meta-analysis across cohorts.

---

## 3. Single-cell data for interpreting bulk methylation–expression links and bulk deconvolution

### 3.1 Which cell types express the methylation-associated genes

- **Purpose:** label each ΔR² gene as tumour/epithelial-intrinsic or infiltrate-expressed. A promoter-methylation association for a gene expressed only by T cells is most likely a composition effect (Bacolod 2019; Fröhlich 2020). For tumour-expressed genes, an epigenetic regulation claim is more plausible (cf. Anichini 2025's tumour-intrinsic programmes).
- **Data:** the Lin 2026 atlas (Zenodo [10.5281/zenodo.19586163](https://doi.org/10.5281/zenodo.19586163), CC BY 4.0). The record lists `seurat_full.qs2` (4.0 GB, R `qs2`) plus four Visium samples, and describes the data only as "processed". Whether raw counts are included is **UNVERIFIED**. Use pretreatment cells only, for both the ICI-cohort scoring and the cross-cancer comparators. For PRAD, use the CELLxGENE hormone-naive prostate atlas, which was not inspected in this pass.
- **Caveat:** scRNA dissociation distorts cell proportions. Use it for *which cell type expresses a gene* (specificity), not for how many cells there are.

### 3.2 Benchmarking deconvolution with pseudobulk

- Pseudobulk mixtures from annotated scRNA are standard benchmarking practice (Sturm 2019; Avila Cobos 2020). They give known ground-truth proportions for testing quanTIseq or CIBERSORTx, especially for melanoma and kidney, where tumour cells are not in TIL10.
- Pitfalls: (i) pseudobulk needs counts, so check the Seurat object for a counts layer; (ii) scRNA and bulk differ in gene detection and 3′ bias, so pseudobulk accuracy is an upper bound; (iii) **sample overlap**. If an atlas patient also appears in a bulk ICI cohort, or a CIBERSORTx S-mode signature is built from atlas cells of cohorts we later test, the benchmark and the response analysis are no longer independent. Build any custom signature from cohorts disjoint from Paper A's bulk cohorts and from IMvigor210.
- CIBERSORTx S-mode with a Lin-atlas signature is technically supported (droplet/UMI reference). It adds a second deconvolution path but also adds circularity risk, because the reference comes from ICI-treated tumours.

### 3.3 Cell-type methylation references

- **Loyfer 2023 atlas** (PMID 36599988, [doi:10.1038/s41586-022-05580-6](https://doi.org/10.1038/s41586-022-05580-6)): deep WGBS of 39 sorted cell types from 205 healthy samples, with replicates ">99.5% identical". The UXM reference shipped with the authors' deconvolution tool (<https://github.com/nloyfer/UXM_deconv>, `supplemental/Atlas.U25.l4.hg38.tsv`; column header read directly) includes **Blood-T, Blood-B, Blood-NK, Blood-Mono+Macro, Blood-Granul, Prostate-Ep, Bladder-Ep, Lung-Ep-Alveo/Bron, Kidney-Ep, Liver-Hep, Gastric-Ep, Head-Neck-Ep, Epid-Kerat, Endothel, Smooth-Musc**, among others. At this grouping level T cells are not split into CD4 and CD8, and the file has no melanocyte column. UXM works on fragment-level sequencing (`.pat` files), not on 450K/EPIC arrays. How many atlas markers fall on 450K probes is **UNVERIFIED**.
- **Salas 2022** (PMID 35140201, [doi:10.1038/s41467-021-27864-7](https://doi.org/10.1038/s41467-021-27864-7)): array-based (EPIC and earlier platforms) IDOL libraries for 12 leukocyte subtypes, including naive and memory CD4 and CD8, Tregs, NK and B cells. They were validated in blood, not in tumour tissue.
- **MethylCIBERSORT** (Chakravarthy 2018, PMID 30104673, [doi:10.1038/s41467-018-05570-1](https://doi.org/10.1038/s41467-018-05570-1)): array-based tumour/stroma/immune deconvolution, already used in TCGA pan-cancer work. It is the most directly usable option for the TCGA 450K data in Paper B.
- **scDeconv** (Liu 2022, PMID 35453146, [doi:10.1093/bib/bbac150](https://doi.org/10.1093/bib/bbac150)) deconvolves bulk methylation using scRNA plus paired bulk RNA–methylation samples, assuming paired samples share composition. TCGA has such pairs, so this is a possible route to cell-type-informed methylation covariates.

### 3.4 Single-cell methylation

- Joint methods exist, e.g. scNMT-seq (Clark 2018, PMID 29472610, [doi:10.1038/s41467-018-03149-4](https://doi.org/10.1038/s41467-018-03149-4)), which was validated in mouse embryonic stem cells. I found no human ICI-tumour or hormone-naive prostate single-cell methylation dataset matched to our cohorts (**UNVERIFIED** that none exists). Low CpG coverage per cell also makes promoter-level per-gene values unreliable. **Not usable for the thesis.** Use sorted-cell references (§3.3) instead.

---

## Recommendations for the spec

1. **Option D1: run quanTIseq (lsei, `--tumor=TRUE`, mRNA scaling on) as the primary deconvolution, within cohort, on RNA-seq TPM cohorts only, with array cohorts in `--arrays` mode as a separate stratum and NanoString excluded unless TIL10 coverage passes a pre-set threshold.** Pro: absolute fractions with an "Other" term that ties to purity; one documented input contract; open source. Con: drops or weakens non-TPM cohorts; the published baseline signal for quanTIseq is modest (B cells, p = 0.02, PMID 31126321).
2. **Option D2: add CIBERSORTx (LM22, B-mode) as a sensitivity analysis only.** Pro: has its own pretreatment ICI evidence (PMID 31061481) and explicit cross-platform batch correction, including NanoString. Con: fractions are relative to immune cells and depend on the cohort they were fitted in; absolute-mode definition not verified; non-commercial web licence or Docker setup. Reported as a sensitivity analysis, it is not a co-primary.
3. **Option D3: pre-register the circularity rule.** Fractions and immune programmes (CYT, GEP, IFN-γ, CXCL9) are treated as one immune axis; any claim for a fraction is incremental over CXCL9 or GEP within cohort. Pro: TIL10 shares almost no genes with these programmes (§1.4), but the biological dependence is real, and this rule addresses it directly. Con: stricter bar; fractions may show no incremental value.
4. **Option L1: Design B (module preservation, outcome-free) as the primary TCGA→ICI bridge, run on raw correlations and on composition-residualised correlations, in cancer-type-matched TCGA comparators.** Pro: no response labels, so no double-dipping; directly tests whether the Paper B structure exists in treated tumours. Con: composition can drive preservation; small cohorts and NanoString gene loss limit power; no published precedent found.
5. **Option L2: Design A (frozen TCGA ΔR² gene score → ICI response) as a secondary analysis, adjusted for an immune axis and split into tumour-intrinsic vs infiltrate genes by scRNA.** Pro: gives the one response-facing link Paper B can offer. Con: an expression score, not methylation; must be frozen before ICI data are opened; incremental value over the immune axis may be nil.
6. **Option L3: drop methylation imputation (Design C).** Pro: avoids a circular construct with no validated tool. Con: no methylation-level statement in ICI cohorts at all.
7. **Option S1: use the Lin 2026 atlas (pretreatment cells) and the prostate atlas only for gene-to-cell-type attribution and for pseudobulk benchmarking of quanTIseq, not for building response signatures.** Pro: answers whether a gene is tumour-intrinsic or infiltrate-expressed, which is the main interpretive gap. Con: counts layer unconfirmed; dissociation bias; patient overlap with bulk cohorts must be checked.
8. **Option S2: add a methylation-based composition covariate in Paper B (MethylCIBERSORT on 450K, with the Loyfer/UXM atlas as a sequencing-based cross-check where applicable).** Pro: separates infiltrate from tumour methylation in the same data modality. Con: partly contains the outcome if used as primary adjustment, so keep it as a sensitivity analysis (as in the 2 Nov evidence file, option B3); UXM is not array-native.
9. **Option S3: no single-cell methylation component.** Pro: no matched data exist, and coverage is too sparse for promoter-level work. Con: none material.
10. **Before freezing, verify:** (a) the cohort list behind Lin 2026's 19-cohort validation, for IMvigor210 or Paper A overlap; (b) TIL10 and LM22 gene coverage per NanoString/array cohort; (c) the Seurat counts layer in `seurat_full.qs2`; (d) the CIBERSORTx absolute-mode definition from the official docs if CIBERSORTx is kept.

**Recommended combination:** D1 + D3 + L1 primary, with L2 and S1 secondary, D2 and S2 as sensitivity analyses, and L3/S3 recorded as explicit exclusions.
