# Verification of the user's AI-tool leads (2026-10-30)

Every claim below was checked against a primary record: GEO `acc.cgi`, the recount3 S3 bucket (HEAD requests and project metadata), ARCHS4's public version API and download page, EBI Search, the CELLxGENE curation API, the Broad Single Cell Portal search API, the GitHub API, the Figshare API, and PMC full text.

**Rules followed:**
- Metadata only. No expression matrices were downloaded. The recount3 project metadata files (sample tables) were read only to count runs.
- No GSM or run IDs appear here, and nothing was committed.
- Where a site would not render without a browser, it is recorded as such and not worked around.

**Status key:** **CONFIRMED**, **WRONG**, **PARTLY**, **UNVERIFIED**.

---

## 1. Uniformly reprocessed hubs

### 1a. recount3 (Monorail)

Membership was checked by HEAD request on the project metadata and GENCODE v26 gene-sum files in the official bucket, `https://recount-opendata.s3.amazonaws.com/recount3/release/human/data_sources/sra/` (`metadata/<last2>/<project>/sra.recount_project.<project>.MD.gz` and `gene_sums/<last2>/<project>/sra.gene_sums.<project>.G026.gz`).

| Project | Cohort | In recount3 human `sra`? | Runs in recount3 | ENA RNA-Seq runs (from intake) |
| --- | --- | --- | ---: | ---: |
| SRP094781 | Riaz | **Yes** | 109 | 109 |
| SRP070710 | Hugo | **Yes** | 28 | 28 |
| ERP105482 | Gide | **Yes** | 91 | 91 |
| ERP107734 | Kim (gastric) | **Yes** | 45 | 78 (partial in recount3) |
| SRP150548 | GSE115821 | **Yes** | 31 | 37 (partial in recount3) |
| SRP155030 | Zhao GBM | No (404) | — | 34 |
| SRP217040 | GSE135222 | No | — | 27 |
| SRP250849 | GSE145996 | No | — | 42 |
| SRP302761 | GSE165278 | No | — | 149 |
| SRP183455 | GSE126044 | No | — | 16 |
| SRP425656 (PRJNA940989) | Vos salivary gland | No | — | 45 |

**5 of 11 are in recount3.** Its SRA snapshot predates the later projects. For Kim and GSE115821 not every run is included, so the missing runs need checking against the patient map.

**Pipeline documentation:**
- **Paper:** Wilks et al. 2021, *Genome Biol*, PMID 34844637 (PMC8628444). It describes "over 750,000 publicly available human and mouse RNA sequencing (RNA-seq) samples uniformly processed by our new Monorail analysis pipeline".
- **Aligner:** STAR. Version **2.7.3a**: "the versions of the 3 tools that use them in recount-pump are: STAR 2.7.3a" (`langmead-lab/monorail-external` README).
- **Reference and annotation:** "Reference indexes + annotations are already built/extracted for human (HG38, Gencode V26)" (same README). Gene sums are also offered for GENCODE v29, FANTOM6-CAT, RefSeq, ERCC and SIRV (`recount3` R package annotation options). The file suffix `G026` = GENCODE v26.
- **Quantification and units:** not a read-count quantifier. "Monorail uses Megadepth to analyze the spliced-alignment BAM file output by STAR… The result is a tab-separated value (TSV) file containing coverage sums across all genes and exons" (paper, Methods). Units are **base-pair coverage sums**. They must be scaled to read counts (the `recount3::transform_counts` step) before count-based methods are used.
- **Images:** recount-pump 1.1.3 and recount-unify 1.1.1 are the current public images (README). The README advises that studies unified before 2022-02-19 be re-unified because of a gene-collision bug. Which image produced each release project is **UNVERIFIED**.

**Verdict:** documented well enough to pass a processing check (aligner + version, reference, annotation, quantification method, units). The two caveats are coverage-sum units and partial run coverage for Kim and GSE115821. It is the strongest uniform source for the 5 projects it holds.

### 1b. ARCHS4

| Item | Finding | Source |
| --- | --- | --- |
| Current release | Download page: "ARCHS4 Version 2.5 (Ensembl 107)", human gene file dated 2024-08-24. The public version API lists rolling "latest" human gene files, the newest dated **2026-07-04, with 1,098,771 samples, Ensembl 107** | `maayanlab.cloud/archs4/download.html`; `https://archs4.org/api/versionfile` |
| Quantifier | kallisto ("the Kallisto aligner is applied in an efficient parallelized cloud infrastructure"); "Kallisto pseudocounts are rounded to integer values"; gene level by symbol | ARCHS4 site |
| kallisto version | **Not stated** on the download page. The kallisto index files are downloadable, so the index can be pinned. **UNVERIFIED** | download page |
| Annotation | "The Ensembl Annotation version is 107 for both human and mouse data" | download page |
| ENA-only (ERP) projects | ARCHS4 is indexed by GEO sample (GSM). The site describes "all human and mouse RNA-seq experiments from the Gene Expression Omnibus (GEO) and the Sequence Read Archive (SRA)", and metadata are "retrieved from GEO for GSM samples". Projects with no GEO series (ERP105482 Gide, ERP107734 Kim) are therefore **expected to be absent** (UNVERIFIED) | site text |
| Membership of the 11 projects | **UNVERIFIED.** No per-series lookup API was found; checking needs the 45 GB H5 metadata, which was not downloaded | — |

**Verdict:** a uniform kallisto + Ensembl 107 pipeline, but the kallisto version is not on the page and per-project membership is unverified. Useful for GEO-linked projects only.

### 1c. Expression Atlas

EBI Search (`atlas-experiments` domain) for nivolumab, pembrolizumab, ipilimumab, atezolizumab, durvalumab, "immune checkpoint" and anti-PD-1 returns a single hit: **E-MTAB-6214**, "Bulk RNA-seq validation experiment comparing blood from healthy donors and two groups of metastatic melanoma patients: responders and non-responders to anti-PD-1 immunotherapy". That is blood, not tumour.

**Verdict:** no tumour ICI cohort.

---

## 2. Single-cell ICI datasets

| Lead | Status | Title (GEO) | Cancer | Regimen | Patients / samples | Response labels | Pre / on | Access |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSE115978 (Jerby-Arnon 2018) | **CONFIRMED** (PMID 30388455) | "Single-cell RNA-seq of melanoma ecosystems reveals sources of T cells exclusion linked to immunotherapy clinical outcomes" | Melanoma | ICI-naive vs post-ICI tumours | 31 tumours; Smart-seq2 | Not response: ICI exposure / resistance status (paper) | Untreated and post-ICI | GEO processed; raw: "will be made available through dbGaP" |
| GSE120575 (Sade-Feldman 2018) | **CONFIRMED** (PMID 30388456) | "Defining T cell states associated with response to checkpoint immunotherapy in melanoma" | Melanoma | PD-1 (35 samples), CTLA-4 (2), PD-1 + CTLA-4 (11) | 48 samples, 16,291 CD45+ cells | GEO `response`: Responder 17 / Non-responder 31 samples | Pre (baseline) and post (on treatment) | GEO processed; raw dbGaP phs001680; also Broad SCP398 |
| GSE123813 (Yost 2019) | **CONFIRMED** (PMID 31359002; SubSeries of GSE123814) | "Clonal replacement of tumor-specific T cells following PD-1 blockade [single cells]" | Basal cell carcinoma (+ SCC, per paper) | PD-1 | 14 donors, 86 samples (sorted fractions) | Not in GEO; in the paper (UNVERIFIED) | Pre 45 / post 41 samples | GEO + SRA (SRP173389) |
| "Bi 2021 RCC, GSE156728" | **WRONG.** GSE156728 is "Pan-Cancer Single Cell Landscape of Tumor-Infiltrating T Cells" (PMID 34914499) | Bi et al. 2021 (*Cancer Cell*, PMID 33711272) is on **Broad SCP1288**, "Tumor and immune reprogramming during immunotherapy in advanced renal cell carcinoma"; raw dbGaP phs002065 | ccRCC | PD-1 ± CTLA-4 (per paper; UNVERIFIED) | UNVERIFIED | UNVERIFIED | ICI-exposed vs naive | SCP (public study); raw controlled |
| "Zhang 2021, GSE179368" | **WRONG.** GSE179368 is "The METTL3-m6A pathway is a master regulator of muscle maintenance and growth" (mouse) | Zhang et al. 2021 (*Cancer Cell*, PMID 34653365) is **GSE169246**, "PD-L1 blockade-induced temporal single cell dynamics in triple negative breast cancer", 83 samples | TNBC | **COMBINATION**: paclitaxel ± atezolizumab | UNVERIFIED | Paper | Pre / on | GEO processed; raw GSA |

### Other public single-cell ICI datasets found on portals (study level)

| Portal | Licence and raw counts | ICI datasets found |
| --- | --- | --- |
| **Broad Single Cell Portal** (search API) | Licence set per study (UNVERIFIED for each); raw counts depend on the submitter | SCP398 (Sade-Feldman); SCP109 "Melanoma immunotherapy resistance" (Jerby-Arnon); SCP1288 (Bi RCC); SCP2510 "Human lung cancer harbors spatially-organized stem-immunity hubs that associate with response to immunotherapy"; SCP3341 "Tumor Transcriptional Subtype Is a Key Axis of Immune Checkpoint Blockade Response in Glioblastoma"; SCP3121 "Dysregulation of the Hippo Pathway in Stromal Cells is Associated with Immune Checkpoint Inhibitor R[esponse]…"; SCP837 (blood, nivolumab) |
| **CELLxGENE Discover** (curation API, 404 collections) | CELLxGENE publishes datasets under CC BY 4.0 and its schema carries raw counts (both **UNVERIFIED** for these specific datasets) | "Integrated cancer cell-specific single-cell RNA-seq datasets of immune checkpoint blockade-treated patients" (*Sci Data* 2025, doi 10.1038/s41597-025-04381-6); Krishna 2021 ccRCC (doi 10.1016/j.ccell.2021.03.007) |
| **TISCH2** | Gallery is rendered in the browser; no machine-readable list found from the static page | **Not harvested** (immunotherapy filter not reachable without a browser) |

Patient-level response for the portal datasets above is UNVERIFIED unless shown in the table.

---

## 3. Corrections

| Claim | Verdict | Evidence |
| --- | --- | --- |
| GSE135222 is Jung 2019, not "Ravi 2023" | **CONFIRMED** | GEO: "DNA methylation loss coupled with mitotic cell division promotes immune evasion of tumours with high mutation load [RNA-seq]", PMID 31537801; 27 NSCLC patients on anti-PD-1/PD-L1 |
| GSE126044 is Cho, not Jung | **CONFIRMED** | GEO: "Genome-wide identification of differentially methylated promoters and enhancers associated with response to anti-PD-1 therapy in non-small cell lung cancer", PMID 32879421 (Cho et al. 2020). **Further correction:** Hwang 2020 (PMID 31959763, the BHK/ORCESTRA "Hwang" cohort) cites **GSE136961**, not GSE126044. Fixed in `ICB_DATABASES_HARVEST_20261030.md` |
| Braun 2020 is *Nat Med*; n = 311 includes the everolimus arm | **CONFIRMED** | PubMed: *Nat Med* 2020, PMID 32472114. PMC7499153: "within the overall group of 311 patients with RNA-seq", and the study spans anti-PD-1 and mTOR-inhibitor arms ("261 patients treated with anti-PD1, 193 patients treated with mTOR inhibition" for WES). The anti-PD-1 RNA subset is smaller (181 in the BHK inventory); exclude everolimus for A/B |
| "Padron 2022, GSE153960" | **WRONG accession.** GSE153960 is "Truncated stathmin-2 is a marker of TDP-43 pathology in frontotemporal dementia" (ALS/FTD postmortem). PRINCE (PMID 35662283, PMC9205784) cites no GEO series (only a Zenodo DOI); its data are on cBioPortal `paad_iatlas_prince_2022` and ORCESTRA `ICB_Padron` | — |
| PRINCE is chemo ± nivolumab, i.e. a combination | **CONFIRMED, more precisely:** patients were "randomized to receive nivo/chemo, sotiga/chemo or sotiga/nivo/chemo" (gemcitabine + nab-paclitaxel in every arm). **There is no ICI-only arm.** The registry's "mixed study, check for an ICI-only arm" can be closed: all arms are COMBINATION | PMC9205784 |
| GitHub "SISIR-Omics/IMvigor210CoreBiologies" | **DOES NOT EXIST.** The repo and the `SISIR-Omics` user both return 404. Two unofficial, non-fork mirrors exist (`SiYangming/IMvigor210CoreBiologies`, `BioInfoCloud/IMvigor210CoreBiologies`). The official package is served by Genentech at `http://research-pub.gene.com/IMvigor210CoreBiologies/`. Nothing was installed | GitHub API |

---

## 4. Cancer-Immu (PMID 34903605, PMC9189237)

**Figshare file 39877785: CONFIRMED.**
- It is the single file of Figshare article **22431438**, "Supplementary Table from A Pan-Cancer Immunogenomic Atlas for Immune Checkpoint Blockade Immunotherapy".
- DOI 10.1158/0008-5472.22431438.v1, published 2023-03-31, licence **CC BY**.
- File `can-21-2335_supplementary_tables_s1-s4_supps1-4.xlsx`, **4,007,553 bytes** (Figshare API). This is byte-identical in size to the copy read earlier through the Europe PMC supplementary-files API, so Table S1 was read from that copy; Figshare was not downloaded again.
- Note: `api.figshare.com/v2/articles/39877785` returns "Entity not found", because 39877785 is a **file** ID, not an article ID.

**Table S1, study level.** Status is marked against the intake and harvest files: IN_PIPELINE / IN_INTAKE / KNOWN (already in the harvest or expanded notes) / NEW.

| Cancer-Immu source | Accession / route | Data | Status |
| --- | --- | --- | --- |
| Auslander (melanoma) | GSE115821 | RNA 37 | IN_PIPELINE (parked) |
| Chen (melanoma) | PMC5082984 supplement | RNA 104 (NanoString) | KNOWN (harvest NEW list) |
| Hugo | GSE78220 | RNA 28 | IN_PIPELINE |
| Prat | GSE93157 | RNA 25 (melanoma part) | IN_INTAKE |
| Riaz | GSE91061 | RNA 117 | IN_PIPELINE |
| Samstein (all rows) | cBioPortal `tmb_mskcc_2018` | panel DNA only | KNOWN (set aside: no RNA) |
| Snyder-Nathanson | PMC4315319 supplement | RNA 24 | KNOWN (harvest: Nathanson NEW; Snyder 2014 known) |
| Van Allen | phs000452 | RNA 42 | IN_INTAKE |
| Liu | PMC6898788 supplement | RNA 114 | IN_PIPELINE |
| Jerby-Arnon validation cohort 2 | GitHub wiki | RNA 112 | KNOWN (harvest NEW list) |
| Gide | PRJEB23709 | RNA 91 | IN_PIPELINE |
| Sade-Feldman | GSE120575 | scRNA 48 | KNOWN (harvest 2d) |
| Krieg (melanoma) | FlowRepository 1124 | CyTOF | **NEW, but not RNA** (set aside) |
| Rizvi H. / Rizvi N. (NSCLC) | cBioPortal | DNA only | KNOWN (set aside) |
| Mariathasan | EGAS00001002556 | RNA 348 | IN_PIPELINE (locked final test) |
| Miao (RCC) | phs001493 | RNA 33 | IN_INTAKE |
| Harding (HCC) | cBioPortal `hcc_mskimpact_2018` | panel DNA only | **NEW, but no RNA** (set aside) |
| Kim (gastric) | PRJEB25780 | RNA 61 | IN_INTAKE |
| Kwek (prostate) | GSE39688 | protein array | KNOWN (set aside) |
| Le (CRC) | supplement | DNA only | **NEW, but no RNA** (set aside) |
| Cloughesy (GBM) | GSE121810 | RNA 29 | KNOWN (expanded-note candidate) |
| Yost (BCC) | GSE123814 | scRNA | **NEW** (single-cell; see section 2) |

Cancer-Immu adds **no new bulk-RNA ICI cohort**. Its only new items are single-cell (Yost) or non-RNA (Krieg CyTOF, Harding and Le DNA).

---

## 5. Plain summary

1. **recount3 is the strongest uniform source, but for only 5 of the 11 projects**: Riaz, Hugo, Gide, Kim and GSE115821, the last two partially. Its pipeline is documented (STAR 2.7.3a, hg38, GENCODE v26, Megadepth coverage sums), and the coverage-sum units must be converted before count-based use. The six newer projects, including GSE135222, GSE145996, GSE165278 and the salivary trial, are not in it.
2. **ARCHS4:** kallisto + Ensembl 107, latest public file July 2026. It is GEO-indexed, so the ENA-only Gide and Kim are expected to be absent. Its kallisto version and per-project membership are unverified. **Expression Atlas** has no tumour ICI cohort (one blood study only).
3. **Single-cell leads:** GSE115978, GSE120575 and GSE123813 are confirmed. "Bi 2021 = GSE156728" is **wrong** (that is a pan-cancer T-cell atlas; Bi is Broad SCP1288). "Zhang 2021 = GSE179368" is **wrong** (that is a mouse muscle study; Zhang TNBC is GSE169246 and is a chemotherapy combination).
4. **Corrections:**
   - Confirmed: GSE135222 = Jung, GSE126044 = Cho, and Braun's 311 includes everolimus.
   - "GSE153960" is **not** PRINCE (it is an ALS dataset). PRINCE has no ICI-only arm (every arm contains chemotherapy).
   - "SISIR-Omics/IMvigor210CoreBiologies" **does not exist**; the official package is Genentech's site.
   - Also found: ORCESTRA's "Hwang" cohort is GSE136961, not GSE126044. This is now fixed in the harvest note, and the ORCESTRA + IOhub coverage there becomes 29/86 (34%).
5. **Cancer-Immu:** Figshare file 39877785 exists (CC BY, 4.0 MB; article 22431438) and is the same Table S1/S4 workbook. It adds no new bulk-RNA ICI cohort, only Yost (single-cell) and three non-RNA studies.
