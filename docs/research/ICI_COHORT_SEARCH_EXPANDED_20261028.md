# Expanded ICI cohort search for Paper A and Paper B (2026-10-28)

This note builds on `A_ICI_LANDSCAPE_MCP_20261028.md`, which sits in the same folder. That note's cohort tables still hold. This note adds:

- the ICBatlas accession resolution;
- the 16 Paper B handoff candidates;
- the prostate treated cohorts;
- new hits in other cancers.

It covers metadata only. No expression matrix was downloaded, no pipeline code was changed, and no biological analysis was run.

## How this was made

- **Guideline:** ICBatlas (Yang et al., Cancer Immunol Res 2022;10:1398).
  - Response is RECIST v1.1, with R = CR/PR and NR = SD/PD.
  - Each dataset is analysed on its own, and matrices are never merged.
  - Patients with no outcome are dropped.
- **Search:**
  - geo MCP `search_geo_series`: 4 queries (HNSCC, gastric/esophageal, mixed rare cancers, the MSS CRC trial).
  - The same GEO backend through NCBI E-utilities (`esearch`/`esummary`, db=gds): 8 queries, one per cancer group (HNSCC, gastric/esophageal, TNBC, mesothelioma/GBM, RCC, CRC/MSI, prostate, urothelial). This returned about 580 series. A keyword filter cut it to about 150, and about 40 of those were chosen by hand.
- **Verification:**
  - Every row was checked against GEO `acc.cgi` (`targ=self` and `targ=gsm`, `form=text`), with requests at least 1 s apart.
  - Sample counts and response fields were counted from the GSM characteristics.
  - SRP/ERP numbers were resolved through the ENA portal API (`result=study` and `result=read_run`, using the `fastq_ftp` field) and through GEO `esearch`.
  - EGA studies were checked through `metadata.ega-archive.org`.
  - PubMed titles were checked with E-utilities `esummary`.
- Anything not checked against a primary record is marked **UNVERIFIED**.

### Column key

- **Tag:**
  - **A** = pre-treatment tumour plus a RECIST-like response (needed for Paper A's signature-robustness and endpoint-sensitivity work).
  - **B** = a treated prostate cohort, or paired pre/on-treatment samples useful to Paper B (why the immune and antigen-presentation program is low, and whether treatment moves it).
  - **A+B** = both.
- **Ready** (readiness):
  - **R1** = per-sample response is in GEO and a processed matrix is public.
  - **R2** = the matrix is public, but labels are only in the paper or supplement.
  - **R3** = raw reads only, or controlled access.
  - **X** = set aside (reason given).
- **Drug class:**
  - PD-1, PD-L1 and CTLA-4 are listed separately.
  - "+" means a combination.
  - "chemo", "TKI", "RT" and "other" mark non-ICB partner drugs.
- **Pre n** = pre-treatment tumour samples. **Pairs** = patients with both a pre-treatment and an on- or post-treatment tumour sample.
- **ICBatlas** = yes if the accession is in the ICBatlas roster.
- **Panel** = a targeted panel, not the whole transcriptome (NanoString, Oncomine). Some signature genes may be missing.

## 0. Already in the pipeline or already decided (not re-qualified)

| Accession | Status | ICBatlas |
|---|---|---|
| [GSE91061](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061) (= SRP094781) | Admitted (Riaz) | yes |
| [GSE78220](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE78220) (= SRP070710) | In the pipeline | yes |
| [GSE176307](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176307) | In the pipeline | yes |
| [GSE248014](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE248014) | In the pipeline (also in the Paper B list) | no |
| [GSE168204](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE168204) | In the pipeline | no |
| [GSE115821](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE115821) (= SRP150548) | Parked | yes |
| [GSE126044](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE126044) (= SRP183455) | Parked | yes |

**Exposure note:** the Paper B status note says that B's scratch runs computed panel AUCs on GSE93157 and GSE122220 (plus GSE78220 and GSE91061). Both of those appear below as A candidates. Log them as exposed before giving either one a test role.

## 1. ICBatlas accessions resolved

| ICBatlas accession | Resolves to | What it is (from the ENA/GEO title) | Processed matrix public? | Raw reads |
|---|---|---|---|---|
| ERP105482 | ENA PRJEB23709; no GEO series | Melanoma, checkpoint blockade (probably Gide 2019, UNVERIFIED) | **No GEO matrix**. Processed data elsewhere: UNVERIFIED | 91 RNA-seq runs, FASTQ public in ENA |
| ERP107734 | ENA PRJEB25780; no GEO series | Gastric cancer, pembrolizumab (Samsung; probably Kim 2018, UNVERIFIED) | **No GEO matrix** | 78 RNA-seq runs, FASTQ public in ENA |
| SRP011540 | PRJNA82747; no GEO series | "Melanoma Genome Sequencing Project" (Broad; probably the Van Allen 2015 ipilimumab cohort, UNVERIFIED) | **No** | 164 RNA-seq runs listed, no public FASTQ → **controlled** (dbGaP; study number UNVERIFIED) |
| SRP070710 | [GSE78220](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE78220) | Hugo 2016 melanoma | Yes | In the pipeline |
| SRP094781 | [GSE91061](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061) | Riaz 2017 | Yes | Admitted |
| SRP128156 | PRJNA420786; no GEO series | RCC, checkpoint therapy (Broad; probably Miao 2018, UNVERIFIED) | **No** | 154 RNA-seq runs listed, no public FASTQ → **controlled** |
| SRP150548 | [GSE115821](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE115821) | Melanoma (Auslander 2018) | Yes | Parked |
| SRP155030 | PRJNA482620; no GEO series | GBM, anti-PD-1, longitudinal (Columbia; probably Zhao 2019, UNVERIFIED) | **No GEO matrix** | 34 RNA-seq runs, FASTQ public in ENA |
| SRP183455 | [GSE126044](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE126044) | NSCLC anti-PD-1 | Yes | Parked |
| SRP217040 | [GSE135222](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135222) | NSCLC, 27 patients, PD-1/PD-L1 | Yes, RSEM TPM | Public SRA |
| SRP230414 | PRJNA578193; no GEO series | Melanoma, anti-PD-1 (UCLA; probably Liu 2019, UNVERIFIED) | **No GEO matrix**. A paper-supplement TPM table is UNVERIFIED | 60 RNA-seq runs, FASTQ public in ENA |
| SRP250849 | [GSE145996](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE145996) | Melanoma, anti-PD-1 | Yes, FPKM, but **only 14 of the 52 patients** | Public SRA |
| SRP302761 | [GSE165278](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE165278) | Melanoma, ipilimumab, pre and post | Yes, TPM (xlsx) | Public SRA |

The GEO-native ICBatlas series (GSE111636, GSE122220, GSE136961, GSE140901, GSE67501, GSE93157, GSE99070) are qualified in the main table below.

## 2. Candidate table (sorted by tag, then readiness)

| Tag | Ready | Accession | Cancer | Drug class | Pre n | Pairs | Response: where it lives and how it is defined | Expression file and units | Access | ICBatlas |
|---|---|---|---|---|---|---|---|---|---|---|
| A+B | R1 | [GSE224450](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE224450) · PMID [37188668](https://pubmed.ncbi.nlm.nih.gov/37188668/) | EBV+ nasopharyngeal, recurrent or metastatic | PD-1+CTLA-4 (nivolumab + ipilimumab) | 22 | 19 | GEO `best overall response`, RECIST. Pre-treatment: PR 9 / SD 6 / PD 7 | NanoString IO360, RUVSeq-normalized xlsx (**panel**) | Public | no |
| A+B | R1 | [GSE210287](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE210287) · PMID 36385142 | HNSCC, HPV-unrelated, neoadjuvant | PD-L1+RT (durvalumab + SBRT) | 12 | 10 post | GEO `response`, R/NR, **author binary** (probably pathological, UNVERIFIED). Pre-treatment: R 7 / NR 5 | Raw counts + CPM (xlsx) | Public | no |
| A+B | R1 | [GSE211645](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE211645) | Melanoma, advanced (NIBIT-M4) | CTLA-4+other (ipilimumab + guadecitabine) | 14 | W4 and W12 for most | GEO `response to therapy`, BOR. Pre-treatment: CR 2 / PR 2 / SD 2 / PD 8. Sample titles count **SD as responder** | Custom NanoString (**panel**), RAW.tar | Public | no |
| A+B | R1 | [GSE289743](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE289743) · PMID [40836096](https://pubmed.ncbi.nlm.nih.gov/40836096/) | Cutaneous SCC, neoadjuvant (NCT04154943; drug probably cemiplimab, UNVERIFIED) | PD-1 | 17 | Mostly post (66 post samples) | GEO `response`, responders / non-responders, author binary (probably pathological, UNVERIFIED). Pre-treatment: R 12 / NR 5 | Raw counts CSV (FFPE) | Public | no |
| A+B | R1 | [GSE202361](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE202361) | Sarcoma (DDLPS/UPS), neoadjuvant | ICB, regimen UNVERIFIED | 23 | Yes (64 total) | GEO `outcome`, RECIST. Baseline: PR 1 / SD 14 / PD 8 | TPM + raw counts | Public | no |
| A+B | R1 | [GSE289583](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE289583) · PMID 41719220 | MSS colorectal, metastatic | PD-1+CTLA-4+TKI (regorafenib) | 8 | 6 (week 4) | GEO `best response`. Baseline: PR 1 / SD 5 / PD 2 | Raw counts | Public. Tumour subseries of [GSE289582](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE289582), which is **blood T cells** (set aside) | no |
| A | R1 | [GSE93157](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE93157) · PMID 28487385 | NSCLC, HNSCC, melanoma | PD-1 (nivolumab or pembrolizumab) | 65 (33 baseline biopsy + 32 archival) | – | GEO `best.resp`, RECIST: CR 3 / PR 17 / SD 16 / PD 29, plus PFS | NanoString 730 (**panel**) | Public | **yes** · B-exposed |
| A | R1 | [GSE140901](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE140901) · PMID 34414122 | HCC | ICI (agent not in GEO; UNVERIFIED) | 24 archival | – | GEO `best_response`: PR 6 / SD 10 / PD 8, plus `clinical_benefit_response` (Y 13 / N 11), PFS and OS | NanoString log2 CPM (**panel**) | Public | **yes** |
| A | R1 | [GSE241876](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE241876) · PMID 37882661 | TNBC, metastatic | PD-1+chemo (pembrolizumab + carboplatin + nab-paclitaxel) | 19 (pre-treatment status UNVERIFIED) | – | GEO `overall response`, RECIST: CR 2 / PR 9 / SD 4 / PD 4 | Raw counts + DESeq2-normalized | Public | no |
| A | R1 | [GSE235919](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE235919) | RAS-mutant CRC | PD-L1+CTLA-4+chemo | 34 | – | GEO RECIST: CR 6 / PR 17 / SD 11, **no PD** | TPM | Public | no |
| A | R1 | [GSE345048](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE345048) | Inflammatory breast cancer | PD-L1+chemo or other | 16 | some | GEO best response. Baseline: PR 1 / SD 5 / PD 8 / unevaluable 2 | TPM, FPKM, counts | Public; raw controlled | no |
| A | R1 | [GSE235863](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE235863) | HBV+ HCC | PD-1+TKI (lenvatinib) | 15 bulk | – | GEO: CR 5 / PR 6 / SD 2 / PD 2 | Counts + TPM | Public; raw in GSA | no |
| A | R1 | [GSE122220](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE122220) | Melanoma | PD-1 (8), PD-1+CTLA-4 (2) | 10 | – | GEO, RECIST: CR 2 / PR 2 / SD 1 / PD 5 | Illumina array, normalized + non-normalized | Public | **yes** · B-exposed |
| A | R1 | [GSE67501](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE67501) · PMID 27491898 | RCC | PD-1 (nivolumab) | 11 archival (taken 2–81 months before therapy) | – | GEO, RECIST: CR 2 / PR 2 / SD 2 / NR 5 | Illumina array, non-normalized | Public | **yes** |
| A | R1 | [GSE111636](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE111636) | Urothelial | PD-1 (pembrolizumab) | 11 (timing UNVERIFIED) | – | GEO, author binary: responder 6 / progressor 5 | Affymetrix HTA 2.0, RMA | Public | **yes** |
| A | R1 | [GSE248514](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE248514) · PMID 39731918 | Mesothelioma (DREAM trial) | PD-L1+chemo (durvalumab) | 46 archival | – | GEO `progression-free at 6 months`: yes 24 / no 22. **Not RECIST**; suits endpoint sensitivity | NanoString raw + normalized (**panel**) | Public | no |
| A | R1 | [GSE190266](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE190266) | NSCLC | PD-1 | 70 | – | GEO 6-month PFS event (not ORR) | TPM | Public | no |
| A | R1 | [GSE136961](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE136961) · PMID 31959763 | NSCLC | PD-1 | 21 | – | GEO: PFS days + recurrence only. The DCB label is in the paper (UNVERIFIED) | Oncomine Immune Response, about 400 genes (**panel**), TPM + counts | Public | **yes** · already in PROPOSED_RECORDS |
| A | R2 | [GSE343570](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE343570) | NSCLC, 1st line | PD-1 ± HDACi (vorinostat) | 32 | 34 on-treatment (pairing UNVERIFIED) | Not in GEO; paper not yet linked | RSEM counts | Public | no |
| A | R2 | [GSE285963](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE285963) | HCC | PD-L1+VEGF (atezolizumab + bevacizumab) | 73 | – | Not in GEO; PMID 41362708 | Read counts | Public | no |
| A+B | R2 | [GSE302495](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE302495) | HCC, potentially resectable | PD-1+CTLA-4 | 38 | Up to 32 post | Not in GEO; PMID 40972843 | Read counts | Public | no |
| A+B | R2 | [GSE281729](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE281729) | HNSCC, neoadjuvant | PD-1 ± IDO inhibitor | 36 | 31 on-treatment | Not in GEO; pathological response (PMID 39585339) | logTPM | Public | no |
| A+B | R2 | [GSE213065](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE213065) · PMID [38429415](https://pubmed.ncbi.nlm.nih.gov/38429415/) | Soft-tissue sarcoma (5 subtypes) | PD-1+CTLA-4 ± chemo ± cryotherapy for 64 of 87 samples; the rest chemo only | 59 T1 samples (patient-level split by drug UNVERIFIED) | 26 T2 samples | Not in GEO (paper) | Salmon TPM, protein-coding genes only | Public | no |
| A+B | R2 | [GSE225066](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE225066) · PMID 40298406 | Bladder (urothelial 22, squamous 4), neoadjuvant | PD-L1+PARPi (durvalumab + olaparib) | 16 TURBT | 10 cystectomy | Not in GEO; the paper compares responders (definition UNVERIFIED) | Normalized counts only | Public | no |
| A+B | R2 | [GSE222932](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222932) · PMID 36928921 | Urothelial, after prior ICI | PD-L1+DNMTi (atezolizumab + guadecitabine) | 33 | 17 post | Not in GEO. Subseries of GSE222934 (already listed) | RAW.tar (type UNVERIFIED) | Public | no |
| A+B | R2 | [GSE179730](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE179730) · PMID 34755131 | Oral-cavity SCC, neoadjuvant | PD-1 | 11 | 11 | Not in GEO; pathological response in paper | CPM only | Public | no |
| A+B | R2 | [GSE306800](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE306800) · PMID 40932382 | HPV+ HNSCC, neoadjuvant | PD-L1+metformin | 9 | 9 | Not in GEO | Processed file (units UNVERIFIED) | Public | no |
| A+B | R2 | [GSE319641](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE319641) | TNBC (NeoTRIP) | PD-L1+chemo vs chemo | 241 | 160 at D1C2 | Not in GEO; **pCR** | **TPM already ComBat-corrected** (violates the no-merge rule) | Public | no |
| A+B | R2 | [GSE245372](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE245372) | ccRCC, non-metastatic | PD-1 neoadjuvant | 13 | 15 post | Not in GEO | Expected counts | Public; raw withheld | no |
| A | R2 | [GSE212549](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE212549) (SuperSeries [GSE212551](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE212551)) · PMID 38290766 | HNSCC, recurrent or metastatic, platinum-refractory (NIVACTOR) | PD-1 (nivolumab) | 80 (+20 test set; timing UNVERIFIED) | – | Not in GEO for the 80. The 20-sample test set has only long- vs short-term survivor. RECIST in the paper (UNVERIFIED) | Affymetrix GPL23126 CEL | Public | no |
| A | R2 | [GSE293952](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE293952) | ccRCC, metastatic | PD-1/PD-L1/CTLA-4 + TKI (mixed: 41 lenvatinib + pembrolizumab) | 61 | – | Not in GEO; PMID 42242232 | FPKM, batch-corrected FPKM, raw | Public | no |
| A | R2 | [GSE253564](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE253564) | NSCLC | PD-L1 ± CTLA-4 + RT (2 arms) | 32 | – | Not in GEO; PMID 38401548 | **FPKM only** | Public | no |
| A | R2 | [GSE135222](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135222) · PMID 31537801 | NSCLC | PD-1/PD-L1 | 27 | – | Not in GEO (PFS in the paper; UNVERIFIED) | RSEM TPM | Public | **yes** |
| A | R2 | [GSE145996](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE145996) · PMID 32708981 | Melanoma | PD-1 | 14 in GEO (of 52) | – | Not per sample. The design text gives 21 CR/PR vs 31 SD/PD for the full cohort | **FPKM only** | Public | **yes** |
| A | R2 | [GSE226976](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE226976) · PMID 37188783 | Recurrent GBM | PD-1 + oncolytic adenovirus | 48 (timing UNVERIFIED) | – | Not in GEO | Array RAW.tar | Public | no |
| A | R2 | [GSE311339](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE311339) | RCC, oligometastatic | PD-1+RT (SABR) | 30 (timing UNVERIFIED) | – | Not in GEO | NanoString (**panel**) | Public | no |
| A | R2 | [GSE274983](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE274983) · PMID 39395787 | Pleural mesothelioma | PD-1 (13), PD-1+CTLA-4 (4), pembrolizumab (1) | 18 | – | Not in GEO (serum SMRP groups only) | RAW.tar (type UNVERIFIED) | Public | no |
| A | R2 | [GSE158403](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE158403), [GSE190265](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE190265) | See the earlier note | | | | | | | no |
| A | R3 | PRJEB23709 (ERP105482) | Melanoma | PD-1 ± CTLA-4 (UNVERIFIED) | UNVERIFIED | UNVERIFIED | Paper only | FASTQ only | Public raw | **yes** |
| A | R3 | PRJEB25780 (ERP107734) | Gastric | PD-1 (pembrolizumab) | UNVERIFIED | – | Paper only | FASTQ only | Public raw | **yes** |
| A | R3 | PRJNA578193 (SRP230414) | Melanoma | PD-1 | UNVERIFIED | – | Paper only | FASTQ (a supplement TPM table is UNVERIFIED) | Public raw | **yes** |
| A+B | R3 | PRJNA482620 (SRP155030) | GBM | PD-1 | UNVERIFIED | Longitudinal (per the study title) | Paper only | FASTQ only | Public raw | **yes** |
| A | R3 | PRJNA82747 (SRP011540), PRJNA420786 (SRP128156) | Melanoma; RCC | CTLA-4; PD-1 (UNVERIFIED) | UNVERIFIED | – | Paper only | – | **Controlled** | **yes** |
| B | R1 | [GSE314805](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE314805) · PMID [41378786](https://pubmed.ncbi.nlm.nih.gov/41378786/) | mCRPC, bone biopsies (NCT02499835) | PD-1 + DNA vaccine (pTVG-HP) | 12 | **12 pairs** | GEO `clinical psa response` (any PSA decline): yes 4 / no 8 per timepoint. Also irAE status | NanoString via nSolver, RAW.tar (**panel**) | Public | no |
| B | R1 | [GSE273798](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE273798) · PMID 39536751 | Small-cell/neuroendocrine bladder **and** prostate (prostate n UNVERIFIED) | PD-1+chemo (cisplatin) | 10 | – | GEO `group`: responder 6 / "responder progressed" 4. **No non-responder group** | CPM from STAR counts (Tempus xR) | Public | no |
| B | R2 | [GSE159237](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE159237) · PMID 33771853 | Mixed: **prostate 12 samples**, plus pancreatic, melanoma, HNSCC | CTLA-4 + hypoxia prodrug (evofosfamide) | Prostate 7 | Prostate 5 pairs | Not in GEO | StringTie **FPKM only** | Public; SRA SRP286769 | no |
| B | R2 | [GSE288248](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE288248) · PMID 41173002 | Prostate cancer (poly-ICLC trial, 4 cohorts) | Intratumoral poly-ICLC (**not a checkpoint drug**; ICB in any cohort UNVERIFIED) | 12 | **12 pairs** | Not in GEO | Affymetrix HuEx 1.0, SCAN-normalized | Public | no |
| B | R3 | EGAS00001004050 | mCRPC, 30 patients | CTLA-4 (ipilimumab) | UNVERIFIED | UNVERIFIED | EGA description: favorable vs unfavorable outcome groups | Expression data type UNVERIFIED | **Controlled (EGA)** | no |
| B | R2 | [GSE227666](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE227666) | Ovarian | Chemo ± PD-1 (pembrolizumab) | 32 (NACT+P arm) + 21 (NACT arm) | 32 + 24 post | Not in GEO | Counts | Public | no |
| B | R2 | [GSE271757](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE271757) | Ovarian | PD-1+chemo | 42 | 55 post | Not in GEO | RAW.tar | Public | no |

### Set aside

| Accession | Reason |
|---|---|
| [GSE289582](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE289582) | Sorted blood CD4/CD8 T cells. Use the tumour series GSE289583 instead |
| [GSE332987](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE332987) | Spatial GeoMx regions, melanoma, pepinemab + ICB. Not whole-tumour bulk |
| [GSE266919](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE266919) | TNBC, PD-L1+chemo. Pre-treatment samples are **sorted immune cells** (R 12 / NR 17), and total-cell samples are post-treatment only |
| [GSE189926](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE189926) | Gastric, PD-1 + disulfiram. Sorted CD45+ cells, not tumour bulk (it does have RECIST: PR 4 / SD 11 / PD 3 / NE 4) |
| [GSE264695](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE264695) | GBM. Resected **after** neoadjuvant pembrolizumab, so no pre-treatment sample |
| [GSE99070](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE99070) (ICBatlas) | Mesothelioma. 10 ICI-treated samples with no response label in GEO; mainly a CyTOF/proteomics study |
| [GSE212217](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE212217), [GSE316301](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE316301), [GSE287371](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE287371) | Blood or PBMC, single-cell |
| [GSE286827](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286827), [GSE256326](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE256326) | Mainly single-cell. GSE256326 has only 6 bulk patients (renal medullary carcinoma, PD-1+CTLA-4) |
| [GSE234136](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE234136), [GSE270047](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE270047), [GSE307471](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE307471) | Ex-vivo culture, assay-precision runs, or cell lines; not treated patients |
| [GSE333537](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE333537) | HNSCC, oncolytic virus + durvalumab. Day 0 / 8 / 28 samples with no labels; the virus confounds the ICB effect |
| [GSE154538](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE154538) | GI cancers, PD-1. Only 8 patients and no response field |
| [GSE123728](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE123728) | Melanoma, single-dose neoadjuvant PD-1. GEO has recurrence only (not RECIST), and timing is UNVERIFIED |
| [GSE298296](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE298296) | MIBC, PURE-01 neoadjuvant pembrolizumab, 102 arrays. pCR is not in GEO. **Could be promoted to A R2** if the pCR table is obtainable (UNVERIFIED) |
| [GSE289185](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE289185) | ESCC, neoadjuvant RT + immunotherapy, 29 samples. FPKM, with no timepoint or response field |
| [GSE193898](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE193898), [GSE229394](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE229394) | Prostate, but **not ICB-treated** (docetaxel-based chemohormonal therapy; DynAMo). B context only |

## 3. Plain-language takeaways

- The **ready Paper A set** (R1 and RECIST-like) grew with six new cohorts: GSE224450, GSE241876, GSE140901, GSE93157, GSE67501 and GSE122220. Three of these (GSE93157, GSE140901, GSE224450) are **panel** data, and GSE122220 and GSE93157 are already **exposed** by B's scratch runs.
- Most of the ICBatlas roster that is not in GEO is **raw reads only** (Gide, Kim gastric, Zhao GBM, Liu) or **controlled** (Van Allen, Miao). Using it would mean our own alignment, so it is R3.
- The **Paper B prostate side is thin**. Only GSE314805 (12 pairs, PSA response, panel) and GSE159237 (5 prostate pairs, FPKM) are public, ICB-treated and paired. EGAS00001004050 is controlled.
- **Endpoints differ.** RECIST: GSE224450, GSE241876, GSE140901, GSE93157, GSE122220, GSE67501. Author binary: GSE210287, GSE289743, GSE111636, GSE273798. PFS6: GSE248514, GSE190266. PSA: GSE314805. pCR: GSE319641. Keep these in separate endpoint arms.
- **Do not merge.** GSE319641 ships ComBat-corrected TPM, which conflicts with ICBatlas's analyse-separately rule.

## 4. Roster cross-check (117 records)

The source is `outputs/01a0f1c4-…/study-inventory-20261012/inventory-input.json`. Where the roster disagreed with a primary record (GEO, ENA, EGA, dbGaP, cBioPortal API, or a GitHub README), the primary record was trusted.

**Count: 30 covered / 10 newly qualified / 13 unavailable / 64 out of scope = 117.**

### 4a. Newly qualified (same columns, tags and readiness rules as section 2)

The cBioPortal counts below are value totals from the public cBioPortal API (`/clinical-data`, `/sample-lists`). No expression data was downloaded.

| Tag | Ready | Roster ID → data location | Cancer | Drug class | Pre n | Pairs | Response: where it lives and how it is defined | Expression and units | Access | ICBatlas |
|---|---|---|---|---|---|---|---|---|---|---|
| A | **R1** | ICB-BULK-014/042, Mariathasan 2018 IMvigor210 → cBioPortal `blca_iatlas_imvigor210_2017`, plus Genentech package [IMvigor210CoreBiologies](http://research-pub.gene.com/IMvigor210CoreBiologies/) (about 122 MB tarball, still served, last modified 2019-02). Raw: EGAS00001002556 (controlled) | Urothelial, metastatic | PD-L1 (atezolizumab) | **347**, all "Pre", FFPE | – | cBioPortal `RESPONSE`, RECIST: CR 25 / PR 43 / SD 63 / PD 167 (49 without a label). The package's `pData(cds)` has "all sample annotations" according to its vignette. The exact BOR column name in the package is UNVERIFIED | cBioPortal: iAtlas-harmonized RNA-seq. Package: raw counts (`CountDataSet`), TruSeq RNA Access, which is an exome-capture chemistry | Open processed; raw controlled. Package licence UNVERIFIED | no |
| A | **R1** (supplement) | ICB-BULK-029, Braun 2020 (PMID 32472114, [PMC7499153](https://pmc.ncbi.nlm.nih.gov/articles/PMC7499153/)). Raw: EGAS00001004290/1/2 (CheckMate 009/010/025; controlled) | ccRCC, advanced | PD-1 (nivolumab). CheckMate 025 also has an **everolimus** arm, which must be dropped | UNVERIFIED (mostly archival; timing UNVERIFIED) | – | PMC supplement **Table S1, "Clinical and immune phenotype data"** (ORR per patient: UNVERIFIED until the file is opened) | PMC supplement **Table S4, "RNA expression (normalized expression matrix)"**. Normalization method UNVERIFIED | Open supplement; raw controlled | no |
| A | **R1** | ICB-BULK-016, Van Allen 2015 (phs000452, controlled) → cBioPortal `skcm_dfci_2015` | Melanoma | CTLA-4 (ipilimumab) | 40 with RNA | – | cBioPortal field named `DURABLE_CLINICAL_BENEFIT`, but its values are RECIST-like (CR / PR / SD / PD / X) across 110 patients | `rna_seq_mrna` (units UNVERIFIED) | Open processed; raw controlled | **yes** (SRP011540) |
| A+B | R1 | ICB-BULK-017, Snyder 2014 (dbGaP [phs001041](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001041), controlled) → cBioPortal `skcm_mskcc_2014` | Melanoma | CTLA-4 (mostly ipilimumab; 4 tremelimumab) | 21 RNA samples in total. `BIOPSY_TIME` is 34 pre / 30 post across all 64 samples | Possible; UNVERIFIED | `TREATMENT_RESPONSE` (response 14 / non-response 41) and long- vs no-benefit (author definition) | `rna_seq_mrna` | Open processed; raw controlled | no |
| A | R1 (upgrade) | ICB-BULK-032, Liu 2019 → cBioPortal `mel_iatlas_liu_2019` (also `mel_dfci_2019`, which has TPM and `BR`) | Melanoma | PD-1 (± prior CTLA-4) | **122**, all "Pre" | – | `RESPONSE`, RECIST: CR 16 / PR 32 / SD 18 / PD 56 | iAtlas-harmonized RNA-seq; `mel_dfci_2019` has TPM | Open processed; raw FASTQ public (section 1) | **yes** |
| A+B | R1 (upgrade) | ICB-BULK-015, Gide 2019 → cBioPortal `mel_iatlas_gide_2019` | Melanoma | PD-1 (41) or PD-1+CTLA-4 (34) | 73 | 18 on-treatment | `RESPONSE`, RECIST: CR 17 / PR 32 / SD 13 / PD 29 | iAtlas-harmonized RNA-seq | Open processed | **yes** |
| A | R1 | ICB-BULK-020, [GSE165745](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE165745) (PMID 33951424) | Melanoma, metastatic | PD-1 | 24 | – | GEO `phenotype`: responder 12 / non-responder 12. Definition is in the paper (UNVERIFIED) | NanoString Wnt + immune custom panel (**panel**), RAW.tar | Public | no |
| A+B | R1 | PROST-BULK-010, PORTER (NCT03835533) → GitHub [ParkerICI/porter-trial-data](https://github.com/ParkerICI/porter-trial-data) | mCRPC | PD-1+other (nivolumab-based cohorts A/B/C) | Baseline biopsies, about 43 patients (RNA n UNVERIFIED) | Not in the RNA file (baseline only) | Clinical CSV: BOR by **PCWG3-modified RECIST 1.1**, PSA50 responder, composite responder, 6-month disease control | Raw counts + TPM per gene (long format). The README names the RNA file `AMADEUS_primarycohort_…`, a different trial's name, so check this before use | Open processed; raw not public. No licence file in the repo | no |
| B | R2 | PROST-BULK-004, [GSE77910](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77910) (PMID 28346412) | Prostate, localized | CTLA-4 + ADT (ipilimumab + leuprolide) | 3 | 6 post (pairing UNVERIFIED) | Not in GEO | Affymetrix array, RAW.tar | Public | no |
| A | X / R2 | ICB-BULK-023, [GSE183924](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE183924) (PMID 34604072) | Esophageal/GEJ adenocarcinoma | PD-L1, **adjuvant** after chemoradiation and surgery | 37 (timing relative to durvalumab UNVERIFIED) | – | A clinical xlsx is in GEO. Adjuvant setting, so the outcome is relapse or DFS, **not RECIST** (UNVERIFIED) | FPKM only | Public | no |
| A | R1 (meta) | ICB-BULK-040, cBioPortal melanoma aggregate | – | – | – | – | Resolves to the per-study rows above, plus `mel_iatlas_riaz_nivolumab_2017` and `mel_iatlas_hugo_ucla_2016` (already in the pipeline as GSE91061 and GSE78220) | – | Open | – |

**Off-roster bonus.** These are iAtlas-harmonized cBioPortal studies with "Pre" RNA and RECIST labels that are not on the roster. All are open processed data.

- `rcc_iatlas_immotion150_2018`: RCC. 174 atezolizumab-treated (88 + bevacizumab), 89 sunitinib (drop these). Pre 263 in total. CR 19 / PR 53 / SD 96 / PD 79.
- `brca_iatlas_anders_2022`: TNBC, pembrolizumab + cyclophosphamide. Pre 31. CR 1 / PR 6 / SD 3 / PD 21.
- `paad_iatlas_prince_2022`: PDAC, chemo ± nivolumab (50 nivolumab). Pre 64 + 29 on-treatment. PR 38 / SD 29 / PD 18. A+B.
- `ccrcc_iatlas_choueiri_2016`: RCC, nivolumab. Pre 16. PR 3 / SD 5 / PD 8.
- `gbm_iatlas_prins_2019`: GBM, 15 pre + 15 on. This is GSE121810, already in PROPOSED_RECORDS.

### 4b. Unavailable or controlled (13)

| Roster ID | Study | Where the data actually is |
|---|---|---|
| ICB-BULK-028 | OAK/POPLAR (Patil 2021) | EGAD00001007703: 891 pre-treatment NSCLC transcriptomes, atezolizumab or docetaxel. **Controlled** (EGA policy EGAP00001002123) |
| ICB-BULK-030 | CheckMate 067 RNA-seq | EGAD00001006306: 38 samples. **Controlled** (EGAP00001001640) |
| ICB-BULK-034 | Helmink 2020 | EGAS00001003178 (neoadjuvant nivolumab ± ipilimumab melanoma, NCT02519322). **Controlled** |
| ICB-BULK-035 | Cabrita 2020 | No PMC full text. No GEO series found with a TLS + ICB search. **UNVERIFIED / not located** |
| ICB-BULK-036 | Chen 2016 | No PMC full text and no GEO hit. NanoString data may be in the paper supplement (**UNVERIFIED**) |
| ICB-BULK-037 | Herbst 2014 | PMC text cites no accession. **No deposit located** |
| ICB-BULK-038 | Miao 2018 | dbGaP [phs001493](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001493), "Genomic Predictors of Response to Immune Checkpoint Therapy". **Controlled** (and no public FASTQ, section 1) |
| ICB-BULK-039 | Cristescu 2018 | dbGaP [phs001572](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001572), cited in the PMC text. **Controlled**; whether it holds expression data is UNVERIFIED |
| ICB-BULK-041 | Nathanson 2017 | PMC text cites no accession. Probably dbGaP (phs001041 is Snyder's study; whether Nathanson's data is there is UNVERIFIED). See the Snyder row above for open RNA |
| ICB-BULK-044 | Weber-era nivolumab deposits | No GEO series found with a CheckMate 064 / nivolumab melanoma expression search. **Not located** |
| PROST-BULK-007 | KEYNOTE-199 (pembrolizumab mCRPC) | No deposit. The roster note agrees |
| PROST-BULK-008 | CheckMate 650 (nivolumab + ipilimumab mCRPC) | No open deposit. A related spatial Zenodo record (PROST-SPAT-002) is not bulk |
| PROST-BULK-013 | PROSTVAC + nivolumab | No deposit |

The roster also lists Kim gastric 2018 (ICB-BULK-031), which is counted as covered: ENA PRJEB25780, public FASTQ, section 1. EGAS00001004050 (PROST-BULK-001) is also covered; its dataset EGAD00001005713 holds WES + RNA-seq, 87 samples from 30 patients, **controlled**.

**Roster errors found:**

- ICB-BULK-021 GSE165252 is **esophageal adenocarcinoma** (PERFECT trial: chemoradiation + atezolizumab), not rectal. GEO has responder 23 / non-responder 48 / NA 6 across baseline, on-treatment and resection samples.
- GSE213145 (ICB-BULK-027) has no response field in GEO; its 20 samples are all pre-anti-PD-1 FFPE.
- GSE295599 (PROST-BULK-006) is a mixed cancer cohort that includes only **3 prostate** samples. Its time field is 16 baseline / 13 on-treatment.

### 4c. Out of scope (64), one line per group

- **ICB-SC (21) and PROST-SCRNA (5):** single-cell or PBMC. None hides a bulk tumour + response series, except GSE149652, GSE200996 and GSE205506, which are already flagged in PROPOSED_RECORDS. The GSE246613 SuperSeries composition is UNVERIFIED.
- **ICB-SPAT (7) and PROST-SPAT (2):** spatial, imaging or regional data. Not whole-tumour bulk.
- **ICB-PROT (6) and PROST-PROT (3):** proteomics or serum (GSE39688 and GSE50410 are serum).
- **ICB-PATH (5), PROST-PATH (1) and ICB-BULK-018 (Tumeh 2014, IHC):** pathology or IHC, no RNA.
- **ICB-MET (2) and PROST-META (1):** metabolomics or lipidomics.
- **PROST-NICHE (3), PROST-WES (1), PROST-CTDNA (1), PROST-CYTOF (1):** DNA, ctDNA or CyTOF only.
- **Other prostate bulk out of scope:**
  - PROST-BULK-009, GSE246684: 2 nodules from one untreated patient.
  - PROST-BULK-012, GSE294391: PBMC.
  - PROST-CAR-001, GSE214583: cell line and xenograft.
- **ICB-BULK-045:** a meta-row pointing to a secondary catalogue, not a cohort.

### 4d. Plain summary

1. The roster has 117 records: 30 were already covered, 10 are newly qualified, 13 are unavailable or controlled, and 64 are out of scope.
2. The biggest find: **IMvigor210 is open**. cBioPortal has 347 pre-treatment urothelial RNA profiles with RECIST labels (CR 25 / PR 43 / SD 63 / PD 167), and the Genentech R package with raw counts is still served. This would be Paper A's largest cohort.
3. Several cohorts the roster lists as "controlled" have **open processed RNA + response on cBioPortal**: Van Allen 2015, Snyder 2014, Liu 2019 (122) and Gide 2019 (73 pre + 18 on). Braun 2020 RCC has open supplement tables for clinical data (S1) and normalized RNA (S4).
4. For Paper B, PORTER (mCRPC, nivolumab-based) gives open baseline RNA counts/TPM with PCWG3-RECIST and PSA labels on GitHub, but no on-treatment RNA. GSE77910 adds a small prostate ipilimumab pre/post array set.
5. These remain controlled or missing: OAK/POPLAR, CheckMate 067, Helmink, Miao, Cristescu, and the three prostate ICB trials (KEYNOTE-199, CheckMate 650, PROSTVAC + nivolumab). Cabrita, Chen 2016, Herbst and the Weber deposits were not located.

## 5. Epigenetic drug + checkpoint inhibitor cohorts (combination paper, 2026-10-29)

These cohorts are for the separate combination paper (rule: `docs/decisions/COMBINATION_COHORTS_20261029.md`), not Papers A and B. The exception is the ICI-only arm of a randomised mixed study, which can go to A/B under the same rule.

**How this was made.** Metadata only; nothing was downloaded. Requests were spaced at least 1 s apart.
- GEO through E-utilities (db=gds): an epigenetic-drug AND checkpoint-drug query (111 series), plus an epigenetic-drug AND patient/trial query (534 series). The series were screened by title, and every row below was checked against GEO `acc.cgi` (series and GSM characteristics, counted in aggregate).
- PubMed: an epigenetic-drug AND checkpoint-drug AND trial query (82 papers), plus 6 targeted queries. Data-availability statements were read from PMC full text (33 papers).
- EGA metadata API for every EGA accession found; ClinicalTrials.gov API v2 (184 registered epigenetic + ICI trials, 54 with posted results; trial records not opened one by one); cBioPortal study keyword search (no epigenetic-drug study found); GitHub API for the repositories the papers name.
- Columns and readiness follow the column key above: **R1** = response in GEO plus a public matrix; **R2** = public matrix, labels only in the paper; **R3** = raw or controlled only; **X** = set aside.
- **Lead-in** = a tumour biopsy taken after the epigenetic drug alone, before the first ICI dose (like GSE248014's C1D1).

### 5a. Solid tumours with public data

| Ready | Accession | PMID | Cancer | Regimen | Patients | Timepoints (samples) | Epi-only lead-in | Assay | Response labels (definition) | Access |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 (already in pipeline; registry) | [GSE248014](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE248014) | 39532835 | PDAC, metastatic (NCT03250273) | Entinostat 2-week lead-in, then entinostat + nivolumab | 25 with RNA (27 evaluable in trial) | Baseline 23, C1D1 18, C2D1 4 | **Yes** (C1D1, 18 samples) | Bulk RNA-seq, processed table | GEO `recist` Responder / NonResponder (RECIST 1.1 ORR); 5 of 45 samples responder | Public |
| **R1, new** | [GSE343570](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE343570) | none in GEO; paper not found (trial number UNVERIFIED, possibly NCT02638090) | NSCLC, first line, metastatic, PD-L1 ≥1% | **Randomised**: arm A pembrolizumab alone; arm B pembrolizumab + vorinostat | 45 (A 24, B 21) | Pre 33 (A 16, B 17), on-treatment cycle 1 day 14–21: 33; pairs 21 (A 10, B 11) | No (concurrent start) | Bulk RNA-seq, RSEM counts | BOR in sample titles (PR / SD / PD; assumed RECIST, UNVERIFIED). Patients with a pre sample: A PR 6 / SD 5 / PD 5; B PR 9 / SD 5 / PD 3 | Public |
| R1 (registry) | [GSE211645](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE211645) (NIBIT-M4) | 37739939, 31530631 | Melanoma, advanced | Guadecitabine + ipilimumab | 14 with pre samples | Pre, W4, W12 | No biopsy in it. Guadecitabine starts week 0 and ipilimumab week 1 (PMID 37739939), but the first on-treatment biopsy (W4) is after both | Custom NanoString (**panel**) | GEO `response to therapy` BOR; titles count SD as responder | Public |
| R2 | [GSE188249](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE188249) (RNA) / [GSE186825](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE186825) (methylation), SuperSeries GSE188250 | 35671108 | Ovarian, platinum-resistant (NCT02901899, UNVERIFIED) | Guadecitabine days 1–4, pembrolizumab day 5, every 21 days | 17 (RNA) | Baseline C1D1 17, C2D8 9; RNA pairs 9; methylation pairs 11 | No (C1D1 is pre-everything; pembrolizumab starts day 5 of cycle 1) | Bulk RNA-seq (RAW.tar per sample); EPIC array | GEO `responder` R / NR (RNA baseline R 7 / NR 10). The paper defines durable clinical benefit as benefit lasting ≥6 cycles; that GEO R = this is UNVERIFIED | Public. Already in the lead list (overlap flag) |
| R2 | [GSE222932](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222932) (RNA + WES) / [GSE222933](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222933) (methylation), SuperSeries GSE222934 | 36928921 | Urothelial, metastatic, after ICI progression | Guadecitabine + atezolizumab | 15 with RNA (18 with WES) | RNA pre 15 / post 7 (pairs 7); methylation pre 17 / post 8. Post = before C3D1 (about 12 weeks) | No | Total RNA-seq (RAW.tar); EPIC beta matrix | Not in GEO. Paper: no RECIST responses; patients split into SD vs PD | Public |
| R2 (methylation only) | [GSE147537](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE147537) (METADUR) | 32753546 | MSS CRC 14, ER+ breast 10, ovarian 4 (samples) | CC-486 (oral azacitidine) days 1–14 (± vitamin C) + durvalumab day 15, every 28 days | 11 with ≥2 samples (16 pre-treatment samples) | Baseline, cycle 2 day 12 (pre 16 / post 12) | No (on-treatment biopsy is after both drugs) | EPIC methylation only, **no RNA** | Not in GEO; paper reports RECIST ORR | Public |

### 5b. Solid tumours, controlled or not deposited

| Ready | Accession | PMID | Cancer | Regimen | Patients | Timepoints | Epi-only lead-in | Assay | Response labels | Access |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R3 | EGAS00001005478 (PEMDAC) | 34453044 | Uveal melanoma, metastatic (NCT02697630) | Entinostat + pembrolizumab | 29 treated; 20 RNA | Pre-treatment only | No (pre only) | RNA-seq + exome, FFPE | RECIST ORR (14%) | EGA controlled |
| R3 | EGAS50000000731 (PEVO) | 40588522, 41468684 | Squamous-cell carcinomas, basket (NCT04357873) | Pembrolizumab + vorinostat | UNVERIFIED | Baseline mandatory; before the first assessment and at progression optional | No | EGA study type is exome; RNA-seq UNVERIFIED | RECIST | EGA controlled |
| R3 | EGAS50000001165 / EGAD50000001664 | 41652014 | Ovarian, platinum-resistant (NCT02900560) | Oral azacitidine (4 dose cohorts) + pembrolizumab from day 1 | 34 enrolled, 20 evaluable; EGA dataset has 24 samples | Baseline, week 6 | No | Bulk RNA-seq | ORR 2.9%, DCR 50%, CA-125 response | EGA controlled |
| R3 | EGAS00001006419 (RNA) / EGAS00001006420 (WGBS) | 36923309 | Melanoma, anti-PD-1-resistant | Azacitidine + carboplatin priming (2 cycles), then avelumab | 20 enrolled; RNA for 3 | Baseline, week 9 (after priming), week 22 | **Yes, but priming includes carboplatin** | RNA-seq, WGBS | RECIST | EGA controlled |
| R3 (UNVERIFIED accession) | Paper cites "EGA50000000682"; EGAS50000000682 resolves to an unrelated study | 40091844 | HNSCC, after ICI progression (NCT03019003) | Low-dose 5-azacytidine (5 or 10 days) + durvalumab + tremelimumab | 12 treated; 8 pairs | Baseline, on-treatment (timing not stated in the extract) | UNVERIFIED | Sequencing (type UNVERIFIED) | Exploratory | EGA, accession needs correction |
| X (no raw data) | J15221; GitHub `OncologyQS/J15221_RNAseq_paper`, `FertigLab/J15221_trial_paper` | 38355777, 40585251, 42578817 | Breast, HER2-negative (NCT02453620) | 2-week entinostat run-in, then entinostat + nivolumab + ipilimumab | 19 with biopsies (37 biopsies) | Baseline, C1D1 (after the run-in), week 8 | **Yes** | Bulk RNA-seq, but raw data are not shared (no consent). GitHub holds only DE results and per-sample CyTOF tables | RECIST and clinical benefit | Not public. GSE303155 from the same group is mouse |
| X (no deposit found) | none | 33203644 | NSCLC after anti-PD-(L)1 (ENCORE-601, NCT02437136) | Entinostat + pembrolizumab | 76 treated | Not stated | UNVERIFIED | None found | RECIST ORR | No deposit found. The ENCORE-601 melanoma cohort was not located |
| X (data on request) | none | 34991708; 41844546; 38302476; 35717027; 40021215; 42882866; 39941804; 38518549; 40102759 | CRC (aza + pembro); PDAC (aza + pembro); ccRCC (guadecitabine + durvalumab, 57 pts); solid tumours (guadecitabine + pembro, phase 1); breast neoadjuvant window (decitabine + pembro); mucosal melanoma (oral decitabine/cedazuridine + nivolumab, 8 pts); HNSCC (tazemetostat + pembro); oesophagogastric (domatinostat + avelumab); solid tumours (BET inhibitor RO6870810 + atezolizumab) | as listed | n/a | n/a | n/a | n/a | n/a | "On reasonable request", supplement only, or Vivli |
| X (no deposit found) | none | 31409616; 31796519; 30654297; 35678233; 34135021; 37087488; 34552864; 36890020; 38438735 | NSCLC (pembro + vorinostat, phase I/Ib); HNSCC/salivary (pembro + vorinostat); NSCLC randomised (pembro ± CC-486, 100 pts); melanoma (mocetinostat + ipi + nivo); solid tumours (entinostat + nivo ± ipi, ETCTN-9844); solid tumours (aza + epacadostat + pembro); NSCLC (citarinostat + nivo); NSCLC (mocetinostat + durvalumab); MSS CRC randomised (chidamide + sintilimab + bevacizumab; not in PMC, UNVERIFIED) | as listed | n/a | n/a | n/a | n/a | n/a | No accession in the full text |

Not located: other arms of NCT03250273 beyond PDAC (the cholangiocarcinoma arm), and any tucidinostat/chidamide + ICI solid-tumour human RNA deposit (GSE301188 is chidamide in mice). GSE292179 (DNMTi + anti-PD-1, NK/T lymphoma) deposits only mouse and cell-line RNA; set aside as X.

### 5c. Haematological malignancies (bone marrow or blood, not tumour biopsy)

These pair a hypomethylating agent with ICI and are public, but the tissue is marrow or blood, so solid-tumour gene panels would not read the same way.

| Ready | Accession | PMID | Disease | Regimen | Timepoints (samples) | Epi-only lead-in | Assay | Response labels | Access |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | [GSE326589](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE326589) | 42305767 | MDS, HMA-relapsed/refractory | Guadecitabine + atezolizumab | 21 individuals; screening 21, post-cycle 2: 13, post-cycle 4: 8 | No | Bulk RNA-seq of CD34+ cells (42) + CITE-seq | Not in GEO (paper: survival) | Public |
| R1 (panel, blood) | [GSE219085](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE219085) | 36988276 | MDS | ICI ± HMA (52 samples ICI + HMA, 20 ICI alone, 26 HMA alone) | Pre 49 / post 49 | No | NanoString 579-gene panel, peripheral blood | GEO `response`: Response / Non-response | Public |
| R2 (panel, pre only) | [GSE178926](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE178926) | 36099049 | AML, relapsed/refractory (NCT02845297) | Pembrolizumab + azacitidine | Pre-treatment 33 | No | NanoString, bone marrow | GEO has survival only; response in paper | Public |
| R3 | [GSE223844](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE223844) | 36706355 | MDS/AML (ETCTN 10026) | Decitabine lead-in cycle, then decitabine + ipilimumab | Screening, end of lead-in, C1, C2, end of treatment | **Yes** (end of decitabine lead-in) | scRNA-seq; raw in dbGaP phs003015 | Paper | GEO processed; raw controlled |
| R3 | [GSE195471](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE195471) | 35017151 | AML, relapsed/refractory (NCT02996474) | Pembrolizumab + decitabine | Day 0, later, relapse (6 patients) | No | scRNA-seq / CITE-seq | Paper | Public |
| R2 | [GSE271406](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE271406) | none | AML | Pembrolizumab + decitabine | Multiple follow-ups, 10 patients (bulk) | No | Bulk total RNA (count.csv) + scRNA-seq | Not in GEO | Public |

### 5d. Plain summary

1. **One strong new cohort:** GSE343570, a randomised NSCLC trial (pembrolizumab alone vs pembrolizumab + vorinostat), with RNA-seq counts, 21 pre/on pairs and BOR in the sample titles. Under the combination rule, its pembrolizumab-only arm can feed A/B, and the arm comparison is causal because it was randomised.
2. **Public solid-tumour sets with response in the paper only (R2):** guadecitabine + pembrolizumab in ovarian cancer (GSE188249, with methylation in GSE186825), guadecitabine + atezolizumab in urothelial cancer (GSE222932/3), and CC-486 + durvalumab (GSE147537, methylation only).
3. **Epigenetic-drug-only lead-in biopsies** like GSE248014's C1D1 exist in J15221 (breast), the azacitidine + carboplatin melanoma study and ETCTN 10026 (decitabine, myeloid), but none of these has public tumour RNA. GSE248014 remains the only public solid-tumour set with a lead-in biopsy.
4. **Controlled on EGA:** PEMDAC (uveal melanoma, pre-treatment only), PEVO (squamous basket), azacitidine + pembrolizumab in ovarian cancer, and the azacitidine + durvalumab + tremelimumab HNSCC study (whose EGA number needs correcting). ENCORE-601 and most vorinostat, mocetinostat and guadecitabine trials have no deposit.
5. **The blood-cancer HMA + ICI sets are public** (MDS and AML: GSE326589, GSE219085, GSE178926, GSE271406), but they are marrow or blood, not tumour biopsies, so they fit the combination paper only as a side analysis.
