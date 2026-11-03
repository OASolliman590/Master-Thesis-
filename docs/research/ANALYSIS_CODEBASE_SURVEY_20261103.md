# Analysis codebase survey, 3 Nov 2026

This note answers four questions. (1) Which codebases already do molecular meta-analysis of ICI response, stratified by cancer and by treatment class? (2) Which tools are standard for bulk RNA, microarray and NanoString analysis? (3) Which tools are standard for single-cell QC, normalisation, embedding, annotation checks and pseudobulk? (4) What is the smallest stack that fits the signed Paper A method, and how should the Python repo call R?

Every fact comes from a primary source, cited inline:
- **Repositories:** read through the GitHub API (`gh api repos/...`). "Last push" is the repo's `pushed_at` field. "Last commit" is the newest commit on the default branch.
- **Bioconductor:** the release `VIEWS` index (<https://bioconductor.org/packages/release/bioc/VIEWS>). Bioconductor 3.23 is the current release and is tied to R 4.6.0 (<https://bioconductor.org/config.yaml>).
- **CRAN:** the package pages at `https://cran.r-project.org/web/packages/<pkg>/`.
- **PyPI:** the JSON API at `https://pypi.org/pypi/<pkg>/json`.
- **Papers:** PubMed records (source: PubMed, with the DOI given).

Claims not confirmed from a primary record are marked **UNVERIFIED**. Nothing was cloned or installed, and no data were downloaded. The Lin atlas Zenodo record was read only as metadata, through its JSON API.

---

## 1. Meta-analysis of ICI response across studies

### 1.1 ICI-specific codebases

**bhklab/PredictioR** (<https://github.com/bhklab/PredictioR>). An R package for "pan-cancer, cancer-specific, and treatment-specific" IO biomarker analysis ([README](https://github.com/bhklab/PredictioR/blob/main/README.md)). Version 0.0.0.9000. No GitHub releases; not on CRAN or Bioconductor. Last commit on main 2025-09-17; last push 2026-04-28. Licence inconsistent: `DESCRIPTION` says GPL-3, the repo `LICENSE` file is MIT ("Copyright (c) 2023 BHKLAB"). What the code does, read from `R/`:
- **Per-study gene effect.** `geneLogReg.R` z-scores each gene (`scale()`) and fits `glm(response ~ g, binomial)` with R = 0 and NR = 1, returning the log-odds ratio per SD and its SE. Survival versions exist (`geneSurvCont`, `geneSurvDicho`, Cox). Before testing it drops genes whose share of values equal to log2(0.001) exceeds `missing.perc` (`rem.R`; input assumed log2(TPM+0.001)). This is **not** a Hedges g or a DE log fold change, so its effects are not on our scale.
- **Pooling.** `metafun.R` calls `meta::metagen(TE, seTE, fixed = FALSE, random = TRUE)` with otherwise default settings, returning the pooled estimate, CI, p, I² and Q p-value. It requires k ≥ 3 studies, otherwise returns NA.
- **meta's defaults.** `metagen` defaults to REML for τ² and `method.random.ci = "classic"`, a Wald CI with no Hartung–Knapp correction ([settings.meta.R](https://github.com/guido-s/meta/blob/master/R/settings.meta.R), lines 561 and 566). PredictioR therefore runs REML **without** Knapp–Hartung.
- **Subgroups.** `metaPerCanfun.R` and `metaPerTreatmentfun.R` call `cancerfun` / `treatmentfun`, which relabel any cancer or treatment with only 1–2 studies as `"Other"`, then fit a separate random-effects model in each group with ≥ 3 studies. No subgroup-difference test, no meta-regression.
- **Multiple testing.** No FDR inside the meta functions; the BH line in `geneLogReg.R` is commented out.
- **Fit:** a design cross-check, not a dependency. Its effect scale, missing modified Knapp–Hartung, "Other" pooling and licence ambiguity conflict with the signed method.

**bhklab/PredictIO** (Bareche 2022 code; <https://github.com/bhklab/PredictIO>). Bareche 2022 is PMID 36055464 ([doi:10.1016/j.annonc.2022.08.084](https://doi.org/10.1016/j.annonc.2022.08.084)), a meta-analysis of >3,600 ICB patients across 12 tumour types. The code is a set of R scripts (`code/meta`, `code/denovo_Single_Gene`, `code/PredictIO`, …, and a `run_analysis.R` driver), needing R ≥ 4.1 and using `meta` and `metafor` ([README](https://github.com/bhklab/PredictIO/blob/master/README.md)). `code/meta/Meta-Analysis.R` pools with `metagen` and runs subgroups with `update.meta(meta, byvar = Primary)`. Last commit 2022-09-28. **No licence file**: reading material only.

**ORCESTRA ICB data.** The curated ICB objects behind PredictioR (Mammoliti 2021, PMID 34608132, [doi:10.1038/s41467-021-25974-w](https://doi.org/10.1038/s41467-021-25974-w)), downloadable with `orcestra-downloader` (MIT; PyPI 0.15.0, 2025-05-13; <https://github.com/bhklab/orcestra-downloader>). The older `bhklab/orcestra-icb-datasets` CLI is archived per its README. `bhklab/icb_data_exploration_and_analysis` (no licence, last push 2022-12-13) shows the same per-gene logistic regression followed by DerSimonian–Laird pooling ([README](https://github.com/bhklab/icb_data_exploration_and_analysis/blob/main/README.md)). `bhklab/ORCESTRA` is the web application (Apache-2.0), not analysis code.

**Litchfield 2021 CPI1000+.** PMID 33508232 ([doi:10.1016/j.cell.2021.01.002](https://doi.org/10.1016/j.cell.2021.01.002)); code at <https://github.com/kevlitchfield1/CPI1000_paper>: per-figure plotting scripts with input tables. `code/Figure2/Fig2_script.R` pools with `meta::metagen(Effect, SE, sm = "OR")` at defaults. No licence; last push 2021-01-27. Not reusable as a pipeline.

**Lin 2026 atlas** (PMID 42679812, [doi:10.1016/j.ccell.2026.08.007](https://doi.org/10.1016/j.ccell.2026.08.007)). No public code repo found: none among the corresponding author's GitHub repos (`gh api users/dviraran/repos`), none in GitHub searches, and the Zenodo record ([10.5281/zenodo.19586163](https://doi.org/10.5281/zenodo.19586163)) lists only data files (`seurat_full.qs2` and four spatial zips). Code availability elsewhere is **UNVERIFIED**.

### 1.2 Generic meta-analysis tools

| Tool | What it does | Subgroups and small k | Status | Fit |
|---|---|---|---|---|
| **metafor** (R) | `escalc(measure = "SMD")` gives bias-corrected SMD (Hedges g) ([escalc.Rd](https://github.com/wviechtb/metafor/blob/master/man/escalc.Rd), line 130). `rma()` uses REML by default; `test = "knha"` is Knapp–Hartung; `test = "adhoc"` is KH with adjusted SEs never smaller than unadjusted, i.e. modified KH (Jackson 2017, §4.3) ([rma.uni.Rd](https://github.com/wviechtb/metafor/blob/master/man/rma.uni.Rd), lines 14, 73, 144). | `mods = ~ cancer` / `~ class`: meta-regression with an omnibus F test under KH; subsetting for per-group fits; `rma.mv` for multilevel structure. | CRAN 5.2-1 (2026-09-15), GitHub dev 5.3-2 (2026-10-28), GPL (≥ 2) | **Use**: matches the signed REML + modified KH |
| **meta** (R) | `metagen` with `method.random.ci = "HK"` and `adhoc.hakn.ci` ([metagen.Rd](https://github.com/guido-s/meta/blob/master/man/metagen.Rd)); `subgroup =`. Default CI is classic. Tutorial: Balduzzi 2019, PMID 31563865 ([doi:10.1136/ebmental-2019-300117](https://doi.org/10.1136/ebmental-2019-300117)). | Subgroup Q test | CRAN 8.5-0 (2026-05-25), GPL (≥ 2) | Optional (forest plots); set HK explicitly |
| MetaVolcanoR | DE p/FC/vote combination | n/a | Removed from Bioconductor (3.20 removal list, <https://bioconductor.org/about/removed-packages/>) | Skip |
| DExMA | expression meta-analysis with missing-gene handling | not checked | Bioc 1.20.0, GPL-2 | Skip |
| metaRNASeq | p-value combination only ([CRAN](https://cran.r-project.org/package=metaRNASeq)); Rau 2014, PMID 24678608 ([doi:10.1186/1471-2105-15-91](https://doi.org/10.1186/1471-2105-15-91)) | no effect sizes or τ² | 1.0.8 (2025-03-26) | Skip |
| RankProd | rank product; Hong 2006, PMID 16982708 ([doi:10.1093/bioinformatics/btl476](https://doi.org/10.1093/bioinformatics/btl476)) | no moderators | Bioc 3.38.0 | Skip |
| MetaIntegrator | multi-cohort effect sizes; Haynes 2017, PMID 27896970 ([doi:10.1142/9789813207813_0015](https://doi.org/10.1142/9789813207813_0015)) | n/a | CRAN archived 2024-10-14 | Skip |
| GeneMeta | Choi 2003, PMID 12855442 ([doi:10.1093/bioinformatics/btg1010](https://doi.org/10.1093/bioinformatics/btg1010)) | DL-type τ² | Bioc 1.84.0 | Skip |
| statsmodels `combine_effects` | Paule–Mandel or DL; HKSJ via `use_t` ([docs](https://www.statsmodels.org/stable/generated/statsmodels.stats.meta_analysis.combine_effects.html)) | **no REML** | 0.15.0 (2026-08-27), BSD-3 | Skip (sanity check at most) |
| PyMARE | REML, Knapp–Hartung covariance ([estimators.py](https://github.com/neurostuff/PyMARE/blob/master/pymare/estimators/estimators.py), lines 1305–1312, 639–668), meta-regression | moderators via design matrix | 0.0.13 (2026-09-29), MIT, pre-1.0 | Optional cross-check; no modified-KH option found (**UNVERIFIED** beyond this file) |

**Small k.** Paper A has per-cancer k = 10 (melanoma), 3 (lung), 2 (kidney, bladder) and 1 (gastric, liver, head and neck). Röver 2015 (PMID 26573817, [doi:10.1186/s12874-015-0091-1](https://doi.org/10.1186/s12874-015-0091-1)) recommends modified KH when studies are few with varying precision; Jackson 2017 (PMID 28748567, [doi:10.1002/sim.7411](https://doi.org/10.1002/sim.7411)) advises a standard random-effects sensitivity; Seide 2019 (PMID 30634920, [doi:10.1186/s12874-018-0618-3](https://doi.org/10.1186/s12874-018-0618-3)) studies likelihood-based random effects with few studies. k = 2 gives KH a t-distribution with 1 df; the plan should state up front how k ≤ 2 strata are reported. PredictioR's "Other" pooling mixes cancers and should not be copied.

---

## 2. Bulk expression analysis

| Need | Tool and source | Note for Paper A |
|---|---|---|
| Raw reads → counts | nf-core/rnaseq 3.27.0 (2026-09-23, MIT); Ewels 2020, PMID 32055031 ([doi:10.1038/s41587-020-0439-x](https://doi.org/10.1038/s41587-020-0439-x)) | Only if FASTQ are reprocessed; **skip** |
| NB DE on counts | DESeq2 1.52.0 (LGPL ≥ 3); Love 2014, PMID 25516281 ([doi:10.1186/s13059-014-0550-8](https://doi.org/10.1186/s13059-014-0550-8)). edgeR 4.10.7 (GPL ≥ 2); Chen 2025, PMID 39844453 ([doi:10.1093/nar/gkaf018](https://doi.org/10.1093/nar/gkaf018)) | Pick **one** NB engine; export log2FC + SE |
| Linear models | limma 3.68.5; Ritchie 2015, PMID 25605792 ([doi:10.1093/nar/gkv007](https://doi.org/10.1093/nar/gkv007)); voom: Law 2014, PMID 24485249 ([doi:10.1186/gb-2014-15-2-r29](https://doi.org/10.1186/gb-2014-15-2-r29)) | limma for arrays and log TPM/FPKM (limma-trend) |
| Python NB DE | PyDESeq2 0.5.4 (MIT); Muzellec 2023, PMID 37669147 ([doi:10.1093/bioinformatics/btad547](https://doi.org/10.1093/bioinformatics/btad547)) | Skip (second implementation) |
| PCA | DESeq2 `vst` + `plotPCA` (rnaseqGene: Love 2015, PMID 26674615, [doi:10.12688/f1000research.7035.1](https://doi.org/10.12688/f1000research.7035.1)); PCAtools 2.24.0 | `prcomp` is enough; PCAtools optional |
| Batch | sva 3.60.0; Leek 2012, PMID 22257669 ([doi:10.1093/bioinformatics/bts034](https://doi.org/10.1093/bioinformatics/bts034)); ComBat-seq: Zhang 2020, PMID 33015620 ([doi:10.1093/nargab/lqaa078](https://doi.org/10.1093/nargab/lqaa078)); RUVSeq: Risso 2014, PMID 25150836 ([doi:10.1038/nbt.2931](https://doi.org/10.1038/nbt.2931)) | Per-study effects + meta-analysis absorb between-study batch; within-study batch as a design covariate; `removeBatchEffect` for plots only |
| Enrichment | fgsea 1.38.0 (MIT); clusterProfiler 4.20.3 (Wu 2021, PMID 34557778, [doi:10.1016/j.xinn.2021.100141](https://doi.org/10.1016/j.xinn.2021.100141)); GSEApy 1.3.2 (Fang 2023, PMID 36426870, [doi:10.1093/bioinformatics/btac757](https://doi.org/10.1093/bioinformatics/btac757)); msigdbr 26.1.1 (MIT) | **fgsea** with msigdbr gene sets; MSigDB terms **UNVERIFIED** |
| Sample scores | GSVA 2.6.15 (Hänzelmann 2013, PMID 23323831, [doi:10.1186/1471-2105-14-7](https://doi.org/10.1186/1471-2105-14-7)); singscore 1.32.0 (Foroutan 2018, PMID 30400809, [doi:10.1186/s12859-018-2435-4](https://doi.org/10.1186/s12859-018-2435-4)); decoupleR 2.17.0 (Badia-i-Mompel 2022, PMID 36699385, [doi:10.1093/bioadv/vbac016](https://doi.org/10.1093/bioadv/vbac016)); PROGENy (Schubert 2018, PMID 29295995, [doi:10.1038/s41467-017-02391-6](https://doi.org/10.1038/s41467-017-02391-6)); CollecTRI (Müller-Dott 2023, PMID 37843125, [doi:10.1093/nar/gkad841](https://doi.org/10.1093/nar/gkad841)) | **singscore** is per-sample and platform-robust; GSVA is cohort-relative |
| Deconvolution | immunedeconv v2.1.4 (GitHub, GPL-2; `quantiseq`, `epic`, `mcp_counter`, `cibersort`; [README](https://github.com/omnideconv/immunedeconv)); Sturm 2019, PMID 31510660 ([doi:10.1093/bioinformatics/btz363](https://doi.org/10.1093/bioinformatics/btz363)) | quanTIseq via immunedeconv |
| Co-expression | WGCNA 1.74; Langfelder 2008, PMID 19114008 ([doi:10.1186/1471-2105-9-559](https://doi.org/10.1186/1471-2105-9-559)) | Not in Paper A's signed method (Paper B bridge uses module preservation) |
| Workflow references | rnaseqGene (above); RNAseq123: Law 2016, PMID 27441086 ([doi:10.12688/f1000research.9005.3](https://doi.org/10.12688/f1000research.9005.3)) | Code-style references |
| NanoString | NanoStringDiff 1.42.0 (Wang 2016, PMID 27471031, [doi:10.1093/nar/gkw677](https://doi.org/10.1093/nar/gkw677)); NanoTube 1.18.0; RUV normalisation: Bhattacharya 2021, PMID 32789507 ([doi:10.1093/bib/bbaa163](https://doi.org/10.1093/bib/bbaa163)) | Only normalised matrices here: limma on log2 values |

---

## 3. Single-cell analysis (QC, embedding, annotation check, pseudobulk only)

| Need | Tool and source | Note |
|---|---|---|
| Reference practice | Heumos 2023, *Nat Rev Genet*, PMID 37002403 ([doi:10.1038/s41576-023-00586-w](https://doi.org/10.1038/s41576-023-00586-w)); book repo `theislab/single-cell-best-practices` (Apache-2.0, 0.2.0, 2026-10-29) | Methods reference |
| Python core | scanpy 1.12.5 (Wolf 2018, PMID 29409532, [doi:10.1186/s13059-017-1382-0](https://doi.org/10.1186/s13059-017-1382-0)); anndata 0.13.4; scverse: Virshup 2023, PMID 37037904 ([doi:10.1038/s41587-023-01733-8](https://doi.org/10.1038/s41587-023-01733-8)); BSD-3, Python ≥ 3.12 | Prostate CELLxGENE h5ad |
| R core | Seurat 5.6.0 (MIT); SeuratObject 5.4.0; Hao 2024, PMID 37231261 ([doi:10.1038/s41587-023-01767-y](https://doi.org/10.1038/s41587-023-01767-y)) | Lin atlas stays in R |
| `.qs2` reading | qs2 0.4.0 (GPL-3), `qs_read()` ([README](https://github.com/qsbase/qs2)) | Required |
| Doublets / ambient RNA | scDblFinder 1.26.9 (Germain 2021, PMID 35814628, [doi:10.12688/f1000research.73600.2](https://doi.org/10.12688/f1000research.73600.2)); SoupX 1.6.2 (Young 2020, PMID 33367645, [doi:10.1093/gigascience/giaa151](https://doi.org/10.1093/gigascience/giaa151)); CellBender 0.4.0 (Fleming 2023, PMID 37550580, [doi:10.1038/s41592-023-01943-7](https://doi.org/10.1038/s41592-023-01943-7)) | SoupX/CellBender need raw droplets: **skip**; scDblFinder optional; otherwise audit QC metrics |
| Annotation check | CellTypist 1.7.1 (Domínguez Conde 2022, PMID 35549406, [doi:10.1126/science.abl5197](https://doi.org/10.1126/science.abl5197)); Azimuth 0.5.1 (Hao 2021, PMID 34062119, [doi:10.1016/j.cell.2021.04.048](https://doi.org/10.1016/j.cell.2021.04.048)) | Author labels + canonical-marker dot plots; CellTypist optional |
| Pseudobulk | muscat 1.26.0 (Crowell 2020, PMID 33257685, [doi:10.1038/s41467-020-19894-4](https://doi.org/10.1038/s41467-020-19894-4)); decoupler-py 2.3.1 `pp.pseudobulk` ([anndata.py](https://github.com/scverse/decoupler/blob/main/src/decoupler/pp/anndata.py), line 305); Squair 2021, PMID 34584091 ([doi:10.1038/s41467-021-25960-2](https://doi.org/10.1038/s41467-021-25960-2)); Murphy 2022, PMID 36550119 ([doi:10.1038/s41467-022-35519-4](https://doi.org/10.1038/s41467-022-35519-4)); Zimmerman 2021, PMID 33531494 ([doi:10.1038/s41467-021-21038-1](https://doi.org/10.1038/s41467-021-21038-1)) | Sum raw UMIs per sample × compartment; report at patient level |
| Integration / deep models | scvi-tools 1.5.2 (Gayoso 2022, PMID 35132262, [doi:10.1038/s41587-021-01206-w](https://doi.org/10.1038/s41587-021-01206-w)); pertpy 1.4.0 (Heumos 2026, PMID 41476114, [doi:10.1038/s41592-025-02909-7](https://doi.org/10.1038/s41592-025-02909-7)) | **Skip** |
| R↔Python conversion | anndataR (Bioc 1.2.3, [README](https://github.com/scverse/anndataR)); zellkonverter 1.22.0; SeuratDisk (last push 2023-11-04, Seurat v5 issues [#147](https://github.com/mojaveazure/seurat-disk/issues/147), [#191](https://github.com/mojaveazure/seurat-disk/issues/191)); anndata2ri 2.0.1 | Wang 2026 found conversion tools failing widely at scale (PMID 42894136, [doi:10.1186/s12864-026-13198-5](https://doi.org/10.1186/s12864-026-13198-5)). **Do not convert the 1.5M-cell object**: pseudobulk in R, export a compact table |

---

## 4. Recommended minimal stack

**Rule: statistics in R, orchestration and I/O in Python, one file contract between them.**

1. **Python** (existing pinned env): ingest, harmonisation, manifests, Hedges g inputs, result tables, figures; prostate h5ad single-cell with scanpy + decoupler-py pseudobulk.
2. **R 4.6 / Bioconductor 3.23**, pinned with **renv** (1.3.1, MIT; <https://github.com/rstudio/renv>): per-study DE (DESeq2 *or* edgeR; limma); `metafor::escalc(measure = "SMD")`, `rma(method = "REML", test = "adhoc")`, `mods = ~ cancer` / `~ class`; `p.adjust(method = "BH")`; fgsea, singscore, immunedeconv; Lin atlas QC and pseudobulk (`qs2::qs_read` → Seurat `AggregateExpression` or `muscat::aggregateData`).
3. **Bridge: `Rscript --vanilla` subprocess, not rpy2.** Each R module reads TSV/Parquet + JSON and writes TSV + `sessionInfo()`. Reasons: process isolation (rpy2 3.6.9 is GPL-2.0+ and needs a compatible R at runtime), each R step testable on fixed inputs, one lockfile per language.
4. **Layout to copy:** PredictioR's split (per-study association → meta → per-cancer / per-treatment wrappers, [R/](https://github.com/bhklab/PredictioR/tree/main/R)) with metafor REML + modified KH and no "Other" pooling; Bareche's `code/<analysis>/` + single driver (structure only; no licence).

### Tool table

| Tool | Purpose | Language | Licence | Last release (source) | Verdict |
|---|---|---|---|---|---|
| metafor | REML + modified KH, moderators | R | GPL (≥ 2) | 5.2-1, 2026-09-15 (CRAN) | **use** |
| meta | forest plots, cross-check | R | GPL (≥ 2) | 8.5-0, 2026-05-25 (CRAN) | optional |
| PredictioR | design reference | R | GPL-3 / MIT conflict | none; last commit 2025-09-17 | optional (read) |
| PredictIO (Bareche) | design reference | R | none | last commit 2022-09-28 | read only |
| CPI1000_paper | figure scripts | R | none | last push 2021-01-27 | skip |
| orcestra-downloader | ORCESTRA ICB objects | Py | MIT | 0.15.0, 2025-05-13 | optional |
| MetaVolcanoR / DExMA / metaRNASeq / RankProd / MetaIntegrator / GeneMeta | various | R | various | see 1.2 | skip |
| statsmodels meta | PM/DL + HKSJ | Py | BSD-3 | 0.15.0 | skip (no REML) |
| PyMARE | REML + KH | Py | MIT | 0.0.13 | optional cross-check |
| nf-core/rnaseq | FASTQ → counts | Nextflow | MIT | 3.27.0 | skip |
| DESeq2 / edgeR | NB DE | R | LGPL / GPL | 1.52.0 / 4.10.7 (Bioc 3.23) | **use one** |
| limma (+voom) | array, log-TPM, NanoString DE | R | GPL (≥ 2) | 3.68.5 | **use** |
| PyDESeq2 | NB DE in Python | Py | MIT | 0.5.4 | skip |
| PCAtools | PCA plots | R | GPL-3 | 2.24.0 | optional |
| sva / ComBat-seq | batch | R | Artistic-2.0 | 3.60.0 | optional (within-study) |
| RUVSeq | unwanted variation | R | Artistic-2.0 | 1.46.0 | skip |
| fgsea + msigdbr | ranked GSEA, gene sets | R | MIT | 1.38.0 / 26.1.1 | **use** |
| clusterProfiler / GSEApy | ORA/GSEA | R / Py | Artistic / BSD | 4.20.3 / 1.3.2 | skip |
| singscore | per-sample scores | R | GPL-3 | 1.32.0 | **use** |
| GSVA | cohort-relative scores | R | Artistic-2.0 | 2.6.15 | optional |
| decoupleR / decoupler-py | PROGENy, CollecTRI, pseudobulk | R / Py | GPL-3 / BSD-3 | 2.17.0 / 2.3.1 | optional / **use** (py pseudobulk) |
| immunedeconv | quanTIseq | R | GPL-2 | v2.1.4 (GitHub) | **use** |
| WGCNA | co-expression | R | GPL | 1.74 | skip (Paper A) |
| NanoStringDiff | NanoString NB DE | R | GPL | 1.42.0 | optional (raw RCC only) |
| scanpy + anndata | sc core | Py | BSD-3 | 1.12.5 / 0.13.4 | **use** |
| Seurat + SeuratObject + qs2 | sc core (Lin atlas) | R | MIT / GPL-3 | 5.6.0 / 0.4.0 | **use** |
| muscat | pseudobulk | R | GPL-3 | 1.26.0 | optional |
| scDblFinder | doublets | R | GPL-3 | 1.26.9 | optional |
| SoupX / CellBender | ambient RNA | R / Py | GPL-2 / BSD-3 | 1.6.2 / 0.4.0 | skip |
| CellTypist | annotation check | Py | MIT | 1.7.1 | optional |
| Azimuth / scvi-tools / pertpy / zellkonverter / SeuratDisk | various | — | — | — | skip |
| anndataR | Seurat ↔ AnnData | R | MIT | 1.2.3 | optional (small subsets) |
| anndata2ri / rpy2 | in-process bridge | Py | GPL | 2.0.1 / 3.6.9 | skip (use Rscript) |
| renv | R pinning | R | MIT | 1.3.1 | **use** |

### Open items
- Lin 2026 code availability: UNVERIFIED (check the paper's key resources table).
- PredictioR licence conflict: ask the maintainers before reusing code.
- PyMARE modified KH: not found; compare against metafor `test = "knha"` if a Python cross-check is wanted.
- k ≤ 2 cancer strata (kidney, bladder, gastric, liver, head and neck): state the reporting rule before running.

*Written by the coordinator from the research agent's report (the agent could not write files), 3 Nov 2026.*
