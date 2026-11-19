# Paper A comparator scoring rules from primary sources (19 Nov 2026)

**Scope.** SPEC_v2 §7 admits a supporting comparator only with "their exact published scoring rules". This note records what the primary papers, supplements and author code actually specify for each named comparator, what can be computed exactly from RNA-seq TPM (linear or log), and where the current `tools/a_comparators` code and registry differ. The sources were papers, supplements, author code, and repository or record metadata. No expression matrix, patient-level table or outcome file was opened or downloaded, and IMvigor210 material was not touched. Files that hold patient-level data are named below only as locators.

Status words: **EXACT** means the published rule can be reproduced without any guessed parameter. **PROCEDURE** means it can be reproduced only by re-running a cohort-relative procedure, not as a fixed per-sample rule. **BLOCKED** means a rule element is unavailable.

## Summary

| Comparator | Implementable exactly on RNA-seq TPM? | Required input | Gene list / weights locator | Licence / access | Mismatch with current code/registry |
|---|---|---|---|---|---|
| CYT (Rooney 2015) | **EXACT** on linear TPM. Also exact from log TPM when the log transform and pseudocount are known and inverted exactly. | Linear gene TPM for GZMA and PRF1 | Rooney 2015 Experimental Procedures, "Cytolytic activity and other cell type-specific signatures" | Journal article; trivial formula, no code needed | **Yes.** Primary rule adds a **0.01 offset**: sqrt((GZMA+0.01)(PRF1+0.01)). `a_scoring.cyt`, the registry and the assay contract all fix sqrt(GZMA×PRF1) with no offset, yet keep the ID `CYT_Rooney_TPM_v1`. |
| Ayers 2017 IFN-γ 6-gene / expanded immune 18-gene | **BLOCKED** for an exact rule. Each score is a plain average, but the 11 housekeeping genes used for per-sample normalisation are not named in the text. | Housekeeping-normalised log10 NanoString counts | Ayers 2017 Methods; gene lists in Table 2 (image only) | JCI article | No implementation exists (correct). The registry does not list these two average scores separately from the final GEP. |
| Ayers/Cristescu final 18-gene T-cell-inflamed GEP | **BLOCKED.** Weights sit only in a supplementary table that also holds patient-level counts. The platform is NanoString, so an RNA-seq port is not the published assay. | log10 counts minus mean log10 of 11 housekeeping genes; weighted sum | Cristescu 2018 *Science* Table S2B, as corrected by erratum 10.1126/science.aax1384 | Journal supplement; retrieving it brings patient-level counts | No implementation (correct). The registry text agrees with the primary sources. |
| TIS (Danaher 2018) | **BLOCKED.** Weights are "predefined" from Ayers but not printed. | log2 expression after re-normalisation to **10** nCounter housekeeping genes | Danaher 2018 Statistical methods; genes in Table 1 | JITC (CC BY); the assay is NanoString IUO | No implementation (correct). The registry should record that TIS uses 10 housekeeping genes and log2, where the GEP uses 11 and log10. |
| PredictIO (Bareche 2022) | **PROCEDURE** (cohort-relative GSVA). Not exact: the published 100-gene list and the input scale are not verified from the primary paper. | Per-cohort gene z-scores of an unverified expression scale, then GSVA | Gene list derived by code from a meta-analysis result file; paper Supplementary Table S8 (not accessed) | Code repository has **no licence file**. Data on Zenodo is CC BY 4.0. | No implementation (correct). Confirmed that the two launchers differ (details below). |
| Subramanian 2023 angio-immune C1/C2/C3 | **PROCEDURE** only. GSVA plus hierarchical clustering within a cohort; there are no centroids and no single-sample classifier. | "Normalized bulk RNA-seq" (TCGA upper-quartile; ICB cohorts TPM) | 91 gene sets in `Genesets_File.txt` (Zenodo 11942459); R script (Zenodo 7317331) | Code MIT; gene sets and results CC BY 4.0; Dryad record CC0 | No implementation (correct). The registry should add that the author script cannot run as written. |
| Lin 2026, 59 genes | **BLOCKED.** No gene list, weights, algorithm or code is openly accessible. | Unknown | Paper STAR Methods/supplement (publisher page refused access, HTTP 403); no author code found | Atlas data on Zenodo 19586163 (CC BY 4.0); no code record | No implementation (correct). Status unchanged: BLOCKED. |

## 1. CYT, Rooney et al. 2015

Source: Rooney MS et al., *Cell* 2015, [doi:10.1016/j.cell.2014.12.033](https://doi.org/10.1016/j.cell.2014.12.033), [PMC4856474](https://pmc.ncbi.nlm.nih.gov/articles/PMC4856474/). Retrieved via PubMed Central.

- **Rule (Experimental Procedures, "Cytolytic activity and other cell type-specific signatures"):** CYT "was calculated as the geometric mean of GZMA and PRF1 (as expressed in TPM, 0.01 offset)". The Figure 1 legend calls it the "log-average (geometric mean)", which is the same quantity.
- **Exact formula:** CYT = sqrt((TPM_GZMA + 0.01) × (TPM_PRF1 + 0.01)). Equivalently, CYT = exp(mean(ln(TPM_g + 0.01))). Higher means more cytolytic activity.
- **Input:** gene-level TPM. The paper took gene-level expression from GDAC Firehose (tumours) and GTEx (normals). The Methods do not name the quantifier.
- **On log TPM:** recover linear TPM exactly (for example 2^x − 1 when the input is log2(TPM+1)), then apply the formula. Mean(log(TPM+0.01)) ranks samples identically, so AUC is identical.
- **Implementable:** EXACT. Nothing is missing.
- **Mismatch:** `tools/a_scoring/core.py::cyt` returns `sqrt(gzma*prf1)`, and `specs/A/COMPARATOR_REGISTRY.md` and `specs/A/ASSAY_PROCESSING_CONTRACT.md` §"CYT and prediction compatibility" state "No pseudocount is added to CYT". That is a deliberate project rule, but it is **not Rooney's published rule**. The two rules rank samples differently only when a value is at or near zero: without the offset, any sample with zero TPM in either gene scores 0 and ties with every other such sample. Two fixes are possible. Either adopt the 0.01 offset, or keep the no-offset rule under a name that does not claim Rooney's definition (for example a `_nooffset` variant) and document the difference. This is a decision, not a code bug.
- **Side note:** PredictIO's own "CYT" score is GSVA over {PRF1, GZMA} (`data/signatures/signature_INFO.txt` in its repository). That is not Rooney's rule and should not be cited as CYT.

## 2. Ayers 2017 IFN-γ and expanded immune signatures, the final T-cell-inflamed GEP, and TIS

### 2a. Ayers 2017 preliminary and refined signatures

Source: Ayers M et al., *J Clin Invest* 2017, [doi:10.1172/JCI91190](https://doi.org/10.1172/JCI91190), [PMC5531419](https://pmc.ncbi.nlm.nih.gov/articles/PMC5531419/).

- **Normalisation (Methods):** discovery used quantile normalisation followed by log10. The clinical-assay route normalises each gene's log10 count by subtracting "the arithmetic mean of the log10 counts" of 11 low-variance housekeeping genes. **The 11 housekeeping genes are not named in the text.**
- **IFN-γ (6-gene) and expanded immune (18-gene) scores:** "calculated by averaging of the included genes" (Methods). The gene lists are in Table 2, which is an image only and was not machine-readable. The preliminary 10-gene IFN-γ set is named in the text: IFNG, STAT1, CCR5, CXCL9, CXCL10, CXCL11, IDO1, PRF1, GZMA, HLA-DRA.
- **Secondary concordance only (not the primary source):** the refined 6-gene IFN-γ list in bhklab SignatureSets is IDO1, CXCL10, CXCL9, HLA-DRA, STAT1, IFNG. For the expanded immune signature, the PredictIO and SignatureSets "IRG_Ayers" files list **17** genes, while SignatureSets' TME copy lists **18**: the same 17 plus LAG3. The secondary sources therefore disagree, and Table 2 must be read directly before any list is frozen.
- **On RNA-seq TPM:** an average of log expression can be computed. The published rule, however, subtracts a per-sample housekeeping mean, and that shift changes cross-sample ranking. Without the housekeeping list the rule is not exact. Changing the log base only rescales the score; the pseudocount does not.

### 2b. Final 18-gene T-cell-inflamed GEP (Ayers 2017; Cristescu 2018)

Sources: Ayers 2017 (above). Cristescu R et al., *Science* 2018, [doi:10.1126/science.aar3593](https://doi.org/10.1126/science.aar3593), [PMC6718162](https://pmc.ncbi.nlm.nih.gov/articles/PMC6718162/), Materials and methods, "Gene expression (RNA) profiling: NanoString methodology". Erratum: [doi:10.1126/science.aax1384](https://doi.org/10.1126/science.aax1384).

- **Algorithm (Ayers Methods):** genes and weights come from an elastic-net penalised logistic regression for objective response, with the penalty chosen by 5-fold CV repeated over 10 partitions. The non-zero coefficients are the weights. Score = weighted sum of the housekeeping-normalised values of the 18 genes. No intercept is mentioned. CD276 is the only gene negatively associated with outcome.
- **Normalisation (Cristescu Methods):** raw counts are log10-transformed, then the arithmetic mean of log10 counts for 11 housekeeping genes is subtracted. QC follows the NanoString clinical-assay approach.
- **Genes:** CCL5, CD27, CD274, CD276, CD8A, CMKLR1, CXCL9, CXCR6, HLA-DQA1, HLA-DRB1, HLA-E, IDO1, LAG3, NKG7, PDCD1LG2, PSMB10, STAT1, TIGIT. This list matches Cristescu's Methods enumeration (the gene symbols are stripped from the PMC text rendering), Ayers Figure 4 (an image), Danaher Table 1, and SignatureSets. The project already marks membership 18/18 VERIFIED in `docs/research/SIGNATURE_GENE_SETS_20261028.md`.
- **Weights locator:** neither paper prints the weights in its text. According to the erratum notice (via search snippet; the science.org page returned 403), Table S2 was expanded to include raw NanoString counts for the housekeeping and predictor genes plus "the weighting algorithm used to determine the score (table S2B)". **The weights are therefore in Cristescu 2018 Table S2B, which sits beside patient-level KEYNOTE counts.** Under this task's rules it was not retrieved. Fetching it needs an explicit decision on whether a supplement file that contains third-party patient-level counts is acceptable. No weight values were verified. Weight lists circulating online are unverified and must not be used.
- **Cut-off:** Cristescu used a discovery cut-off of −0.318 on the NanoString scale. It does not transfer to RNA-seq.
- **On RNA-seq TPM:** Cristescu applied the GEP to TCGA RNA-seq without describing the transform in the text. Danaher (below) describes an RNA-seq port for TIS. Any RNA-seq GEP is therefore a port of a NanoString assay, not the assay itself. To be faithful it needs the weights, the 11 housekeeping genes, a log10 transform and a stated pseudocount, and it must be labelled a port.
- **Implementable:** BLOCKED (weights, housekeeping list). Even when unblocked, it remains a cross-platform port.

### 2c. TIS (Danaher 2018)

Source: Danaher P et al., *J Immunother Cancer* 2018, [doi:10.1186/s40425-018-0367-1](https://doi.org/10.1186/s40425-018-0367-1), [PMC6013904](https://pmc.ncbi.nlm.nih.gov/articles/PMC6013904/). Retrieved via PubMed Central.

- **Rule (Statistical methods):** RSEM RNA-seq values are "re-normalized … using the 10 reference ('housekeeping') genes used in the nCounter assay", then log2-transformed. TIS = Σ wᵢxᵢ over the 18 genes, where "wᵢ is a predefined weight derived in Ayers et al. (2017)". **Weights are not printed.**
- **Differences from the GEP as published:** **10** housekeeping genes (Ayers/Cristescu use 11), log2 (they use log10), RSEM input. The paper reports an estimated offset of about 1.3 score units between TCGA RNA-seq TIS and the IUO assay, with example thresholds of 6.72, 6.0 and 5.5 on the TCGA scale. TIS is a NanoString IUO assay (reagents, instrument, algorithm and software).
- **Implementable:** BLOCKED (weights, housekeeping list). Keep it distinct from the GEP, as the registry already does.

## 3. PredictIO, Bareche et al. 2022

Sources: Bareche Y et al., *Ann Oncol* 2022, [doi:10.1016/j.annonc.2022.08.084](https://doi.org/10.1016/j.annonc.2022.08.084). The publisher full text returned HTTP 403, so the Methods were not read directly. Author code: [github.com/bhklab/PredictIO](https://github.com/bhklab/PredictIO) at commit `ed30fd40a53a50fc298ab0df46b35852b8584601`, last push 2022-09-28, **no licence file** (default copyright, reuse not granted). Data: [Zenodo 6142546](https://doi.org/10.5281/zenodo.6142546), CC BY 4.0, patient-level and not downloaded.

**Gene selection (`code/denovo_Single_Gene/Get_Individual_Association.R`, `meta-analysis_Response.R`):**
- Per study × tumour type with at least 20 samples, genes with zeros in more than 50% of samples are dropped. Only genes present in 12–14 studies are kept.
- For each gene, logistic regression of response (R = 0, NR = 1) on the z-scored gene. Coefficients and SEs are rounded to 2 decimals. A random-effects meta-analysis (`meta::metagen`) follows.
- Because NR = 1, **coef < 0 means "sensitive" (higher expression goes with response) and coef > 0 means "resistance".**
- Discovery launcher (`code/PredictIO/run_PredictIO.R`): keep genes with p ≤ 0.05, rank by |coef|, take the 100th |coef| as the cut-off, and include every p ≤ 0.05 gene with |coef| ≥ cut-off. Because coefficients are rounded, ties can push the list past 100 genes.
- Validation launcher (`code/PredictIO_Validation/run_PredictIO.R`): the cut-off is computed only among genes with p ≤ 0.05 **and** heterogeneity `I2_pval > 0.05`, but inclusion is still tested against all p ≤ 0.05 genes. **The two launchers can therefore produce different gene sets.** This confirms the existing registry blocker.
- The gene list is not stored in the repository. It is produced from the meta-analysis result file built from the Zenodo data. The paper reportedly gives the lists in Supplementary Tables S3–S8 (from a search snippet, not verified).

**Score (`getIOscore` in both `PredictIO.R` files):**
1. Within the cohort (study × tumour type, at least 20 samples), drop genes with zeros in more than 50% of samples.
2. Z-score every gene across the cohort's samples (`get_Scale`).
3. If more than 80% of the resistance genes are present, IO_resistance = `GSVA::gsva(z, list(resistance))`. Do the same for the sensitive genes. GSVA defaults apply (method "gsva", Gaussian kernel), in a GSVA version for R 4.1 or later. The version is not pinned, and the `gsva(matrix, list)` call is the pre-1.50 interface.
4. **PredictIO = IO_sensitive − IO_resistance.** Higher means more likely to respond. If either half fails the coverage check, the score is NULL. A search summary of the paper describes the score as a "ratio" of the two GSVA scores; the code computes a difference. This is unresolved until the Methods are read.

**Input scale:** the code scores samples whose `rna` annotation is "fpkm" or "tpm". The exact transform (for example log2(TPM+1)) is **not stated in the code** and was not verified from the paper.

**Secondary gene list:** bhklab SignatureSets (MIT, commit `ed57eb0555e6ea91fada846bbec10b8409ca198f`), `data-raw/IO/PredictIO_Bareche.csv`, lists exactly 100 genes: 77 "sensitive" and 23 "resistance". It is a later package from the same lab. Its equivalence to the published Table S8 and to either launcher is **unverified**, so it is not substituted, consistent with the existing registry.

**Implementable:** PROCEDURE only. The score depends on which samples share a cohort (z-scoring, GSVA kernel and the zero filter are all cohort-relative). It must therefore be computed on the frozen common eligible population, per study × tumour type, as the authors did. Blockers: the primary gene list, the input transform, ratio versus difference, the GSVA version, and the absent code licence.

**Caution:** PredictIO's in-repository "TIS", "T_cell_inflamed" (15 genes, cited to PMID 30804515) and "CYT" scores are GSVA scores over gene lists, not the published weighted or geometric-mean rules. They must not be reused under those names.

## 4. Subramanian et al. 2023 angio-immune subtypes

Source: Subramanian M et al., *Cell Rep Med* 2023, [doi:10.1016/j.xcrm.2022.100896](https://doi.org/10.1016/j.xcrm.2022.100896), [PMC9873950](https://pmc.ncbi.nlm.nih.gov/articles/PMC9873950/), STAR Methods ("Building of angio-immune score matrix", "Clustering patients", "Immunotherapy datasets"). Author code: [Zenodo 7317331](https://doi.org/10.5281/zenodo.7317331), `Angio-Immune_Cluster_Identification.R`, MIT, sha256 `e73fb0be…934d`. Gene sets: [Zenodo 11942459](https://zenodo.org/records/11942459), `Genesets_File.txt`, CC BY 4.0, sha256 `f99e0692…903e`. Only this definition file was read. The same record holds patient-level enrichment, cluster and clinical files, including a bladder file from the IMvigor210 family, and none of those were opened. Dryad [10.5061/dryad.v41ns1s11](https://doi.org/10.5061/dryad.v41ns1s11) is CC0.

**Method:**
- 91 MSigDB-derived gene sets related to endothelial and T-cell activity, with no MSigDB version stated. They are scored with GSVA across the patients of a cohort.
- A Pearson correlation matrix between patients is built from the 91 enrichment scores. It is clustered hierarchically with Euclidean distance using `pheatmap` (default linkage: complete), and `cutree(k = 3)` gives the clusters.
- Clusters are labelled post hoc by their enrichment profile: **C1** angiogenesis-high/immune-low, **C2** neither enriched, **C3** angiogenesis-low/T-cell-high, where C3 is the good-response group.
- The ICB cohorts were "derived as described elsewhere": the same procedure was run within each cohort on "Pretreatment TPM normalized RNA sequencing data". TCGA input was Firehose upper-quartile-normalised data.

**Author-script parameters:** `gsva(expr = data, gset.idx.list = genesets, method = "gsva", rnaseq = TRUE, abs.ranking = TRUE)`. Here `rnaseq = TRUE` selects the Poisson kernel, which is meant for integer counts and was applied to TPM. `abs.ranking` and `rnaseq` are removed in current GSVA. The script **cannot run as written**: `corr()` is not base R, and `read.delim` returns a data frame rather than a gene-set list. Two gene-set headers are corrupted (`…IMMUNITYAGER`, `…PRODUCTIONARG1`), and some symbols are outdated (for example ELTD1, GPR116, "SIPR1"). The file holds 1,150 unique genes, with sets of 5 to 483 genes.

**Log versus linear input:** not stated. The Poisson kernel implies a non-log scale.

**Implementable:** PROCEDURE only. There are no centroids and no per-sample rule. A patient's label depends on the other patients in the cohort and on manual mapping of cluster numbers to C1/C2/C3. A faithful re-run needs a GSVA version that still accepts the published arguments, an exact repair of the script bugs (documented as deviations), symbol mapping, and per-cohort clustering on the frozen population. **Prior exposure:** the paper's ICB cohorts include Hugo, Gide, Liu, Van Allen, Kim, Braun, Motzer and Mariathasan, matching the registry's confirmed source-family use.

## 5. Lin et al. 2026, 59-gene signature

Source: Lin Z et al., *Cancer Cell* 2026;44(9):1847–1861.e6, PMID 42679812, [doi:10.1016/j.ccell.2026.08.007](https://doi.org/10.1016/j.ccell.2026.08.007). Not in PMC.

- From the abstract (PubMed): the signature was derived from scRNA TIME-transition analysis and "predicted response and survival for 1,383 baseline tumors across 19 independent cohorts".
- The publisher full text and STAR Methods returned HTTP 403, and no open author manuscript was found. No preprint was located by search, so the "older preprint" the registry mentions was not re-located.
- The atlas record on [Zenodo 19586163](https://doi.org/10.5281/zenodo.19586163) (CC BY 4.0) holds only a Seurat object and Visium data, with no code or gene list. No author GitHub repository was found (the Aran-lab account was checked).
- **Unknown:** gene list, weights or algorithm, input scale, normalisation, thresholds, direction, code, licence and cohort roster.
- **Implementable:** BLOCKED. The status in the readiness registry stands.

## Mismatches with current code and registry

1. **CYT offset:** Rooney uses a 0.01 offset; `a_scoring.cyt`, the registry and the assay contract use none, while the ID still says "Rooney". Rename the rule or adopt the offset, and record the decision.
2. **Registry, TIS row:** add that TIS uses log2 with **10** housekeeping genes (Danaher), against 11 and log10 for the Ayers/Cristescu GEP, and that its weights are "predefined" from Ayers but unprinted.
3. **Registry, Ayers rows:** name the weights locator, Cristescu 2018 Table S2B (erratum aax1384), and note that the file also contains patient-level counts. The 6-gene and expanded 18-gene averages are separate published scores and need their own rows. Their housekeeping list is unnamed, and secondary copies of the expanded list disagree (17 versus 18 genes).
4. **Registry, PredictIO row:** confirmed. The validation launcher adds `I2_pval > 0.05` to the cut-off step only. Add: no code licence; score = GSVA_sensitive − GSVA_resistance after per-cohort gene z-scoring; per-half coverage must exceed 0.8; the "ratio" wording in the paper versus the difference in the code is unresolved.
5. **Registry, Subramanian row:** add the author-script identity (Zenodo 7317331, MIT), the gene-set file identity, the Poisson-kernel arguments, and the fact that the script does not run without repair.
6. **No stray implementations:** no non-CYT comparator is implemented, which is correct.

## Still open

- **CYT:** decide between the offset and the no-offset rule and its naming. This is the only item that changes existing code.
- **Ayers GEP/TIS weights:** decide whether retrieving Cristescu Table S2B is permitted, since it carries third-party patient-level NanoString counts. Name the 11 (GEP) and 10 (TIS) housekeeping genes from a primary table. Read Ayers Table 2 directly to settle the expanded-signature membership.
- **PredictIO:** read the Annals Methods and Supplementary Table S8 through institutional access to settle the gene list, input transform and ratio-versus-difference. Choose the launcher. Pin the GSVA version. Ask the authors about the missing code licence.
- **Subramanian:** pin a GSVA version that accepts `rnaseq`/`abs.ranking` (pre-1.50), and specify the script repairs and the symbol mapping before freezing.
- **Lin 2026:** obtain the STAR Methods and supplement (gene list, rule, 19-cohort roster) through institutional access or from the authors. Until then it stays BLOCKED.
- **For every comparator:** the prior-exposure audit (`docs/validation/PAPER_A_PRIOR_EXPOSURE.tsv`) is unchanged by this note.
