# A — ICI public cohort landscape (GEO MCP exploration, 2026-10-28)

Status: exploration only. Nothing here is admitted to the pipeline. A new cohort enters only as a field map plus a SHA-256-pinned fetch plan.
Scope: GEO metadata only (task 1). Paper and methods review is in the main session. No data files were downloaded and no biological analysis was run.

## How this was made

- **GEO search:** `geo` MCP (`search_geo_series`, `search_geo_samples`), five series queries, about 1,100 hits in total. These were filtered by keyword to about 170 patient ICI series.
- **GEO check:** every candidate below was re-checked by accession, using GEO `acc.cgi` brief text (series and sample `characteristics`). Sample counts, time points and labels in the tables come from that metadata. They do not come from the search hits.
- **PubMed / paper search:** dropped from this note on 2026-10-28 (scope change); the main session runs it. GEO-linked PMIDs below come from GEO series records only.
- **Exclusions and overlap:** cohorts already in the pipeline were excluded (GSE91061, GSE78220, GSE176307, GSE115821, GSE168204, GSE126044, GSE248014). Hits that are already in `docs/validation/A_DAV_04/PROPOSED_RECORDS.json` were also skipped. **Overlap flag:** the search also returned GSE121810, GSE136961, GSE149652, GSE165252, GSE181815, GSE188249, GSE200996, GSE205506, GSE266079, GSE274229 and GSE295599, all of which are already in the lead list. None of the candidates below appear anywhere in `docs/` or `tools/`.
- **UNVERIFIED** means the GEO metadata did not confirm the point.

## 1. Candidate cohorts (new, not in pipeline or lead list)

"Pre-tx n" is the number of GEO samples labelled baseline, pre-treatment or screening.

### Tier A — pre-treatment tumour, genome-wide bulk RNA, response label inside GEO metadata

| Accession | Cancer | Drug | Samples (pre-tx n) | Response: where it lives | Expression file(s) | Access |
|---|---|---|---|---|---|---|
| [GSE190266](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE190266) | NSCLC, advanced (Dijon "France4") | anti-PD-1 monotherapy, 1st/2nd line | 70 (70, "tumors collected at diagnosis") | GEO `pfs_evt (6 months)` and `pfs_time`: 52 events / 18 non-events. That is a 6-month PFS (CB-like) label, **not ORR**. ORR: UNVERIFIED | `GSE190266_TPM_France4.csv.gz` (kallisto TPM) | Processed public; no SRA link in GEO |
| [GSE235919](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE235919) | RAS-mutant metastatic CRC | durvalumab + tremelimumab + chemotherapy (1st line) | 34 (pre-tx: UNVERIFIED, likely baseline) | GEO `recist criterion`: CR 6 / PR 17 / SD 11, **no PD** | `GSE235919_TPM.txt.gz` | Processed public |
| [GSE202361](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE202361) | Soft-tissue sarcoma (DDLPS/UPS), neoadjuvant | ICB (NCT03307616; regimen: UNVERIFIED) | 64 (23 baseline) | GEO `outcome`: baseline PD 8 / SD 14 / PR 1 | `AllSamples_TPM` + `rawcount` | Processed public |
| [GSE345048](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE345048) | Inflammatory breast cancer, metastatic | atezolizumab + cobimetinib + eribulin, or atezolizumab + eribulin | 23 (16) | GEO `best response`: baseline PD 8 / SD 5 / PR 1 / unevaluable 2 | TPM, FPKM, expected counts (RSEM-style). Uses exome-capture RNA chemistry | Processed public; raw controlled (dbGaP phs004886) |
| [GSE162137](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE162137) | Cutaneous T-cell lymphoma | pembrolizumab | 64 LCM regions, 14 patients (25 PRE) | GEO `response`: responders / non-responders | `CTCL_raw_reads.csv.gz` (raw counts) | Public, raw in SRA (SRP294135). Note: these are laser-captured regions, not whole-tumour bulk |
| [GSE235863](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE235863) | HBV+ HCC | anti-PD-1 + lenvatinib | 69, of which 15 are bulk tumour | GEO `response`: bulk CR 5 / PR 6 / SD 2 / PD 2 (sample titles say "pre-treatment") | `bulk_rna_seq_raw_counts` + `bulk_rna_seq_tpm` | Processed public; raw in China GSA (HRA009324) |
| [GSE341672](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE341672) | TNBC / ER-low breast (MEDIOLA window trial) | olaparib, then olaparib + durvalumab | 160 (54 baseline; 49 pass QC) | GEO `pathologic complete response`: baseline yes 38 / no 16. pCR is measured after later neoadjuvant therapy (UNVERIFIED), so this is **not an ICI-only endpoint** | gene TPM, counts, gene length | Processed public; raw controlled (EGAS50000002019) |

### Tier B — pre-treatment tumour bulk RNA, but labels not in GEO metadata (need paper supplement or a GEO supplementary table)

| Accession | Cancer | Drug | Samples (pre-tx n) | Response: where it lives | Expression file(s) | Access |
|---|---|---|---|---|---|---|
| [GSE190265](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE190265) | NSCLC ("France3") | anti-PD-1 monotherapy | 34 (34) | Probably `GSE190265_samples_info_France3.csv.gz` (contents UNVERIFIED) | `TPM_France3.csv.gz` | Processed public |
| [GSE158403](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE158403) | Melanoma, advanced | GEO `treatment` = durva.mek / durva.mek.braf (anti-PD-L1 + MAPKi) | 95 (60 screening) | Not in GEO. Paper PMID [33288749](https://pubmed.ncbi.nlm.nih.gov/33288749/) (UNVERIFIED) | `FPKM_matrix.txt.gz` (FPKM only) | Public, raw in SRA (SRP285080) |
| [GSE343570](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE343570) | NSCLC, 1st line, PD-L1 ≥1% | pembrolizumab ± vorinostat (randomized phase 2) | 67 (32) | Not in GEO; paper not linked yet (UNVERIFIED) | `batch01.rsem.count.txt.gz` | Processed public |
| [GSE285963](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE285963) | HCC | atezolizumab + bevacizumab | 84 (73) | Not in GEO. Paper PMID [41362708](https://pubmed.ncbi.nlm.nih.gov/41362708/) (UNVERIFIED) | `readcount.gct.gz` | Processed public |
| [GSE302495](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE302495) | HCC, potentially resectable | nivolumab + ipilimumab | 70 (38) | Not in GEO. PMID [40972843](https://pubmed.ncbi.nlm.nih.gov/40972843/) (UNVERIFIED) | `readcount_tbl.txt.gz` | Processed public |
| [GSE179351](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE179351) | MSS CRC + PDAC | nivolumab + ipilimumab + radiation | 54 (23 Pre-Tx) | Not in GEO. PMID [35122060](https://pubmed.ncbi.nlm.nih.gov/35122060/) (UNVERIFIED) | Raw counts + DESeq2-normalized counts | Public, raw in SRA (SRP326688) |
| [GSE253564](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE253564) | NSCLC | durvalumab ± tremelimumab + radiation (two arms; UNVERIFIED) | 32 (32, archival FFPE) | Not in GEO. PMID [38401548](https://pubmed.ncbi.nlm.nih.gov/38401548/) | `Pre-treatment_Samples_Pubs_FPKMs` (FPKM only) | Processed public |
| [GSE318308](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE318308) | Recurrent ovarian | durvalumab + cediranib ± olaparib | 75 (about 55, sample titles `_pre`) | Series design says CB vs NCB (35 CB / 20 NCB). Per-sample labels not in GEO | `RAW.tar` (per-sample files; type UNVERIFIED) | Processed public |
| [GSE281729](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE281729) | HNSCC, neoadjuvant | nivolumab ± IDO inhibitor | 67 (36) | Not in GEO; pathological response (PMID [39585339](https://pubmed.ncbi.nlm.nih.gov/39585339/), UNVERIFIED) | logTPM processed file | Processed public |
| [GSE195832](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE195832) | Oral-cavity HNSCC, neoadjuvant | nivolumab | 86 (32 pre tumour) | Not in GEO. PMID [35262677](https://pubmed.ncbi.nlm.nih.gov/35262677/) | FPKM, read counts, featureCounts | Processed public |
| [GSE212525](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE212525) | ccRCC, neoadjuvant | sitravatinib, then sitravatinib + nivolumab | 50 (20 baseline; baseline is before both drugs) | Not in GEO. PMID [37164948](https://pubmed.ncbi.nlm.nih.gov/37164948/) | read counts (FFPE) | Processed public |
| [GSE273829](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE273829) | ccRCC (BIONIKK, NCT02960906) | nivolumab ± ipilimumab or TKI by subgroup (UNVERIFIED) | 92 (pre-tx: UNVERIFIED) | Not in GEO. PMID [42425076](https://pubmed.ncbi.nlm.nih.gov/42425076/) | kallisto raw counts | Processed public |
| [GSE293952](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE293952) | ccRCC, metastatic | 1st line TKI + IO (axitinib+pembrolizumab, cabozantinib+nivolumab, …) | 61 (61, "pretreatment") | Not in GEO. PMID [42242232](https://pubmed.ncbi.nlm.nih.gov/42242232/) | FPKM, batch-corrected FPKM, raw | Processed public |
| [GSE222934](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222934) | Urothelial, after prior ICI | guadecitabine + atezolizumab | 76 (50) | Not in GEO. PMID [36928921](https://pubmed.ncbi.nlm.nih.gov/36928921/) | `RAW.tar` (SuperSeries) | Processed public |
| [GSE319641](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE319641) | TNBC, NeoTRIP | atezolizumab + nab-paclitaxel/carboplatin vs chemo (randomized) | 401 (241 baseline) | Not in GEO; pCR (PMID [42162664](https://pubmed.ncbi.nlm.nih.gov/42162664/)) | **TPM already ComBat-corrected** across all samples | Processed public; raw not deposited |
| [GSE328930](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE328930) | MIBC, DUTRENEO | ICI vs neoadjuvant chemo (hot tumours randomized) | 66 | Probably `GSE328930_metadata.tsv.gz` (UNVERIFIED) | counts | Processed public |
| [GSE227666](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE227666) / [GSE271757](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE271757) / [GSE206422](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE206422) | Ovarian (3 studies) | chemo ± pembrolizumab; pembrolizumab + chemo; ICI regimen UNVERIFIED | 32 / 42 / 28 pre | Not in GEO | counts / RAW.tar / counts | Processed public |
| [GSE225078](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE225078), [GSE245372](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE245372) | mTNBC; non-metastatic ccRCC | pembrolizumab + chemo; neoadjuvant nivolumab | 20 pre; 13 pre | Not in GEO | RAW.tar; expected counts | Processed public, raw withheld |

### Checked and set aside

- [GSE110390](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE110390) (durvalumab, NSCLC 97 + UC 62): the processed files are only a 21-gene matrix. Raw reads are in SRA (SRP132535), so it could be rebuilt genome-wide, but labels are not in GEO. Worth keeping as a lead.
- Rejected because they lack pre-treatment tumour bulk RNA:
  - post-progression only: [GSE244982](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE244982)
  - spatial GeoMx: [GSE233305](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE233305), [GSE332987](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE332987), [GSE254054](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE254054)
  - blood, PBMC or single-cell: GSE252990, GSE253173, GSE289582, GSE302921, GSE313642, GSE335494, GSE288199, GSE314906, GSE264586, GSE241934
  - cell lines: GSE303456
  - n=9: GSE162436
- [GSE318645](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE318645) (GBM ipilimumab/nivolumab, 47 tumours, OS in GEO): the tumours were resected **after neoadjuvant dosing** in some arms (UNVERIFIED), so they are not clean pre-treatment samples.

## 2. Methods comparison

Covered in main session.

## 3. Implications for Paper A (cohort side only)

Literature-based reasoning (endpoint conventions, normalization practice, gaps in prior work) is covered in the main session. Below are only the facts that follow from the GEO metadata above.

**Endpoint**
- ORR-ready labels in GEO: GSE235919 (but no PD patients), GSE202361, GSE345048, GSE235863 (bulk n=15). GSE162137 has only responder / non-responder.
- Non-ORR labels only: GSE190266 (6-month PFS event) and GSE341672 (pCR after later neoadjuvant therapy, UNVERIFIED). These suit an endpoint-sensitivity arm, not the ORR arm.
- Unevaluable patients exist (GSE345048: 2 at baseline). Count and report them when dropped.

**Expression representation**
- Counts available (recompute TPM in the pipeline): GSE202361, GSE345048, GSE162137, GSE235863, GSE343570, GSE285963, GSE302495, GSE179351, GSE212525, GSE273829, GSE328930.
- TPM only: GSE190265, GSE190266, GSE235919, GSE341672 (counts also given).
- **FPKM only:** GSE158403, GSE253564. GSE293952 also has raw counts.
- **Pre-corrected:** GSE319641 ships TPM already ComBat-corrected across all samples, so avoid it or treat it as a separate case.

**Untouched final-test cohort (candidates)**
- NSCLC: **GSE343570** (pembrolizumab, 32 pre-treatment, public 2026; labels still needed).
- HCC: **GSE285963** (atezolizumab + bevacizumab, 73 pre-treatment, 2025) or **GSE302495** (nivolumab + ipilimumab, 38 pre-treatment, 2025).
- GSE190265/190266 date from 2021 and may already be in public ICI compendia. **UNVERIFIED**; check before use.
- Whichever is chosen: lock it and pin it by SHA-256 before any model is fit.
