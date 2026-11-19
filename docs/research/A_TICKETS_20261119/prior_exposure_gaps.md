# Paper A gate 3: prior-exposure evidence gaps (primary-source check)

**Status:** research note for `docs/validation/PAPER_A_PRIOR_EXPOSURE.md`. It does not change any cohort role, admission, or comparator decision. **Evidence cutoff:** 19 November 2026.

**Scope and rules followed.** Only publications, public supplements that describe cohorts, GEO series-level metadata, and author code were read. No expression matrix, clinical table, patient-level prediction file, model checkpoint, or Zenodo/Figshare data archive was downloaded or opened. Aggregate per-study result tables in author repositories (one row per study with N and an effect size) were read only for their study-name and N columns. No IMvigor210 data were touched.

## Summary

Three of the four open gaps are now settled from primary sources; one is still open. **PredictIO** (Bareche 2022): the author code and the aggregate result tables show a 14-study discovery compendium. Response-based single-gene meta-analysis of that compendium selected the PredictIO genes. The compendium includes Riaz, Hugo, Liu, Van Allen, Nathanson, Braun, Jung, and Mariathasan (IMvigor210), so PredictIO is **trained on IMvigor210** and on seven other source families in the roster. Gide and Kim were used only as validation cohorts. **COMPASS** (Shen 2026): the author notebooks fine-tune the model on 16 immunotherapy cohorts. Every leave-one-cohort-out checkpoint except `leave_IMVigor210` was trained on IMvigor210, and so was the all-cohort checkpoint `finetuner_pft_all.pt`. Riaz, Hugo, Liu, Gide, Van Allen, Kim, and Rose (GSE176307) are training cohorts in the same way. **TIDE, Ayers GEP, and CYT** were not trained or tuned on any roster cohort. TIDE was built from ICB-naive data and only evaluated on Riaz, Hugo, Van Allen, and GSE93157. The Ayers GEP was trained and validated only on Merck KEYNOTE trials. CYT is a fixed two-gene formula defined on TCGA. **Subramanian 2023** defined its subtypes on TCGA and only re-clustered and evaluated ICB cohorts, without outcome supervision. **Lin 2026:** the exact roster of the 19 bulk validation cohorts is still **UNVERIFIED**. The author code loads the bulk cohorts from a git-ignored local data object, and the journal supplement could not be retrieved (HTTP 403). Lin's 59 genes are selected on single-cell pseudobulk, so bulk cohorts appear to be used for evaluation only, but cohort membership itself is unknown.

## Table: roster cohort × comparator

Key: **TRAINED** = the cohort contributed labelled data to fitting, feature selection, or fine-tuning of the released comparator. **EVAL** = used only to evaluate a fixed comparator. **NONE** = not used in the inspected primary source. **UNVERIFIED** = the source does not settle the question. "NONE" means absence from the cited source and code version only. It does not establish patient-level independence.

| cohort_id | Lin 2026 59-gene | PredictIO 2022 | Subramanian 2023 | COMPASS 2026 | TIDE 2018 | Ayers GEP 2017 | CYT 2015 |
|---|---|---|---|---|---|---|---|
| riaz_gse91061 | UNVERIFIED [L1] | TRAINED (Riaz) [P1,P2] | NONE [S1] | TRAINED (Riaz) [C1,C2] | EVAL [T1] | NONE [A1] | NONE [R1] |
| hugo_gse78220 | UNVERIFIED | TRAINED (Hugo) | EVAL | TRAINED (Hugo) | EVAL | NONE | NONE |
| gse168204 | UNVERIFIED | NONE | NONE | UNVERIFIED (COMPASS "MGH" is Freeman 2022; see Q3) | NONE | NONE | NONE |
| liu2019 | UNVERIFIED | TRAINED (Liu) | EVAL | TRAINED (Liu) | NONE | NONE | NONE |
| gide2019 | UNVERIFIED | EVAL (validation) | EVAL | TRAINED (Gide) | NONE | NONE | NONE |
| braun2020 | UNVERIFIED | TRAINED (Braun) | EVAL | NONE | NONE | NONE | NONE |
| vanallen2015 | UNVERIFIED | TRAINED (Van_Allen) | EVAL | TRAINED ("Allen") | EVAL | NONE | NONE |
| gse135222 | UNVERIFIED | TRAINED ("Jung" lung; accession equivalence UNVERIFIED) | NONE | NONE | NONE | NONE | NONE |
| gse136961 | UNVERIFIED | Discovery set, survival only ("Hwang"); no response rows, so contribution to gene selection UNVERIFIED | NONE | NONE | NONE | NONE | NONE |
| gse176307 | UNVERIFIED | NONE | NONE | TRAINED ("Rose") | NONE | NONE | NONE |
| kim2018 | UNVERIFIED | EVAL (validation) | EVAL | TRAINED (Kim) | NONE | NONE | NONE |
| **imvigor210** | UNVERIFIED | **TRAINED (Mariathasan)** | EVAL | **TRAINED (IMVigor210)** | NONE | NONE | NONE |
| gse145996 | UNVERIFIED | NONE | NONE | NONE | NONE | NONE | NONE |
| gse165278 | UNVERIFIED | TRAINED via Nathanson source family (patient equivalence UNVERIFIED) | EVAL (Nathanson) | NONE | EVAL for SERPINB9 analysis only, not TIDE score | NONE | NONE |
| gse93157 | UNVERIFIED | NONE | NONE | NONE | EVAL (Prat) | NONE | NONE |
| gse67501 | UNVERIFIED | NONE | NONE | NONE | NONE | NONE | NONE |
| gse122220 | UNVERIFIED | NONE | NONE | NONE | NONE | NONE | NONE |
| gse140901 | UNVERIFIED | NONE | NONE | NONE | NONE | NONE | NONE |
| gse111636 | UNVERIFIED | NONE | NONE | NONE | NONE | NONE | NONE |
| gse218989 | UNVERIFIED (an April 2025 author script used it; see Q1) | NONE | NONE | NONE | NONE | NONE | NONE |
| gse159067 | UNVERIFIED | NONE | NONE | NONE | NONE | NONE | NONE |

Confidence: all TRAINED, EVAL, and NONE entries are **CONFIRMED** against the source cited, except where a cell says UNVERIFIED. The confirmation applies to source-family use. **Exact patient overlap between the comparator's copy and the project's copy is UNVERIFIED in every cell.**

Other registry cohorts seen in the same sources, all registry roles unchanged: PredictIO trained on `miao2018` (Miao.1), `jerby_arnon_bulk`, and `snyder2017` (Snyder, ureteral/bladder), and validated on `cui_puch` (Puch). COMPASS trained on `immotion150`, `miao2018`, `snyder2017`, `zhao2019`, `su2c_mark` (Ravi SU2C-LC1/LC2), and Choueiri 2016 kidney. Subramanian evaluated `javelin_renal101` (Motzer 2020).

### Source locators

- [L1] Lin et al., *Cancer Cell* 2026;44(9):1847–1861.e6, DOI [10.1016/j.ccell.2026.08.007](https://doi.org/10.1016/j.ccell.2026.08.007), PubMed [42679812](https://pubmed.ncbi.nlm.nih.gov/42679812/). Author code: [github.com/zlin-bioinfo/PanCancer_ICI](https://github.com/zlin-bioinfo/PanCancer_ICI) at commit `aa07d1d92cb4` (22 Aug 2026): `Classification/Assignment_bulk.R`, `Figs_Main/Fig5.R`.
- [P1] Bareche et al., *Ann Oncol* 2022;33:1304–1317, DOI [10.1016/j.annonc.2022.08.084](https://doi.org/10.1016/j.annonc.2022.08.084), PubMed [36055464](https://pubmed.ncbi.nlm.nih.gov/36055464/).
- [P2] [github.com/bhklab/PredictIO](https://github.com/bhklab/PredictIO) at commit `ed30fd40a53a` (28 Sep 2022): `code/denovo_Single_Gene/Get_Individual_Association.R`, `code/PredictIO/run_PredictIO.R`, `code/PredictIO_Validation/run_PredictIO.R` (line 36), `results/Summary_Figure/Table/Signature/Signature_Individual.txt` (aggregate, study column), `results/PredictIO/PredictIO/KMPlot/`.
- [S1] Subramanian et al., *Cell Rep Med* 2023;4:100896, DOI [10.1016/j.xcrm.2022.100896](https://doi.org/10.1016/j.xcrm.2022.100896), [PMC9873950](https://pmc.ncbi.nlm.nih.gov/articles/PMC9873950/): STAR Methods "Immunotherapy datasets" and Key resources table.
- [C1] Shen et al., *Nat Med* 2026, DOI [10.1038/s41591-026-04502-7](https://doi.org/10.1038/s41591-026-04502-7).
- [C2] [github.com/mims-harvard/COMPASS](https://github.com/mims-harvard/COMPASS) at default-branch commit `0e5c87665247`: `paper/00_pretrain/run_scripts/03_loco_pft.ipynb`, `paper/05_feature_explaination/01_PFT_score_all/00_finetune_all/all_pft_v100s.ipynb`, `paper/00_pretrain/run_scripts/baseline_run/LOCO_42/*/metric_performance.tsv` (aggregate, cohort columns), `README.md` §2–3. Cohort table: [github.com/mims-harvard/COMPASS-web](https://github.com/mims-harvard/COMPASS-web) at `b09c88ae3e73`, `_notebooks/01_TCGA_ITRP_datasets.ipynb` §2.
- [T1] Jiang et al., *Nat Med* 2018;24:1550–1558, DOI [10.1038/s41591-018-0136-1](https://doi.org/10.1038/s41591-018-0136-1), [PMC6487502](https://pmc.ncbi.nlm.nih.gov/articles/PMC6487502/).
- [A1] Ayers et al., *J Clin Invest* 2017;127:2930–2940, DOI [10.1172/JCI91190](https://doi.org/10.1172/JCI91190), [PMC5531419](https://pmc.ncbi.nlm.nih.gov/articles/PMC5531419/).
- [R1] Rooney et al., *Cell* 2015;160:48–61, DOI [10.1016/j.cell.2014.12.033](https://doi.org/10.1016/j.cell.2014.12.033), [PMC4856474](https://pmc.ncbi.nlm.nih.gov/articles/PMC4856474/).

## Q1. Lin et al. 2026: roster of the 19 bulk validation cohorts

**Finding: still UNVERIFIED.** No primary locator that lists the final 19 cohorts (1,383 baseline tumours) could be retrieved.

- The final article and its supplements on cell.com and sciencedirect.com returned HTTP 403 to automated access. Europe PMC reports no PMC full text or supplement for PubMed 42679812. The final roster is most likely in the article's STAR Methods Key resources table or a supplementary table (Table S-number unknown); it should be read manually from the journal page.
- Author code ([L1], HEAD `aa07d1d`): `Classification/Assignment_bulk.R` loads the bulk cohorts from `data/bulk_datasets/expr_list.qs2` and `clin_list.qs2`. These files sit under `data/` and `tables/`, which `.gitignore` excludes, so the repository does not contain the roster. **CONFIRMED** that the roster is not in the public code.
- The Zenodo record [19586163](https://zenodo.org/records/19586163) (v2) holds only a single-cell Seurat object and four Visium archives. It has no bulk roster. **CONFIRMED.**
- **Lead only, not the final roster.** An earlier commit (`c6f309b`, "backup 23.04.2025", file `scripts/Bulk analysis/Dataset_prep.R`, since removed) prepared these bulk cohorts: Riaz (GSE91061), Nathanson 2017, Van Allen (phs000452, labelled "Cui"), Hugo (GSE78220), Auslander (GSE115821), Liu 2019, Ribas (GSE158403), Gide (PRJEB23709), a LUD2015-005 oesophageal cohort ("Carrol"), IMvigor210, IMmotion150, Braun, and NSCLC Kang (GSE218989). That is 13 cohorts, written 16 months before publication and before the preprint-to-final population change (1,988 to 1,383 tumours). Under the audit rule it must **not** be used as the final roster.
- **Training role. CONFIRMED from code, final roster aside.** In `Figs_Main/Fig5.R` the transition signature is selected by random-forest stability selection on single-cell pseudobulk (`data/pseudobulk_TIME.qs2`) with favourable and unfavourable transition labels. Bulk cohorts are then only scored with directional ssGSEA and assessed by cohort-adjusted logistic regression, Cox models, and forest plots. On this code version, any bulk cohort in the roster is an evaluation cohort, not a training cohort. Whether the published 59-gene list equals this code's output is UNVERIFIED.

## Q2. PredictIO (Bareche 2022): training and validation cohorts

**Finding: CONFIRMED from author code and aggregate outputs [P2].** The paper full text (annalsofoncology.org) returned 403, and the Zenodo data record [6142546](https://zenodo.org/records/6142546) names no studies. The code is therefore the primary locator.

- **Discovery (training) compendium, 14 studies.** `code/denovo_Single_Gene/Get_Individual_Association.R` loads `ICB_exp_filtered.RData` and iterates over all studies in it. It keeps genes present in 12–14 studies, which implies 14 studies. Per-study association is run on each primary-tumour group with at least 20 patients. The 14 study names in `Signature_Individual.txt` are Braun, Fumet.1, Fumet.2, Hugo, Hwang, Jerby_Arnon, Jung, Liu, Mariathasan, Miao.1, Nathanson, Riaz, Snyder, and Van_Allen. `code/PredictIO/run_PredictIO.R` builds PredictIO from `Meta-analysis_Single_Gene_Response.RData`: genes with p ≤ 0.05 and |coef| at or above that of the 100th-ranked gene. **The discovery studies with response labels therefore determined the signature (TRAINED).**
- **Validation cohorts:** `code/PredictIO_Validation/run_PredictIO.R` line 36 is `cohort = c("Shiuan","VanDenEnde","INSPIRE","Kim","Gide","Puch")`. The signature is fixed before these are scored, so they are EVAL.
- **Mapping to project IDs:** Riaz→`riaz_gse91061`; Hugo→`hugo_gse78220`; Liu→`liu2019`; Van_Allen→`vanallen2015`; Braun→`braun2020`; Mariathasan→`imvigor210` (aggregate rows for bladder, kidney, lymph-node, and ureteral tissue sites); Jung (lung)→`gse135222`; Hwang (lung, survival only)→`gse136961`; Nathanson (melanoma)→`gse165278` source family (MSKCC Snyder 2014/Nathanson 2017 cohort, per the project registry); Gide→`gide2019` and Kim→`kim2018` (validation only); Snyder (ureteral)→`snyder2017`; Miao.1→`miao2018`; Jerby_Arnon→`jerby_arnon_bulk`; Puch→`cui_puch`. Name-to-ID mapping is by study name and tumour type. The code does not state accessions, so copy and patient equivalence are UNVERIFIED.
- **Not in the compendium (NONE at this code version):** `gse168204`, `gse176307`, `gse145996`, `gse93157`, `gse67501`, `gse122220`, `gse140901`, `gse111636`, `gse218989`, `gse159067`. The `predictIO.ca` web resource may have grown since 2022; that is not covered here.

## Q3. Subramanian 2023, COMPASS 2026, TIDE, Ayers GEP, CYT: trained/tuned versus evaluated

**Subramanian 2023 [S1]: no outcome-supervised training on ICB cohorts. CONFIRMED.** The 91 angio-immune gene sets come from MSigDB. The C1–C3 subtypes were found by hierarchical clustering of TCGA (30 tumour types). ICB cohorts were scored the same way and "molecular subtypes were derived as described elsewhere" by re-clustering within each cohort. Outcomes were only compared across clusters with log-rank and response-rate tests. ICB cohorts listed: Gide (ERP105482), Hugo (GSE78220), Liu (phs000452), Van Allen (phs000452.v2.p1), Nathanson 2017, Mariathasan (EGAS00001002556), Kim (ERP107734), Braun, and Motzer/JAVELIN. **IMvigor210 is EVAL only.**

**COMPASS 2026 [C1, C2]: TRAINED on IMvigor210 and seven other roster source families. CONFIRMED.**
- The model is pretrained on TCGA and fine-tuned on the 16-cohort ITRP set (1,133 patients). The cohorts are Choueiri, Miao, Snyder (BLCA), Zhao (GBM), SU2CLC1/2 (Ravi 2023), Hugo, Allen, MGH (Freeman 2022), Kim, Riaz, Rose (BJC 2021), Gide, Liu, IMmotion150, and IMVigor210 (n=298) (COMPASS-web `01_TCGA_ITRP_datasets.ipynb` §2).
- `03_loco_pft.ipynb`: for each test cohort, the fine-tuner is trained on all other 15 cohorts and saved as `leave_<cohort>_out.pt`. **Every LOCO checkpoint except `leave_IMVigor210_out` was trained on IMvigor210.** The README's example checkpoint `pft_leave_Gide.pt` is one of these.
- `all_pft_v100s.ipynb` fine-tunes on all ITRP rows and saves `finetuner_pft_all.pt`. That is the checkpoint the README recommends for feature extraction on new cohorts, so **it was trained on IMvigor210**.
- The repository also contains leave-one-patient-out runs within each cohort (`paper/04_model_performance/00_leave_one_patient_out/`), which train within cohorts, including on cohorts such as MGH.
- Whether the downloadable web checkpoints are byte-identical to these notebook outputs is UNVERIFIED. So is whether the shared hyperparameters (fixed across LOCO folds) were chosen after looking at LOCO test results.
- `gse168204` is GEO series "Pathway Signatures Derived from On-treatment Tumor Specimens…" (PubMed 34654806, Du et al. 2021). COMPASS "MGH" cites Freeman et al. 2022 (PubMed 35243413). Both are MGH melanoma anti-PD-1 cohorts, but the patient intersection is **UNVERIFIED**.
- Braun, Van Allen's anti-CTLA-4 partner (Nathanson), and all GSE NanoString/array cohorts on the roster are absent from ITRP.

**TIDE (Jiang 2018) [T1]: not trained or tuned on any ICB clinical cohort. CONFIRMED.**
- The Discussion states that TIDE is trained on data from ICB-naive tumours.
- Dysfunction signatures come from Cox interaction tests on TCGA, PRECOG, and METABRIC. Exclusion signatures come from CAF, MDSC, and M2 TAM expression profiles. The CTL split is the within-dataset mean, and score normalisation uses TCGA melanoma.
- The ICB cohorts used for evaluation were Hugo (n=25), Van Allen (n=42), Prat/GSE93157 (n=33), and Riaz (Supplementary Fig. 6).
- Nathanson was used only for the SERPINB9 survival analysis. A murine B16 anti-CTLA-4 dataset (non-clinical) was used to rank SERPINB9.
- Mariathasan appears only as a background citation, and **IMvigor210 is not used**.

**Ayers 2017 GEP [A1]: NONE for every roster cohort. CONFIRMED.** The final 18-gene weighted GEP was fitted by penalised (elastic-net) logistic regression on 220 KEYNOTE-012/028 patients across nine tumour types, with penalties chosen by 5-fold cross-validation. It was validated on 96 HNSCC patients from KEYNOTE-012. Earlier stages used KEYNOTE-001 melanoma. No public cohort on the roster appears.

**CYT (Rooney 2015) [R1]: NONE. CONFIRMED.** CYT is the geometric mean of GZMA and PRF1 (TPM, 0.01 offset). It is set a priori with no fitting, and the paper analyses TCGA (with GTEx and CCLE controls), not ICB-treated cohorts.

## Still open

1. **Lin 2026 final 19-cohort bulk roster.** Read the journal's STAR Methods Key resources table and supplementary tables by hand (cell.com, DOI above), or ask the corresponding authors. Until then every Lin cell stays UNVERIFIED. Do not substitute the April 2025 script list or the preprint population.
2. **Exact patient overlap** in every TRAINED and EVAL cell. Source-family use is confirmed, but whether each comparator's copy (for example PredictIO "Riaz" TPM n=51, COMPASS "IMVigor210" n=298) contains the same patients as the project copy is not established. Checking this would need patient-level files, which this ticket did not open.
3. **PredictIO accession equivalence** for Jung→GSE135222 and Nathanson→GSE165278, and whether Hwang contributed to response-based gene selection (the aggregate tables show survival endpoints only).
4. **COMPASS checkpoint identity.** Are the web-hosted `finetuner_pft_all.pt` and LOCO checkpoints the notebook outputs? Was hyperparameter choice blind to LOCO test folds? Do MGH (Freeman 2022) and GSE168204 (Du 2021) share patients?
5. **Not covered by this ticket:** quanTIseq and TIS rows of the audit TSV, and the post-2022 contents of the `predictIO.ca` web resource.

Consequence for gate 3, not a decision: PredictIO and COMPASS (any published checkpoint other than `leave_IMVigor210_out`) cannot be treated as independent of `imvigor210`. Subramanian, TIDE, Ayers GEP, and CYT have no training or tuning exposure to it.
