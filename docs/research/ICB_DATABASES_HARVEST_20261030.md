# ICB database harvest: cohorts beyond ICBatlas (2026-10-30)

This note is study-level metadata only. No expression or clinical data were downloaded. Patient-level files were not saved or quoted; one public study-level inventory that contains patient rows (the BHK lab `ICB_Cohorts.csv`) was read only to count patients per study. Nothing was committed. When a site blocked or timed out on automated access, it is recorded as **BLOCKED** or **UNREACHABLE**, and its paper, supplement or GitHub was used instead. No firewall, CAPTCHA, login or JavaScript interstitial was bypassed. Anything not confirmed from a primary record is marked **UNVERIFIED**.

The comparison sets are `docs/integration/20261030-data-assessment/ICBATLAS_INTAKE.md` and `docs/research/ICI_COHORT_SEARCH_EXPANDED_20261028.md`.

**Status values:**
- **IN_PIPELINE**: admitted, signing, worksheet open, final test or parked.
- **IN_ICBATLAS_INTAKE**: listed in the intake plan, not started.
- **NEW**.
- **KNOWN_CANDIDATE** (added): already qualified, set aside or unlocated in the expanded cohort note, but not in the pipeline or intake. It is added so these are not counted as new.

**COMBINATION** = ICI given with a non-ICI agent (rule: `docs/decisions/COMBINATION_COHORTS_20261029.md`).

---

## 1. Databases

| Database | Paper | Access route (as tried 30 Oct) | Human ICI cohorts | Cohort list downloadable? | Harvested? |
| --- | --- | --- | --- | --- | --- |
| **TIGER** | Chen et al. 2023, *Genomics Proteomics Bioinformatics*, PMID 36049666 (PMC10626175) | https timed out (**UNREACHABLE**); the http site loads (single-page app) | Paper: "40 datasets of 18 cancer types" (includes non-ICI: adoptive cell therapy, DC and peptide vaccines). The site's code lists 25 response datasets from about 13 distinct ICI studies | No file. The list was read from the site's public JavaScript bundle | Yes |
| **CRI iAtlas, ICI modules** | Eddy et al. 2020, *F1000Research*, PMID 33214875 | Portal (https timed out); GitHub `CRI-iAtlas/iatlasManifests` (dataset scripts); cBioPortal "iAtlas Harmonized" studies (13 ICI studies via the API) | About 22 bulk ICI datasets (RNA-seq + NanoString), plus scRNA datasets | Yes (GitHub manifests; cBioPortal API) | Yes |
| **IOhub** | Zhang et al. 2024, bioRxiv review, PMID 39713380 (PMC11661151) | Portal URL not given in the PMC text; not located | "36 bulk and 10 single-cell transcriptome datasets" (paper) | Not found | **No** (list not located) |
| **TIDE** (Jiang 2018) | PMID 30127393 (PMC6487502) | Site redirects to `cide.ccr.cancer.gov/tide`, which returns 403 (**BLOCKED**) | Cohorts are named in the paper supplement (PDF, not parsed); later updates were not reachable | Not via the site | **No** (BLOCKED; its cohorts are covered by the other databases) |
| **Cancer-Immu** | Yang et al. 2021, *Cancer Res*, PMID 34903605 (PMC9189237) | Site returned 404 (**UNREACHABLE**); Supplementary Table S1 via the Europe PMC supplementary-files API | 33 data-source rows; 16 with ICI transcriptomes (the rest WES-only, single-cell or protein) | Yes (supplement S1) | Yes |
| **ICBdb** | Not found in PubMed | — | — | — | Does not appear to exist under that name |
| **PredictIO** (= Bareche 2022) | Bareche et al. 2022, *Ann Oncol*, PMID 36055464 (not in PMC) | predictio.ca reachable; GitHub `bhklab/PredictIO-webapp` seed table (25 datasets); `bhklab/icb_data_exploration_and_analysis` (study inventory, 19 studies with clinical data) | 25 datasets (some WES-only) | Yes (GitHub CSV) | Yes |
| **ORCESTRA ICB** (BHK lab) | Mammoliti et al. 2021, *Nat Commun*, PMID 34608132 | Public API `orcestra.ca/api/clinical_icb/available`; each dataset has a Zenodo record; GitHub `BHKLAB-DataProcessing/ICB_*` (27 study repositories) | 21 curated ICB data objects | Yes (JSON API) | Yes |
| **Litchfield 2021 (CPI1000+)** | *Cell*, PMID 33508232 (PMC7933824) | Paper text; supplement archive came back truncated | 12 cohorts, 7 tumour types, >1,000 patients | Partly (cohort names in the text) | Partly (RNA cohorts are all known: Riaz, Hugo, Van Allen, Liu, Mariathasan, McDermott, Miao, Snyder, Zhao, Cristescu…) |
| **CPI1000+ atlas** | *Nat Commun* 2024, PMID 38969631 (PMC11226649) | Supplement archive truncated | UNVERIFIED | Not obtained | No |
| **TCCIA** | *J Immunother Cancer* 2024, PMID 38212124 (PMC10806567) | Supplementary Table 1 via Europe PMC | 25 ICI cohorts | Yes (supplement) | Yes |
| **COMPASS** | *Nat Med* 2026, PMID 42399673 (PMC13472881) | Extended Data Table 1 is an image; accessions taken from the text | 16 cohorts, 1,133 patients | Accessions only | Yes (accessions) |
| **CAMOIP** | *Brief Bioinform* 2022, PMID 35395670 (not in PMC) | Site timed out (**UNREACHABLE**) | UNVERIFIED | No | No |
| **Immu-Mela** | *J Genet Genomics* 2021, PMID 34127402 (PMC8349898) | Europe PMC supplement call returned an empty response; melanoma only | UNVERIFIED (melanoma) | Not obtained | No (melanoma cohorts are covered by other databases) |
| **ICBcomb** | *Brief Bioinform* 2023, PMID 38095856 (PMC10753530) | Paper Table 1 only (supplement archive truncated) | 10 human datasets (mostly combination therapy; CLL, uveal melanoma, HCC, lymphoma…) and 66 mouse datasets | No | Summary only |
| **easier** | Lapuente-Santana et al. 2021, *Patterns*, PMID 34430923 | Reuses published cohorts | — | — | Not a new source |
| **TISMO** | PMID 34534350 | Mouse only | — | — | Skipped (mouse) |
| **ImmuneDB** | No ICI database by that name found | — | — | — | — |
| ICBatlas | (known) | — | — | — | Skipped (in the intake already) |

---

## 2. Merged cohort table

Patients = patients with pre-treatment tumour RNA where known. The Databases column uses these abbreviations: TG = TIGER, IA = iAtlas, CI = Cancer-Immu, PIO = PredictIO/BHK, ORC = ORCESTRA, TC = TCCIA, CMP = COMPASS, CPI = CPI1000+.

### 2a. NEW

| Cohort | Accession(s) | PMID | Cancer | Regimen (ICI class) | Pre-tx RNA patients | Response labels | Databases | Access route (FASTQ size) |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| IMmotion151 | EGAD00001006619 | (Motzer 2020, *Cancer Cell*) | RCC | **COMBINATION**: atezolizumab + bevacizumab vs sunitinib | 823 (dataset size; both arms) | PFS; ORR | TC | EGA controlled |
| IMvigor010 | EGAD00001007575 | (Bellmunt 2021, *Lancet Oncol*) | Urothelial, adjuvant | PD-L1 (atezolizumab) vs observation | 728 (dataset size; both arms) | DFS/OS (adjuvant; no RECIST) | TC | EGA controlled |
| SU2C-MARK NSCLC | phs002822 | (Ravi 2023) | NSCLC | PD-(L)1 ± CTLA-4 | UNVERIFIED (large) | RECIST / PFS | CMP | dbGaP controlled |
| Jerby-Arnon validation cohort 2 | — (GitHub `livnatje/ImmuneResistance`; Broad single-cell portal; ORCESTRA `ICB_Jerby_Arnon`) | 30388455 | Melanoma | PD-1 | 112 | Response + PFS (paper) | CI, PIO, ORC | Processed: TPM of program genes public (portal/supplement); the ORCESTRA object is 0.5 MB, likely a gene subset (UNVERIFIED). Patient overlap with other Essen/MGH/Wistar cohorts UNVERIFIED |
| Chen 2016 (NanoString) | supplement (PMC5082984) | 27301722 | Melanoma | CTLA-4 then PD-1 | 104 samples (pre + on; pre count UNVERIFIED) | Response (paper) | CI, IA | Supplement (**panel**) |
| AMADEUS | GitHub `ParkerICI/amadeus-trial-data` | 39190534 | Pan-tumour (various) | PD-1 + CTLA-4 (72) / PD-1 (7); ICI only | ≤79 treated; baseline-RNA n UNVERIFIED | RECIST BOR, CR/PR flag, disease control (≥6 mo SD) | IA | **Open**: raw counts + TPM, baseline **and on-treatment**, plus a per-patient prior-therapy file |
| Vos 2023 salivary gland | PRJNA940989 (SRP425656); Zenodo 8180441 | 37620627 | Salivary gland carcinoma | PD-1 + CTLA-4 | 64 treated; 45 RNA-seq runs (pre/on split UNVERIFIED) | RECIST ORR | TC | **ENA public FASTQ**: 44 of 45 RNA-Seq runs public, **116.4 GB** |
| Rosenbaum 2023 sarcoma | phs003284 | (Rosenbaum 2023) | Sarcoma | **COMBINATION**: PD-1 + IL-2 agonist / IDO1 / T-VEC | 64 (dataset size) | Trial endpoints | TC | dbGaP controlled |
| Cui 2021 (PUCH) | HRA000524; ORCESTRA `ICB_Puch` | 33542239 | Melanoma (incl. acral/mucosal; UNVERIFIED) | PD-1 | 55 (BHK) / 59 (TCCIA) | R/NR (BHK: 14 R / 35 NR / 6 NA) | PIO, ORC, TC | Processed: ORCESTRA Zenodo object (5 MB); raw: GSA-Human controlled |
| Grasso 2020 | EGAD00001006282 | 33306984 | Melanoma | PD-1 ± CTLA-4 | 54 (dataset size) | RECIST | TC | EGA controlled |
| Roper 2021 SCLC | phs002176 | (Roper 2021, *Nat Commun*) | SCLC, relapsed | PD-1 alone; **COMBINATION** arm PD-L1 + PARP | 46 (dataset size) | Trial endpoints | TC | dbGaP controlled |
| Snyder 2017 urothelial | Zenodo 546110 (kallisto, 63.7 MB); GitHub `hammerlab/multi-omic-urothelial-anti-pdl1` | 28552987 | Urothelial | PD-L1 (atezolizumab) | 25 (BHK; 26 RNA in paper) | R/NR (8 R / 10 NR / 7 NA) | PIO, ORC, CPI | **Open processed** (kallisto); raw not located |
| Nathanson 2017 | ORCESTRA `ICB_Nathanson` (Zenodo) | 27956380 | Melanoma | CTLA-4 | 24 (includes ≥1 post-treatment lesion) | R/NR (10 / 14) | TG, CI, PIO, ORC | Processed FPKM via ORCESTRA; raw UNVERIFIED (the expanded note had it as "not located") |
| phs001427 | phs001427 | (Sade-Feldman 2017) | Melanoma | PD-1 + CTLA-4 | 20 | Trial | TC | dbGaP controlled |
| Gettinger 2017 | phs001464 | (Gettinger 2017, *Cancer Discov*) | NSCLC, acquired resistance | PD-(L)1 ± CTLA-4; one arm + erlotinib (**COMBINATION**) | 19 | Acquired resistance | TC | dbGaP controlled |
| Amato 2020 | PRJNA639866 is WXS only (120 runs); RNA accession UNVERIFIED | 32708981 | Melanoma | PD-1 | UNVERIFIED | Response (paper) | IOhub | RNA route UNVERIFIED |
| Quintela-Fandino 2020 | GSE139050 (6 samples) | 33176887 | Breast, HER2-negative | **COMBINATION**: durvalumab + bevacizumab | ≤6 | Trial | IOhub | GEO public |
| Nguyen 2023 BRCA | phs003316 | (Nguyen 2023) | Breast, HER2-negative | **COMBINATION**: PD-1 + CTLA-4 + T-VEC | 10 | Trial | TC | dbGaP controlled |
| Freeman 2022 melanoma | phs002683 | (Freeman 2022) | Melanoma | PD-1 ± CTLA-4 | UNVERIFIED | Response / survival | CMP | dbGaP controlled |
| Limagne 2022 (two cohorts) | ORCESTRA `ICB_Limagne1`, `ICB_Limagne2` (Zenodo) | 35051357 | NSCLC | **COMBINATION**: chemotherapy + PD-(L)1 (UNVERIFIED per cohort) | UNVERIFIED (objects 66 MB and 81 MB) | UNVERIFIED | PIO, ORC | Processed via ORCESTRA; raw UNVERIFIED |
| Schalper/Melero 2019 GBM (NanoString) | iAtlas `Melero_GBM_2019` | 30742120 | Glioblastoma, neoadjuvant | PD-1 (nivolumab) | UNVERIFIED | UNVERIFIED | IA | Via iAtlas (**panel**) |
| INSPIRE | BHK `ICB_INSPIRE` repos | (Princess Margaret pan-cancer pembrolizumab) | Pan-cancer | PD-1 | UNVERIFIED | UNVERIFIED | PIO | Not on the ORCESTRA available list; access UNVERIFIED |

### 2b. IN_PIPELINE

| Cohort | Accession(s) | PMID | Cancer | Regimen | Pre-tx RNA patients (intake) | Databases |
| --- | --- | --- | --- | --- | ---: | --- |
| Riaz | GSE91061 / PRJNA356761 | 29033130 | Melanoma | PD-1 (± prior CTLA-4) | 49 | TG, IA, CI, PIO, ORC, TC, CMP, CPI |
| Hugo | GSE78220 / PRJNA312948 | 26997480 | Melanoma | PD-1 | 27 | TG, IA, CI, PIO, ORC, TC, CMP, CPI |
| Liu 2019 | phs000452 (PD-1 arm) | 31792460 | Melanoma | PD-1 | 120 | TG, IA, CI, PIO, ORC, TC, CMP, CPI |
| Gide | PRJEB23709 | 30753825 | Melanoma | PD-1 / PD-1 + CTLA-4 | 73 | TG, IA, CI, PIO, ORC, TC, CMP |
| IMvigor210 (Mariathasan) | EGAS00001002556 | 29443960 | Urothelial | PD-L1 | 298 (locked final test) | IA, CI, PIO, ORC, TC, CMP, CPI |
| UNC bladder (Damrauer 2022; Rose 2021 likely same family, UNVERIFIED) | GSE176307 | 36333289 / 34294892 | Urothelial | PD-(L)1 | 89 | IA, CMP |
| Auslander | GSE115821 / PRJNA476140 | 30127394 | Melanoma | PD-1 / CTLA-4 | 14 (parked) | TG, CI, TC |
| Cho 2020 (corrected 30 Oct: GEO PMID 32879421; it was labelled "Hwang" here before) | GSE126044 | 32879421 | NSCLC | PD-1 | 16 (parked) | TG, IOhub |
| — | GSE168204, GSE248014 | — | Melanoma; PDAC (COMBINATION) | — | (pipeline) | none of these databases |

### 2c. IN_ICBATLAS_INTAKE

| Cohort | Accession(s) | Cancer | Pre-tx RNA patients | Databases |
| --- | --- | --- | ---: | --- |
| Jung | GSE135222 | NSCLC | 27 | TG, PIO, ORC |
| GSE145996 | GSE145996 | Melanoma | 14 | TG |
| Zappasodi 2021 | GSE165278 | Melanoma (CTLA-4) | 7 | IA |
| Zhao | PRJNA482620 | GBM | 26 | TG, IA, CMP |
| Kim | PRJEB25780 | Gastric | 45 | TG, IA, CI, PIO, ORC, TC, CMP |
| Braun | EGAS00001004290/1 (supplement route) | RCC | 281 | TG, PIO, ORC |
| Shiuan | PMID 33806963 | RCC | 13 | PIO, ORC |
| Van Allen | phs000452 (CTLA-4 arm) | Melanoma | 41 | CI, PIO, ORC, TC, CPI |
| Miao | phs001493 | RCC | 33 | CI, PIO, ORC, TC, CMP, CPI |
| Tumeh | phs001919 | Melanoma | 27 | TC |
| Prat | GSE93157 | HNSCC / melanoma / NSCLC | 65 | TG, IA, CI |
| GSE67501 | GSE67501 | RCC | 11 | TG |
| Hwang 2020 (BHK/ORCESTRA `ICB_Hwang`; PMC6971301 cites GSE136961) | GSE136961 | NSCLC | 21 | PIO, ORC |
| GSE99070, GSE122220, GSE140901, GSE111636, TCGA anti-CTLA-4 subset | — | various | see intake | (not in these databases) |

### 2d. KNOWN_CANDIDATE (in the expanded note, not pipeline or intake)

IMmotion150 (EGAS00001002928; IA, TC, CMP; COMBINATION arm), Anders TNBC (IA), PRINCE/Padrón PDAC (IA, PIO, ORC; COMBINATION), Choueiri RCC (IA), Prins GBM (IA), Cloughesy GBM GSE121810 (CI), PORTER mCRPC (IA), Snyder 2014 melanoma (`skcm_mskcc_2014` / phs001038; TC), van den Ende PERFECT GSE165252 (PIO, ORC; COMBINATION), Liu S 2021 neoadjuvant oral-cavity SCC = GSE179730 / PRJNA744780 (TC; public FASTQ, 23 RNA-Seq runs, 174.4 GB; corrected 30 Oct, it was first listed as NEW), Obradovic 2022 HNSCC GSE195832 (IOhub), He 2021 thymic carcinoma GSE181815 (IOhub), OAK/POPLAR (EGAD00001008548/9; TC; chemotherapy comparator), Cristescu (CPI; controlled), GSE120575 (scRNA; CI).

### 2e. Set aside (listed by databases but not ICI bulk cohorts)

- TIGER: adoptive cell therapy (GSE100797), DC vaccine (GSE106128), peptide vaccine (E-MTAB-6270), and GSE96619, which is a cell-line interferon study, not an ICI cohort.
- Cancer-Immu: Kwek prostate (GSE39688; protein array).
- Fumet 2018 NSCLC (GitHub `CRichard21/CD8PDL1_Nivolumab`: IHC plus limited RNA values).
- Roh 2017 (no RNA in the BHK inventory).
- WES-only cohorts: Samstein, Rizvi 2015/2018, Miao 2 (Allen 2018).
- ICBcomb, Bi, Krishna, Li and Shiao: scRNA or mouse.

---

## 3. Counts

- **NEW cohorts: 22 rows** (corrected 30 Oct: the oral-cavity set was already known as GSE179730; IOhub added Amato 2020 and Quintela-Fandino 2020). The two Limagne cohorts are one row; Cui is counted as open (processed only).
  - Open or processed-public: 11 (Jerby-Arnon, Chen 2016, AMADEUS, Vos SGC, Cui/PUCH, Snyder 2017, Nathanson, Limagne ×2, Schalper GBM, Quintela-Fandino).
  - Controlled: 10 (IMmotion151, IMvigor010, SU2C-MARK, Rosenbaum, Grasso, Roper, phs001427, Gettinger, Nguyen, Freeman).
  - Access unknown: 2 (INSPIRE, Amato RNA).
- **NEW patients with a known count:**
  - **1,037 in non-combination cohorts:**
    - Open: Jerby-Arnon 112, Cui 55, Snyder 25, Nathanson 24 = 216 (Chen 2016's pre-treatment count is unverified and not added).
    - Controlled: IMvigor010 728, Grasso 54, phs001427 20, Gettinger 19 = 821. Roper's 46 is mixed (an ICI-alone arm plus a PARP-combination arm) and is not split.
  - **943 in combination cohorts:** IMmotion151 823, Rosenbaum 64, Roper 46 (mixed), Nguyen 10; plus ≤6 for Quintela-Fandino.
  - Unknown n: SU2C-MARK, Freeman, AMADEUS (≤79), Vos (≤64), Limagne, Schalper, INSPIRE, Amato.
- **Public FASTQ among NEW:** only PRJNA940989, at **116.4 GB** (45 RNA-Seq runs, 44 public; ENA `fastq_bytes`).

## 4. Plain summary

1. **Coverage:** 17 databases checked. TIDE's site is BLOCKED (403). TIGER over https, Cancer-Immu, CAMOIP and the iAtlas portal were UNREACHABLE. IOhub's list was not found. ICBdb and an ICI "ImmuneDB" do not appear to exist. The most useful sources were ORCESTRA's API and BHK GitHub (PredictIO), TCCIA's and Cancer-Immu's supplements, iAtlas GitHub and cBioPortal, and TIGER's site code.
2. **Most databases recycle the same melanoma, urothelial and RCC cohorts we already have**, so the core public cohorts are covered.
3. **New and usable without access requests:**
   - AMADEUS: pan-tumour, nivolumab ± ipilimumab, baseline + on-treatment counts/TPM on GitHub.
   - Jerby-Arnon validation cohort: 112 melanoma patients, though possibly only a gene subset is public.
   - Cui/PUCH (55) and Nathanson (24), as ORCESTRA processed objects.
   - Snyder 2017 urothelial: kallisto counts on Zenodo.
   - One public-FASTQ set: the salivary gland trial (116 GB). The neoadjuvant oral-cavity trial (174 GB) turned out to be GSE179730, already in the expanded note.
   - Chen 2016 NanoString (supplement).
4. **The largest NEW cohorts are controlled:** IMvigor010 (728, adjuvant, no RECIST), IMmotion151 (823, combination), SU2C-MARK NSCLC (size unverified), Grasso melanoma (54).
5. **Next checks:** AMADEUS baseline-RNA n; whether the Jerby-Arnon public matrix is genome-wide; the Limagne cohorts' regimens; INSPIRE access.

---

## 5. Harmonized collections: verified facts (for `specs/amendments/2026-10-30-source-strategy/DECISION_PENDING.md`)

This section checks each claim against a primary source (Zenodo API, GitHub API/raw files, paper full text in PMC, official APIs). **No data object was downloaded or opened.** The TIGER routes were checked with HTTP HEAD only. IMvigor210 objects were identified by name only and never touched.

### 5.1 ORCESTRA / PredictIO (BHK lab)

| Claim | Finding | Source (quote) |
| --- | --- | --- |
| Records with R objects exist | **TRUE.** 21 ICB data objects, each an `.rds` on Zenodo, listed by the public API | `https://www.orcestra.ca/api/clinical_icb/available` (JSON lists `ICB_<study>` with a Zenodo `doi` and `downloadLink`) |
| Object class is `MultiAssayExperiment` | **TRUE** (per the build code; the objects were not opened). "ClinicalICB" is not the class name in the code | `BHKLAB-DataProcessing/ICB_Common/code/get_MultiAssayExp.R`: "return(MultiAssayExperiment(experiments=se_list, colData=coldata))" |
| Open licence | **TRUE.** Zenodo `license`: cc-zero for 18 objects; cc-by-4.0 for Jung, Kim, Hugo; all `open` | Zenodo records API, e.g. `https://zenodo.org/api/records/7332236` |
| RECIST, irRECIST, PFS, OS mapped | **PARTLY.** Per-patient `recist`, `response`, PFS/OS columns exist in the BHK study inventory (aggregate check only). irRECIST: no field seen (**UNVERIFIED**). The binary `response` is **derived**: CR/PR → R, PD → NR, and **SD is reassigned by 6-month PFS** | `ICB_Common/code/Get_Response.R`: "if( recist %in% "SD" ) … if( t.pfs <= 6 & pfs %in% 1 ) … "NR"" |
| Processing documented and uniform | **NOT UNIFORM; partly documented.** Two routes: (a) public-FASTQ cohorts (Gide, Riaz, Hugo…): kallisto output → tximport with **GENCODE v40**, stored as log2(TPM + 0.001) and log2(counts + 1). The kallisto version and index are **not stated** in the ICB repositories, and the kallisto runs are supplied as pre-made zips. (b) Controlled or supplement cohorts (Liu, Braun, Jerby-Arnon…): the **authors' own matrices** read from journal supplements | `ICB_Common/code/process_kallisto_output.R`: "expr_list[['expr_gene_tpm']] <- log2(expr_gene$abundance + 0.001)"; `ICB_Gide-snakemake/Snakefile`: "annotation/Gencode.v40.annotation.RData"; `ICB_Liu-snakemake/scripts/format_downloaded_data.R` reads "41591_2019_654_MOESM3_ESM.txt" (the author TPM supplement) |
| Patient selection | Documented per study in code. For example, the Riaz script keeps pre-treatment samples only and drops five named patients | `ICB_Riaz-snakemake/scripts/format_downloaded_data.R` (`str_detect(... 'Pre_')`, explicit exclusion list) |
| More studies than released | The curation table lists about 55 studies (Ravi, Thibaudin, Wolf, ABACUS, Fehrenbacher/POPLAR, Rittmeyer/OAK, Hartwig, Foy, Markovits, Weber, Wolchok, Goswami…). Only 21 are released on the API | `ICB_Common/data/DATASET_LOAD_INFO.csv` |
| IMvigor210 included | **Yes** (`ICB_Mariathasan`). It inherits UNTOUCHED_FINAL_TEST: do not download | API list |
| Precomputed scores / AUCs shipped | Not seen in the build code (expression, clinical, SNV/CNA assays). The PredictIO web app holds signature results separately. Object contents are **UNVERIFIED** because they were not opened | `get_MultiAssayExp.R`; `bhklab/PredictIO-webapp` |
| Patient-ID traceability | Good: author patient IDs from supplement tables, and runs mapped to patients through sample titles | Riaz and Gide scripts |

**Verdict: CROSS_CHECK_ONLY overall.**
- The data are open and per-cohort code exists, but there is no single documented pipeline:
  - kallisto version and index are undocumented;
  - the controlled cohorts are the authors' matrices;
  - SD is reclassified in the binary label.
- **Per cohort it can be USABLE_AS_SOURCE** for gap cohorts we cannot get otherwise (Cui/PUCH, Nathanson, Jerby-Arnon, Snyder 2017, Limagne), each through V3 like any other source.

### 5.2 IOhub

| Claim | Finding | Source (quote) |
| --- | --- | --- |
| GitHub repo `hansolo-bioinfo/IOhub` | **Repo exists**: "immune checkpoint inhibitor database that integrate pre vs post scRNAseq and bulk-RNAseq" (created 2023-08-12, last push 2023-09-02) | GitHub API `repos/hansolo-bioinfo/IOhub` |
| `data/` with processed `.rds` | **FALSE.** The repository has 10 files: `app.R`, `server.R`, `ui.R`, images and README. There is no data folder. The data live only behind the Shiny app (`hansolo-bioinfo.shinyapps.io/IOhub`) | GitHub tree API |
| Licence | **None** (`license: null`) | GitHub API |
| Size | README: "1,409 ICB-treated tumor samples from 21 bulk-RNAseq datasets"; bioRxiv 2024 says 36 bulk | README; PMID 39713380 |
| Processing | TPM, then **limma batch correction across cohorts and cancer type**, with signature scores computed on the corrected data | `ui.R`: "We then used limma to remove batch effects and covariates of cancer type. TIDE score, IMPRES score, … were calculated on corrected samples." |
| Response | Clinical benefit / CR / PR / MR = R; PD / **SD** = NR | `ui.R`: "'non-Response/NR' if they showed no clinical benefit, progressive disease (PD), stable disease (SD)…" |
| IMvigor210 included | Yes (Mariathasan is reference 10) | `ui.R` |
| Precomputed scores | Yes (TIDE, IMPRES, IFN-γ, GEP, TLS, deconvolution) | `ui.R` |

**Verdict: NOT_USABLE.** There are no downloadable data and no licence. Expression is batch-corrected across cohorts, which breaks our per-study rule, and scores are precomputed.

### 5.3 CPI1000+ (Litchfield 2021, *Cell*)

| Claim | Finding | Source (quote) |
| --- | --- | --- |
| Uniform reprocessing | **TRUE for analysis**: "reprocessed these data through a uniform bioinformatics pipeline"; RNA: "aligned to the hg19 genome using STAR … normalized using DESeq2 variance stabilizing transformation … TPM values calculated using RSEM with default parameters". **STAR and RSEM versions are not given; the annotation release is not given.** RNA available for 564 patients | PMC7933824, STAR Methods |
| Processed matrices public | **FALSE.** "Data and code availability: The code used for this manuscript is available at: https://github.com/kevlitchfield1/CPI1000_paper". That repository holds figure scripts and figure-level data tables only. No expression matrix, no licence | GitHub tree API |
| Raw data | The original studies' raw data, many of them controlled | Paper |
| IMvigor210 included | Yes (Mariathasan listed among the 12 cohorts) | Paper text |

**Verdict: NOT_USABLE as a data source** (no released expression). Its response harmonisation and cohort list are useful for CROSS_CHECK only.

### 5.4 CRI iAtlas

| Claim | Finding | Source (quote) |
| --- | --- | --- |
| Synapse `syn10337516` | **TRUE**: entity `syn10337516` is the Project "CRI iAtlas". The ICI expression file `syn25981839` ("ici_genes_to_samples.feather") is publicly viewable but `canDownload: false` for anonymous users. No access requirements are listed | Synapse REST `entity/syn10337516`, `entity/syn25981839/permissions` |
| API | **TRUE, open, no login**: GraphQL at `https://api.cri-iatlas.org/api`. `dataSets(dataSetType:["ici"])` returns **23 ICI datasets**. The `genes` query exposes RNA-seq expression per sample. Client: `CRI-iAtlas/iatlasGraphQLClient` (MIT) | live API query (dataset names only) |
| Notebooks | **TRUE**: `CRI-iAtlas/iatlas-notebooks` | GitHub |
| Processing | **UNDOCUMENTED** (see `BATCH2_PROCESSING_EVIDENCE_20261030.md`). The notebooks describe "quantile normalized gene expression"; the cBioPortal files are labelled TPM or log2 UQ counts | notebooks; cBioPortal meta |
| IMvigor210 included | Yes (`IMVigor210` in the API; `blca_iatlas_imvigor210_2017` in cBioPortal) | API |
| Precomputed scores | **Yes**: immune features and predictor scores (the API `features`; cBioPortal `data_gene_signatures`, TIDE fields) | API schema; cBioPortal meta |
| Patient-ID traceability | Partial. cBioPortal `PATIENT_ID` matched the Liu author table by exact ID (122/122, earlier check); other cohorts are UNVERIFIED | `liu2019_SOURCES.md` |

**Verdict: CROSS_CHECK_ONLY.** Access is open, but processing is undocumented and scores ship with the data. This is already our status for Liu, Gide and IMvigor210.

### 5.5 TIDE and TIGER

| Claim | Finding | Source (quote) |
| --- | --- | --- |
| TIDE per-cohort downloads | **UNVERIFIED: BLOCKED.** `tide.dfci.harvard.edu` redirects to `cide.ccr.cancer.gov/tide`, which returns HTTP 403 | HTTP check |
| TIDE processing | Per data set: "standardized the transcriptome data across patients by quantile-normalization, and further normalized the expression values of each gene by subtracting the average"; TIDE scores are the product | PMC6487502 |
| TIGER per-study downloads | **TRUE.** The site code builds `/tiger/Download/immunotherapy/{expression,clinical}/{Rds,tsv}/<DatasetID>.Response.<ext>`. A HEAD request on one non-IMvigor dataset returned 200 (expression 17.6 MB, clinical 4 kB); nothing was downloaded | site JS; HTTP HEAD |
| TIGER processing | Raw RNA-seq where available: "Cutadapt … aligned … using STAR … featureCounts … normalized to … FPKM"; otherwise "Preprocessed data were used if raw data were not available". **No versions or annotation given** | PMC10626175 |
| TIGER IMvigor210 | Not in its 25 response datasets (site code) | site JS |
| TIGER scores | The site computes signature AUC tables across datasets (Fig. 2A); the download files appear to be expression + clinical only (**UNVERIFIED**, not opened) | paper |
| TIGER licence | Not stated (**UNVERIFIED**) | — |

**Verdicts:**
- **TIDE: NOT_USABLE.** The site is blocked, and its data are quantile-normalized and mean-centred by design.
- **TIGER: CROSS_CHECK_ONLY.** Downloads work, but FPKM comes from an unversioned STAR/featureCounts run (mixed with preprocessed author data), there is no licence, and all of its ICI cohorts are already in our set.

### 5.6 Coverage claim: "ORCESTRA + IOhub cover more than 70% of public ICB cohorts"

**Denominator: 86** distinct ICI cohorts with public patient-level bulk expression (raw or processed) and an outcome, counted from our two files plus this harvest:
- pipeline + intake: 26;
- expanded-note GEO candidates: 34;
- section 4a of the expanded note: 5;
- known candidates: 9;
- NEW open: 12.

Controlled-only cohorts are excluded.

| Collection | Cohorts in the denominator it covers | Share |
| --- | ---: | ---: |
| ORCESTRA (20 released objects with RNA) | 20 | 23% |
| IOhub (21 bulk) | 21 | 24% |
| **ORCESTRA ∪ IOhub** | **29** | **34%** (corrected 30 Oct: ORCESTRA's Hwang is GSE136961, not GSE126044) |
| ORCESTRA alone, excluding IMvigor210 (locked) | 19 | 22% |

The union covers mainly the well-known melanoma, kidney and urothelial cohorts. None of the 34 newer GEO cohorts in the expanded note is in either collection.

**Verdict on the claim: FALSE.** It is about one third, not more than 70%, and IOhub is not downloadable at all.

### 5.7 One-line verdicts

| Collection | Verdict | Main reason |
| --- | --- | --- |
| ORCESTRA / PredictIO | **CROSS_CHECK_ONLY** (USABLE_AS_SOURCE per gap cohort, through V3) | Open (CC0/CC-BY) MultiAssayExperiment objects, but two processing routes (kallisto + GENCODE v40 with undocumented version and index, versus author matrices) and a derived SD rule |
| IOhub | **NOT_USABLE** | No data in GitHub, no licence, cross-cohort batch correction, precomputed scores |
| CPI1000+ | **NOT_USABLE** | Uniform pipeline described, but no expression released |
| CRI iAtlas | **CROSS_CHECK_ONLY** | Open API, undocumented processing, ships scores |
| TIDE | **NOT_USABLE** | Site BLOCKED; quantile-normalized and centred data |
| TIGER | **CROSS_CHECK_ONLY** | Working downloads; unversioned FPKM pipeline; no licence; no new cohorts |
