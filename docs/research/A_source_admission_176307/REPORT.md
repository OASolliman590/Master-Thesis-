# GSE176307 source-admission audit — proposed evidence, 2026-09-06

**Source readiness remains conditional; neither A-P1 nor A-P2 is selected. The metadata ceiling is 88 labelled patient codes, not an eligible analysis N.** This audit inspected cached original GEO metadata, the official name key, bounded processed-file prefixes and the original article. No expression scores, models or effects were calculated; no complete matrix was downloaded.

## Corrected identity and response counts

The earlier `specs/A/DATA.md` numbers (90 records, 89 labelled records; CR7/PR9/SD4/PD69/NA1) are correct **record** counts but must not become patient counts. Independent recomputation against the cached SOFT and JSON gives **89 patient codes: CR7, PR9, SD4, PD68, NA1**. BACI165 occurs as GSM5362510 and GSM5362511, both PD; the series explicitly identifies repeat sequencing. BACI217/GSM5362552 has response NA. Therefore the provisional ORR categories contain 16 positive and 72 negative patient codes, before timing, assay QC, duplicate policy and response-adjudication admission. The four SD codes remain the small proposed A-P1 switching group. [Original GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176307); locally recomputed in `metadata_audit.json`.

The downloaded name key contains 89 patient rows and 90 unique RS assay identifiers. BACI165 maps to RS-03239001 and RS-03238964. All patient codes match the GSM titles, and all 90 mapped assays exist in the current TPM header. **However, that header contains 92 unique assay columns:** RS-03238998 and RS-03239044 have no entry in the key. Their identities must remain unresolved; no inferred response or patient mapping is justified. The key does not explicitly map each BACI165 suffix `_1`/`_2` to its RS identifier, although both assays map unambiguously to the same patient. [Official sample-name key](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE176nnn/GSE176307/suppl/GSE176307_BACI_Omniseq_Sample_Name_Key_submitted_GEO_v2.csv.gz), [current TPM file](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE176nnn/GSE176307/suppl/GSE176307_salmon_tpm_gene.matrix.tsv.gz).

## Original study and timing/response boundaries

Rose et al., *British Journal of Cancer* (2021), DOI **10.1038/s41416-021-01488-6**, reports UNC patients treated January 2014–June 2018, archived FFPE from primary/metastatic sites, and successful RNA profiling in 89 patients. **Methods → Clinical annotation** specifies retrospective RECIST v1.1 review by a radiologist blinded to FGFR3 status; deaths before imaging or clinical progression without post-treatment imaging counted as nonresponse. Its clinical-benefit endpoint includes CR/PR or SD lasting at least six months. This does not establish that every deposited PD is imaging-confirmed, or that all SD satisfies that duration. **Methods → Patient samples** provides no patient-level specimen collection/ICI interval. Therefore archival tissue is verified; pre-ICI status remains unverified here. [Original article, PMC methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC8548561/), [publisher version](https://doi.org/10.1038/s41416-021-01488-6).

The cached article HTML is inspectable at `article_response.html` (the request used `?report=xml`, but returned HTML, not XML). The original study's Figure 3a colour-label error was corrected in 2022; the correction does not describe a clinical-label correction. [Correction DOI 10.1038/s41416-022-01781-y](https://www.nature.com/articles/s41416-022-01781-y).

GEO series recruitment says 2014–2018, while every sample's `source_name_ch1` says 2014–2021. Preserve that discrepancy; neither date string proves specimen timing. Patient-level `io.therapy` counts are atezolizumab34, pembrolizumab47, nivolumab5, durvalumab2, avelumab1. This is a mixed single-agent anti-PD-1/PD-L1 source, not an atezolizumab-only cohort. [GEO SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE176nnn/GSE176307/soft/GSE176307_family.soft.gz), local audit.

## Actual file formats and version boundary

| File inspected | Verified structure | Unit/coverage limit |
|---|---|---|
| `salmon_tpm_gene.matrix.tsv.gz` | Complete header: blank identifier heading plus 92 unique RS columns; tab-delimited | GEO declares TPM; 2023-07-12 replaces the older `BACI_tpm_gene.matrix.tsv`. No complete gene universe, CYT coverage, missingness or values validated. |
| `baci_rsem_RS_BACI_headers_tab.txt.gz` | Complete header: blank identifier heading plus 90 RS columns, exactly matching the key | RSEM-named output; exact quantitative field not established by filename/header. Must not automatically call these TPM or raw counts. |
| `BACI_log_trans_normalized_RNAseq.csv.gz` | Gene-column orientation. The 32KB compressed prefix does **not** reach the end of the header; 9,749 observed fields are a lower bound, not total genes. GZMA/PRF1 occur in the inspected header portion. | GEO describes filtered, log-transformed read counts; sample row identities not reached. Their presence here does not verify CYT availability in the current TPM file. |

The [official supplementary inventory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE176nnn/GSE176307/suppl/) lists approximately 9.7M compressed TPM, 19M RSEM and 6.6M transformed CSV. Only **32,768 compressed bytes per matrix** were retained. Prefix digests are not complete-file digests. Source processing describes RSEM/count filtering and transformed downstream analyses separately from the later Salmon TPM file; do not transfer cohort centring/scaling to the new file by assumption. [GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176307).

## Study overlap and proposed exact spec changes

`UNC-108`, Rose2021, GSE176307 and copies in atlases describe one originating source, not independent validation cohorts. The 2025 six-cohort meta-analysis explicitly identifies UNC-108 as GSE176307. Its reuse does not establish absence of patient overlap with every other trial. Record the originating-study alias before atlas admission; audit benchmark development exposure separately. [Primary reanalysis, data availability](https://www.nature.com/articles/s41467-025-56462-0).

Proposed changes only:

1. Amend A/DATA's source row with both record and patient counts above; retain 88 as a ceiling and mark baseline timing pending. Do not replace it with an eligible N.
2. Add response-system value `RECIST1.1_retrospective_with_clinical_nonresponse_exception`; retain unknown patient-level imaging adjudication. A-P1 CR/PR/SD/PD recoding is a proposed ontology, not identical to the study's six-month clinical-benefit definition. Do not recover SD duration from treatment duration or PFS without a justified definition.
3. Pin the 2023 TPM filename and require a full-file checksum, complete feature annotation/QC and GZMA/PRF1 verification before scoring. Use the explicit name-key join; quarantine the two unmatched RS columns with reasons. Define one outcome-independent representation of BACI165 before preprocessing or splitting.
4. For A-P2, this is at most **one** source cohort. Neither a train/test split across its therapies nor treating duplicate assays as patients meets independent-source validation. Freeze its development/final-test role before any feature screening; neither role is assigned here.
5. Reopen admission only with a specimen-timing source, a declared policy for the non-imaged response exception, the duplicate rule, and completed matrix QC/annotation. If those remain unavailable, retain a conditional/sensitivity-only proposal instead of silently asserting primary eligibility.

## Provenance and access limits

`PROVENANCE.json` records exact local bytes/SHA256, URLs, inspected scope and failed routes; `download_receipts.json` preserves response headers and partial flags. `audit_metadata.py` reproduces the identifier/header counts offline; its hash is in `PROVENANCE.json`. Cached metadata hashes are preserved in `metadata_audit.json`. New retained response/download bytes total **329,568**, including a 21,455-byte HTML challenge at the supplemental-PDF URL. No supplement contents were successfully inspected. Europe PMC XML returned404; the publisher supplement host had a DNS failure. The original article HTML succeeded. Raw sequence data are unavailable under the submitter's privacy statement; this audit makes no redistribution permission claim beyond public accessibility. [GEO original record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176307).
