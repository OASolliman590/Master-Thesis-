# ICI transcriptomic signature methods: comparison of papers similar to Paper A

Date: 2026-10-28. Source: PubMed and PubMed Central, read through the PubMed MCP tools. Every paper is cited by PMID and DOI (see Section 5).

Scope: Paper A asks how robust immune and ICI-response gene signatures are in baseline bulk RNA-seq. It looks at how results change between ORR (CR/PR vs rest) and clinical benefit (CB, where SD lasting more than 6 months counts as response), and at transfer across cohorts. Its first cohort is Riaz 2017 (GSE91061, nivolumab melanoma, 49 baseline patients, author FPKM hg19).

Labels used here:
- **[FT]** = facts taken from the PMC full text.
- **[ABS]** = facts taken from the abstract only.
- **UNVERIFIED** = not confirmed in the text I read.
- Note: the PMC text that the tool returns strips most citations and GEO accessions. So "which cohort is which accession" is often not visible in the text. I mark those cases UNVERIFIED.

## 1. Summary

- Riaz 2017 and Hugo 2016 are the most reused ICI RNA-seq cohorts in this literature. TIDE, IMPRES, Sun 2021, Coleman 2022, Kang 2023 and Zhang 2022 use them for evaluation or training, so they are "seen" cohorts, not clean tests [FT: PMID 30127393, 30127394, 33915876, 35781709, 37627121, 35488273].
- Published signatures transfer poorly. Kang 2023 tested 48 scores on 15 baseline datasets: the best (TIDE, CYT) were significant in only 5/15, and four datasets showed no signal for any score [FT: 37627121].
- Spread across cohorts is wide even for the best signatures. In Coleman 2022, IFN-γ-18 had a mean AUROC of 0.70 but a range of 0.48–0.95 over 15 melanoma cohorts. The mean across all signatures was 0.44 in Hugo [FT: 35781709].
- Endpoint definitions are not shared. Litchfield, Coleman and Zhang use CR/PR vs SD/PD (NE counted as non-responder in Litchfield). Kang uses a clinical-benefit rule (CR/PR/SD with PFS > 6 months). Sun 2021 uses CR/PR/SD vs PD as its primary [FT: 33508232, 35781709, 35488273, 37627121, 33915876].
- Only Sun 2021 ran several endpoint definitions side by side (PD, OR, OS, DCB). It reports that results change, but gives no single number for how much [FT: 33915876]. No paper measures the effect of the endpoint switch in a direct, quantified way. This is a gap Paper A can fill.
- The response criterion itself may matter. The TIDE authors suggest that their lower AUC in Riaz than in Hugo may be because Riaz used RECIST 1.1 while Hugo used irRECIST [FT: 30127393].
- Most benchmarks score each cohort separately and avoid pooling. They use per-cohort TPM or log-expression, often z-scored or mean-centred within the cohort [FT: 33508232, 30127393, 35781709, 37627121]. Only Zhang 2022 pooled cohorts, with ComBat, before a random patient-level split [FT: 35488273].
- Litchfield is the clearest model of a leakage-safe design. It used a uniform pipeline, per-study effect sizes with a random-effects meta-analysis, and three test cohorts never used in training (two chosen because they were published after training ended) [FT: 33508232].
- Baselines that keep recurring: TIDE, IMPRES, CYT, IFN-γ (6- and 18-gene), the T-cell-inflamed GEP, PD-L1 (CD274), CD8A/CXCL9, MHC-II, and TMB [FT: 33508232, 37627121, 33915876, 35781709, 35488273].
- Pre-treatment signal is weaker than on-treatment signal [FT: 35781709, 37627121]. Paper A's baseline-only focus is therefore the harder and more clinically honest question.

## 2. Methods-comparison table

| Paper (source) | Cohorts | Endpoint | SD / NE handling | Expression and normalization | Validation design | Leakage control | Performance spread |
|---|---|---|---|---|---|---|---|
| **Litchfield 2021**, Cell, CPI1000+ meta-analysis [FT] (PMID 33508232) | 12 cohorts, n=1,008, WES+RNA-seq, reprocessed raw data. Hugo is named; Riaz inclusion is UNVERIFIED (references stripped). Tests: KEYNOTE-028 "other tumour types" (n=76), Liu 2019 melanoma (n=121), Shim 2020 NSCLC (n=144) | RECIST CR/PR vs SD/PD, best response in >90% of cases | SD = non-responder; **NE = non-responder**. The authors say this "may undercount" benefit. Some lesions and long-term survivors with early progression were excluded | RSEM TPM for multi-gene signatures; DESeq2 VST for single genes; all biomarkers z-scored for effect-size comparison | Per-cohort tests, then random-effects meta-analysis; XGBoost with 5-fold CV on the training data; 3 independent test cohorts | Test cohorts kept out of training; 2 chosen because they were published after training; uniform reprocessing | Multivariable test AUCs 0.86 / 0.66 / 0.70 (TMB 0.68 / 0.58 / 0.62) |
| **Jiang 2018**, TIDE, Nat Med [FT] (PMID 30127393) | Signature built from 189 non-ICB studies (TCGA, PRECOG, METABRIC). Evaluated on melanoma RNA-seq anti-CTLA-4 (n=25) and anti-PD-1 (n=42), a NanoString set (n=33), and Riaz (24 ipi-naive patients) | Original study labels; ROC on the continuous score | Not stated in the text. The authors note Riaz used RECIST 1.1 and Hugo used irRECIST | Quantile normalization within each dataset, then each gene mean-centred across that cohort's samples (**within-cohort centring is part of the method**) | Trained on non-ICB data, then applied to ICB cohorts | Strong by design: no ICB labels used for training | Per-cohort AUCs are in figures only (UNVERIFIED here); lower in Riaz than in Hugo, stated in the text |
| **Auslander 2018**, IMPRES, Nat Med [FT] (PMID 30127394) | Built on neuroblastoma (n=108). Tested on 9 melanoma datasets from 6 studies (256 samples, including Riaz, Hugo and Van Allen) plus a new MGH set (31 anti-PD-1, 10 anti-CTLA-4; GEO accession UNVERIFIED, possibly GSE115821) | Each study's own response labels (Supp. tables) | Sensitivity analysis that **excludes SD**; IMPRES stays superior | Quantile-normalized; score counts 15 gene-pair rules (A > B), so it is invariant to rank-preserving scaling | Built on another disease, then applied; competing signatures re-trained per dataset with SVM CV | Never trained on melanoma, but includes **on-treatment samples** | AUC 0.77–0.96 across datasets; 0.83 overall |
| **Bareche 2022**, PredictIO, Ann Oncol [ABS] (PMID 36055464) | More than 3,600 patients, 12 tumour types (cohort list UNVERIFIED) | ICB response, plus PFS and OS (definition UNVERIFIED) | UNVERIFIED | Signatures "computed with respect to the original publication" | Per-study association, then meta-analysis; de novo PredictIO signature | UNVERIFIED (abstract only) | 21/37 signatures and TMB predictive across tumour types; AUCs UNVERIFIED |
| **Hernando-Calvo 2023**, VIGex, Med [ABS] (PMID 37572657) | 909 NanoString samples (45 tumour types); 98 early-phase ICI patients; meta-analysis of 13 datasets (877 patients) | UNVERIFIED | UNVERIFIED | NanoString nCounter, 12-gene score with hot / intermediate-cold / cold cutoffs | Development, then clinical cohort, then 13-dataset meta-analysis | UNVERIFIED | UNVERIFIED |
| **Kang 2023**, ICB-Portal benchmark, Cancers [FT] (PMID 37627121) | 29 datasets from 16 studies (1,492 samples); 15 baseline-only datasets (n=1,337). Includes Riaz (paired pre/on, ipi-naive vs exposed) | **Clinical benefit**: CR/PR/SD with PFS > 6 mo vs PD or SD with PFS < 6 mo | SD split by 6-month PFS; NE not stated | Protein-coding genes, TPM "or other normalized metrics"; 9 signatures also scored with ssGSEA | Each score tested within each dataset (one-sided Wilcoxon, AUC); no model training | Analyses kept within each dataset to limit batch effects; signatures were partly built on these same cohorts | TIDE and CYT best, at 5/15 datasets; IMPRES, CXCL1, ESCS and CD8T_xCell at 0/15; 4 datasets had no signal for any score |
| **Sun 2021**, Cancers [FT] (PMID 33915876) | 10 studies, 647 patients, melanoma/ccRCC/UC/NSCLC. Hugo, Riaz and Gide reprocessed from raw reads | Primary "PD strategy": CR/PR/SD vs PD. Also OR (CR/PR vs SD/PD), OS-based, and DCB (SD with PFS > 6 mo) | SD counted as responder in the primary analysis; 4 definitions compared | kallisto, then TPM, then log2 | Per-dataset AUC; sample-size-weighted AUC across datasets | **Each signature's own training data was excluded from its AUC** | Mean AUCs low: TMB 0.66, PD-L1 0.63, TIDE 0.61 "fluctuated noticeably"; EMT 0.82 in Hugo only |
| **Coleman 2022**, Mol Carcinog [FT] (PMID 35781709) | 8 studies, 15 melanoma cohorts, 531 patients (Gide, Hugo, Lee, Liu, Riaz, Van Allen, Du, Lauss) | CR/PR vs SD/PD (RECIST) | SD = non-responder; NE not stated | **Mixed author-processed units**: log(CPM+1), log(TPM+1) or log(FPKM+1); genes **z-scored within each study**, then averaged | Per-cohort AUROC only, no training | No model fitted; cohorts overlap with signature-development cohorts | IFN-γ-18 mean 0.70 (0.48–0.95); top 7 at about 0.69; mean of all signatures 0.44 in Hugo and 0.50 in Liu-naive |
| **Zhang 2022**, Stem.Sig, Genome Med [FT] (PMID 35488273) | 10 ICI cohorts (921 patients). Training/validation: Braun, Mariathasan, Liu, Gide, **Riaz**. Test: **Hugo**, Van Allen, Snyder, Zhao, Kim | ORR: CR/PR vs SD/PD (RECIST 1.1; irRECIST for Hugo) | SD = non-responder | GSVA scores; **ComBat across 5 pooled cohorts, then random 80/20 patient split** | Seven ML models, 10×5-fold CV; validation set; 5-cohort independent test set | Test cohorts are separate, but validation is not cohort-independent (patients from the same cohorts, after ComBat) | AUC 0.71 on validation and test; test cohorts 0.62–0.81; IFNG.Sig 0.85 in one cohort and 0.53–0.54 in three |
| **Chen 2022**, TIGER, GPB [FT] (PMID 36049666) | 1,508 ICI bulk samples from 20 studies, 8 cancer types | Not given in the text | Not given | STAR + featureCounts, then FPKM; signatures scored "according to the parameters used in the original study"; robust rank aggregation | Resource; signature AUCs in 23 datasets | Not addressed | Not reported in the text |
| **Yang 2022**, ICBatlas, Cancer Immunol Res [ABS] (PMID 36095221) | 1,515 ICI samples, 25 studies, 9 cancer types | Response vs non-response "on the basis of the clinical information" | UNVERIFIED | UNVERIFIED | Resource (DE, pathways, immune cells) | Not addressed | Not reported |
| **Kovács 2022**, systematic review of datasets, J Transl Med [FT] (PMID 35641998) | 26 datasets, 2,386 samples (RNA-seq 15, NanoString 6, microarray 4, qPCR 1) | Documents each study's own rule | Hugo: CR/PR/SD = responder. Van Allen: CB = CR/PR or SD with OS > 1 y. Gide: non-responder = PD or SD ≤ 6 mo | Records author-deposited units (TPM, FPKM, log2, RMA) | Catalogue only | Not applicable | Not applicable |

Screened and dropped as off-topic or not about bulk RNA-seq ICI signatures:
- Off topic: 37729873, 37261423, 31665482, 40281576, 37146911, 41057909, 38217005, 41327380, 41527309, 39302579, 41089673, 40763838, 40963050, 40274385, 39934971, 38048058, 39787635, 41536941, 34551377.
- Tangential: 38703428, 40432277, 33365377, 37822932.
- MSK-IMPACT clinical model, not RNA-seq: 40890336.
- 34534227 and 31097034 were not returned by the metadata call, so they were not screened (UNVERIFIED).

Extra searches I ran: a title search for systematic benchmarks of ICI transcriptomic biomarkers (found 37627121, 33915876 and 35641998), and a batch/normalization cross-cohort search (mostly noise). I also ran find_related_articles on 37627121, 33915876 and 35781709. Its top 20 results added no new core paper.

## 3. Recurring patterns and disagreements

**Do signatures transfer across cohorts?** Mostly no, or only weakly.
- Kang 2023 concludes that "most biomarkers showed poor performance in terms of stability and robustness across different datasets" [FT: 37627121].
- In Coleman 2022, every top signature has an AUROC range that reaches about 0.47–0.48 in at least one cohort [FT: 35781709].
- IMPRES is the clearest disagreement. Its authors report AUC 0.77–0.96 on 9 datasets [FT: 30127394]. In Sun 2021 it ranked among the top two [FT: 33915876]. But in Kang 2023 it was significant in 0/15 baseline datasets and clustered with negative markers [FT: 37627121]. Possible reasons: different endpoints (Kang used clinical benefit), baseline-only data in Kang versus mixed pre/on-treatment data in IMPRES, and different datasets.
- IMPRES's authors also report that ML signatures trained in one cohort had to be re-trained for each dataset, "otherwise their overall performance was dismal" [FT: 30127394].

**Do signatures transfer across cancer types?** Partly. Simple immune scores travel best.
- CYT was significant in melanoma, gastric cancer, NSCLC and UC. TIDE's hits were mainly in the cancer types it was built on [FT: 37627121].
- Cancer-specific signatures do best in their own cancer [FT: 37627121].
- In the Stem.Sig test set, IFNG.Sig ranged from 0.85 in one cohort to 0.53–0.54 in three others [FT: 35488273].

**Does the endpoint definition change results?** Yes, but nobody quantifies it well.
- Sun 2021 ran four definitions and says differences were "observed" between them. Some datasets showed no signal under any definition [FT: 33915876].
- Litchfield chose ORR (with NE as non-responder) for consistency. It admits this undercounts patients with durable SD [FT: 33508232].
- Kang chose clinical benefit [FT: 37627121].
- So two big benchmarks use opposite primary definitions, and their rankings cannot be compared directly.
- The response criterion also differs between cohorts: RECIST 1.1 in Riaz and irRECIST in Hugo [FT: 30127393, 35488273].

**TPM vs FPKM, and within-cohort scaling.**
- No paper tests TPM against FPKM head to head.
- The common way to avoid the problem is to score each cohort separately on a rank-based or centred scale:
  - TIDE: quantile normalization plus per-cohort gene mean-centring [FT: 30127393].
  - IMPRES: pairwise rules [FT: 30127394].
  - ssGSEA and GSVA: rank-based [FT: 37627121, 35488273].
  - Coleman: per-study z-score [FT: 35781709].
  - Litchfield: z-scores of all biomarkers [FT: 33508232].
- Coleman 2022 mixed CPM, TPM and FPKM across cohorts, relying on per-study z-scoring [FT: 35781709].
- Kang 2023 found that ssGSEA versions of signatures were often more predictive than plain mean or sum versions. They suggest this is because ssGSEA is robust to platform effects [FT: 37627121].
- Batch correction across cohorts (ComBat) appears only in Zhang 2022. It was applied before a patient-level split, which lets information from the validation patients shape the training data [FT: 35488273].

**Leakage and reuse of test cohorts.**
- Many evaluations reuse the cohorts the signatures were built on.
- Sun 2021 explicitly removed each signature's own training data from its AUC [FT: 33915876].
- Litchfield picked test sets by publication date [FT: 33508232].
- Kang and Coleman do not report this kind of exclusion [FT: 37627121, 35781709].

**Baseline vs on-treatment.** On-treatment samples give stronger signals [FT: 35781709]. Immune scores rise on treatment in both responders and non-responders [FT: 37627121]. Mixing pre- and on-treatment samples (as IMPRES did) can inflate AUCs [FT: 30127394].

## 4. Implications for Paper A

**Endpoint handling**
- Primary analysis: ORR (CR/PR vs SD/PD) using RECIST as given by the authors. This matches Litchfield, Coleman and Zhang [FT: 33508232, 35781709, 35488273].
- Pre-registered sensitivity analysis: clinical benefit (CR/PR + SD > 6 months vs PD + SD ≤ 6 months), as in Kang 2023 and the Gide/Kovács definitions [FT: 37627121, 35641998]. Also run an SD-excluded analysis (CR/PR vs PD), as in IMPRES [FT: 30127394].
- Handle NE explicitly. Report counts. In the primary analysis, exclude NE rather than silently calling it non-response; add a Litchfield-style sensitivity analysis that treats NE as non-response [FT: 33508232].
- Record the criterion (RECIST 1.1 vs irRECIST) for each cohort as a covariate, given the TIDE observation [FT: 30127393].
- Report the change in AUC per signature per cohort between definitions (ΔAUC with bootstrap CI). No paper here gives this number.

**Expression representation and per-cohort scaling**
- Keep the author FPKM for Riaz, but convert FPKM to TPM within each sample (TPM = FPKM / sum(FPKM) × 1e6) and use log2(TPM+1). Then score every signature within each cohort only.
- Use rank-based or within-cohort-standardized scores (ssGSEA/GSVA, z-score, mean-centring), which are what most papers rely on [FT: 30127393, 35781709, 37627121].
- Run TIDE with its own preprocessing (per-cohort centring) [FT: 30127393].
- Do not ComBat across cohorts before splitting. If any pooling is done, fit the correction on training cohorts only. Report a sensitivity analysis on raw versus batch-corrected data (motivated by the Zhang 2022 design [FT: 35488273]).
- Add a small robustness check: author FPKM→TPM versus z-score-only scoring for Riaz, to show the ranking of signatures is stable. No paper here tests this directly.

**Which cohorts to hold out as an untouched final test**
- Treat Riaz (GSE91061) and Hugo (GSE78220) as development/"seen" cohorts. They were used to evaluate or train TIDE, IMPRES and Stem.Sig, and appear in the Sun, Coleman and Kang benchmarks [FT: 30127393, 30127394, 33915876, 35781709, 37627121, 35488273].
- Hold out GSE176307 (urothelial) and GSE248014 as the untouched final test. Neither accession appears in any core paper I read (texts strip accessions, so their absence is UNVERIFIED). GSE248014 is likely too recent for these 2018–2023 papers (UNVERIFIED).
- Do not use GSE115821 as a clean test. It may be the IMPRES MGH set (UNVERIFIED), which would make it partly seen by IMPRES.
- Use GSE168204 and GSE126044 as clinical-benefit-only cohorts, so they belong to the CB sensitivity analysis rather than the ORR primary. Whether they appear in these benchmarks is UNVERIFIED.
- Use leave-one-cohort-out for development, and lock all thresholds and choices before touching the hold-out (following Litchfield's logic [FT: 33508232]).

**Baseline signatures to compare against**
- TIDE [FT: 30127393]; IMPRES [FT: 30127394].
- CYT (GZMA, PRF1); IFN-γ 6-gene and IFN-γ 18-gene; the T-cell-inflamed GEP (18 genes).
- CD274; CD8A/CXCL9; an MHC-II signature.
- One stromal/resistance score (IPRES or pan-F-TBRS).
- These recur as the strongest or standard baselines [FT: 33508232, 37627121, 33915876, 35781709, 35488273].
- Optionally add PredictIO [ABS: 36055464].
- Give exact gene lists and scoring methods (mean vs ssGSEA), because the scoring method changes results [FT: 37627121].

**Gaps Paper A can fill**
1. A quantified ORR-versus-CB switch (ΔAUC per signature and cohort), with explicit SD and NE handling. Only Sun 2021 approached this, and without numbers [FT: 33915876].
2. Strictly baseline, cohort-level external testing with leakage audit: which signatures were built on which cohorts, and which cohorts were held out.
3. A check of whether units (FPKM vs TPM vs rank) change the signature ranking. This is not tested in any core paper.
4. Uncertainty reporting (bootstrap CI per cohort, meta-analytic pooled AUC with heterogeneity). Most benchmarks report point AUCs or p-value counts [FT: 37627121, 35781709].

## 5. References

All retrieved from PubMed / PubMed Central through the PubMed MCP tools.

1. Litchfield K, et al. Meta-analysis of tumor- and T cell-intrinsic mechanisms of sensitization to checkpoint inhibition. Cell. 2021. PMID [33508232](https://pubmed.ncbi.nlm.nih.gov/33508232/); DOI [10.1016/j.cell.2021.01.002](https://doi.org/10.1016/j.cell.2021.01.002); [PMC7933824](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7933824/).
2. Jiang P, et al. Signatures of T cell dysfunction and exclusion predict cancer immunotherapy response. Nat Med. 2018. PMID [30127393](https://pubmed.ncbi.nlm.nih.gov/30127393/); DOI [10.1038/s41591-018-0136-1](https://doi.org/10.1038/s41591-018-0136-1); [PMC6487502](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6487502/).
3. Auslander N, et al. Robust prediction of response to immune checkpoint blockade therapy in metastatic melanoma. Nat Med. 2018. PMID [30127394](https://pubmed.ncbi.nlm.nih.gov/30127394/); DOI [10.1038/s41591-018-0157-9](https://doi.org/10.1038/s41591-018-0157-9); [PMC6693632](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6693632/).
4. Bareche Y, et al. Leveraging big data of immune checkpoint blockade response identifies novel potential targets. Ann Oncol. 2022. PMID [36055464](https://pubmed.ncbi.nlm.nih.gov/36055464/); DOI [10.1016/j.annonc.2022.08.084](https://doi.org/10.1016/j.annonc.2022.08.084); no PMCID.
5. Hernando-Calvo A, et al. A pan-cancer clinical platform to predict immunotherapy outcomes and prioritize immuno-oncology combinations in early-phase trials. Med. 2023. PMID [37572657](https://pubmed.ncbi.nlm.nih.gov/37572657/); DOI [10.1016/j.medj.2023.07.006](https://doi.org/10.1016/j.medj.2023.07.006); no PMCID.
6. Kang H, et al. A Comprehensive Benchmark of Transcriptomic Biomarkers for Immune Checkpoint Blockades. Cancers (Basel). 2023. PMID [37627121](https://pubmed.ncbi.nlm.nih.gov/37627121/); DOI [10.3390/cancers15164094](https://doi.org/10.3390/cancers15164094); [PMC10452274](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10452274/).
7. Sun S, et al. Systematic Assessment of Transcriptomic Biomarkers for Immune Checkpoint Blockade Response in Cancer Immunotherapy. Cancers (Basel). 2021. PMID [33915876](https://pubmed.ncbi.nlm.nih.gov/33915876/); DOI [10.3390/cancers13071639](https://doi.org/10.3390/cancers13071639); [PMC8037221](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8037221/).
8. Coleman S, et al. Systematic evaluation of the predictive gene expression signatures of immune checkpoint inhibitors in metastatic melanoma. Mol Carcinog. 2022. PMID [35781709](https://pubmed.ncbi.nlm.nih.gov/35781709/); DOI [10.1002/mc.23442](https://doi.org/10.1002/mc.23442); [PMC9771882](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9771882/).
9. Zhang Z, et al. Integrated analysis of single-cell and bulk RNA sequencing data reveals a pan-cancer stemness signature predicting immunotherapy response. Genome Med. 2022. PMID [35488273](https://pubmed.ncbi.nlm.nih.gov/35488273/); DOI [10.1186/s13073-022-01050-w](https://doi.org/10.1186/s13073-022-01050-w); [PMC9052621](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9052621/).
10. Chen Z, et al. TIGER: A Web Portal of Tumor Immunotherapy Gene Expression Resource. Genomics Proteomics Bioinformatics. 2022. PMID [36049666](https://pubmed.ncbi.nlm.nih.gov/36049666/); DOI [10.1016/j.gpb.2022.08.004](https://doi.org/10.1016/j.gpb.2022.08.004); [PMC10626175](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10626175/).
11. Yang M, et al. ICBatlas: A Comprehensive Resource for Depicting Immune Checkpoint Blockade Therapy Characteristics from Transcriptome Profiles. Cancer Immunol Res. 2022. PMID [36095221](https://pubmed.ncbi.nlm.nih.gov/36095221/); DOI [10.1158/2326-6066.CIR-22-0249](https://doi.org/10.1158/2326-6066.CIR-22-0249); no PMCID.
12. Kovács SA, et al. Transcriptomic datasets of cancer patients treated with immune-checkpoint inhibitors: a systematic review. J Transl Med. 2022. PMID [35641998](https://pubmed.ncbi.nlm.nih.gov/35641998/); DOI [10.1186/s12967-022-03409-4](https://doi.org/10.1186/s12967-022-03409-4); [PMC9153191](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9153191/).
