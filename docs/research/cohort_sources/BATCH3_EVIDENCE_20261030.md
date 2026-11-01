# Batch 3 source evidence: processing, timing, response and prior ICI (2026-10-30)

These are the facts the batch-3 worksheets need (`.scratch/runtime/<cohort>/final-unsigned-20261030/WORKSHEET.md`).

**Sources used:** papers (PMC full text), GEO series and sample text records (`acc.cgi`, `form=text`), ClinicalTrials.gov API v2, cBioPortal meta files at the pinned datahub commit `e1b75cd25bf7436d16719b7d76117ad8f3f66e54`, and cBioPortal API aggregate value counts.

**What was not done:** no expression or clinical data file was downloaded or opened. No patient or sample IDs appear here. Nothing was committed.

**Status key:**
- **SOURCED** = stated in a primary document, quoted with its location.
- **UNDOCUMENTED** = searched for in the reachable primary sources and not stated.
- **UNVERIFIED** = plausible, or located in a supplement that was not opened; needs a reviewer.

---

## 1. Braun 2020 (*Nat Med*, PMID 32472114; CheckMate 009 / 010 / 025)

Source: Braun et al., PMC7499153, Methods ("Transcriptomic analysis", "Clinical benefit", "Patient cohorts", "Data availability").

### (a) Expression processing

| Fact | Status | Quote / location |
| --- | --- | --- |
| Aligner / quantifier | SOURCED (tools); **versions UNDOCUMENTED** | "RNA-seq data from the CheckMate 010 and 025 cohorts were aligned using STAR, quantified using RSEM, and evaluated for quality using RNA-seqQC2" |
| CheckMate 009 part | SOURCED | "For the CheckMate 009 cohort, the previously published TPM matrix was used" (a different, earlier processing) |
| QC exclusions | SOURCED | samples excluded if "interquartile range of log2(TPM+1) < 0.5", "less than 15,000 genes detected", or strand-bias thresholds; for duplicates "the run with a higher interquartile range… was used" |
| Normalization and transform (Table S4A) | SOURCED | "filtered genes that were not expressed in any of the samples (in each cohort independently) then upper quartile-normalized the TPMs to an upper quartile of 1000, and log2-transformed them" |
| Batch correction | SOURCED | "4 batches were corrected for using ComBat", then "a constant that was equal to the first integer above the minimum negative expression value obtained post-ComBat (constant of +21)" |
| Where the matrix is | SOURCED | Data availability: "normalized RNA-seq expression data … are available in Supplementary Table 4" |
| Reference build / annotation for RNA | **UNDOCUMENTED** (the WES section says hg19; the RNA section names no build or annotation) | — |
| Feature scope | SOURCED in part: genes not expressed in any sample were removed, per cohort. Biotype scope **UNDOCUMENTED** | as above |

**V3 consequence:**
- Unit/transform can be pinned as **log2(upper-quartile-normalized TPM, UQ = 1000), ComBat-corrected across 4 batches, +21 offset**. These values are not raw TPM, and ComBat was fit across both arms.
- Reference, annotation and tool versions remain UNDOCUMENTED.

### (b) Biopsy timing

**SOURCED; not uniformly pre-ICI at the time of collection.** The paper says:
- "Formalin-fixed, paraffin embedded tumor tissue (mostly archival; see Supplementary Table 1 for timing of sample collection)… were obtained prior to initial anti-angiogenic therapy for patients enrolled in the CM-010 and CM-025."
- Discussion: "As mostly archival (prior to anti-angiogenic therapy) tumor specimens were available… the immune infiltrate may have further evolved prior to PD-1 blockade."

So the samples precede nivolumab, but most were collected before earlier anti-angiogenic lines, not just before ICI. Per-sample timing lives in **Supplementary Table 1 (S1)**, whose column contents are UNVERIFIED (not opened).

### (c) Response definitions

| Label | Status | Definition (quote) |
| --- | --- | --- |
| **CB** (clinical benefit) | SOURCED | "patients with objective responses (complete or partial), or stable disease with tumor shrinkage and PFS of at least 6 months, were classified as having clinical benefit (CB)" |
| **NCB** (no clinical benefit) | SOURCED | "Patients with progressive disease and PFS less than 3 months were classified as having no clinical benefit (NCB)" |
| **ICB** (intermediate clinical benefit) | SOURCED | "All other patients were classified as intermediate clinical benefit (ICB)". The paper compares CB vs NCB only. **Note:** "ICB" here means intermediate benefit, not immune checkpoint blockade |
| **CRPR** | SOURCED as a response category | used as a group name: "clinical benefit vs. no clinical benefit, CRPR vs. PD". CRPR = complete or partial response (RECIST objective response), pooled. The response assessment criteria per trial (RECIST 1.1 per CheckMate protocols) are UNVERIFIED in this paper |
| Per-patient labels | SOURCED (location) | "Clinical data about the patients… are listed in Supplementary Table 1" |

### (d) Prior ICI

ClinicalTrials.gov eligibility (registry text):

| Trial | Status | Finding |
| --- | --- | --- |
| CheckMate 009 (NCT01358721) | **SOURCED: excluded** | "Prior therapy with … anti-CTLA4, anti-PD1, anti-PD-L1, anti-PD-L2, anti-CD137, anti-CD40, anti-OX40 antibodies" is an exclusion criterion |
| CheckMate 025 (NCT01668784) | **UNDOCUMENTED in the registry** | The listed criteria cover prior anti-angiogenic and mTOR therapy only. The full protocol (not retrieved) may exclude prior ICI |
| CheckMate 010 (NCT01354431) | **UNDOCUMENTED in the registry** | "not have had more than 3 prior treatments" only |

All three trials enrolled patients before any anti-PD-1 approval in RCC, so prior ICI is unlikely, but that is not a source statement. Under the current policy, keep prior ICI **UNKNOWN for CM-010/025 patients** and **NONE (eligibility) for CM-009**.

---

## 2. Van Allen 2015 (*Science*, PMID 26359337; cBioPortal `skcm_dfci_2015`)

Sources: Van Allen et al., PMC5054517 (author manuscript, main text); datahub meta files at the pinned commit; cBioPortal API (aggregate counts).

| Item | Status | Quote / location |
| --- | --- | --- |
| **RPKM vs FPKM** | **UNDOCUMENTED (conflict stands).** The datahub file is `data_mrna_seq_rpkm.txt`, but `meta_mrna_seq_rpkm.txt` says "profile_description: Expression levels (RNA-Seq FPKM)". The paper's main text does not describe RNA quantification; its supplementary methods (Science online) were not reachable as text | datahub meta files; PMC5054517 |
| Aligner / quantifier / build / annotation | UNDOCUMENTED (main text silent; the supplement was not read) | — |
| **Timing** | **SOURCED, study-wide pre-treatment**: "we analyzed whole exomes from pretreatment melanoma tumor biopsies… For 40 of these patients, we also obtained and analyzed transcriptome data from the pretreatment tumor samples." Inclusion required "pretreatment germline and tumor samples available for sequencing" | PMC5054517, abstract and Methods |
| **Clinical benefit definition** | SOURCED: "'clinical benefit' was defined using a composite end point of complete response or partial response to ipilimumab by RECIST criteria or stable disease by RECIST criteria with overall survival greater than 1 year (n = 27). 'No clinical benefit' was defined as progressive disease by RECIST criteria or stable disease with overall survival less than 1 year (n = 73)." The remaining patients form a long-term-survival group (paper: "The subset of patients that showed long-term survival…") | PMC5054517, main text |
| What the cBioPortal field holds | SOURCED (aggregate): `DURABLE_CLINICAL_BENEFIT` contains **RECIST-style best response values**, not the benefit composite: CR 3 / PR 14 / SD 12 / PD 76 / X 5 (110 patients). The meaning of "X" is **UNVERIFIED** (likely not evaluable). The benefit composite needs OS > 1 year applied to SD, so it is a derived label | cBioPortal API |
| Regimen | SOURCED: `TREATMENT` = ipilimumab for all 110; paper: "received ipilimumab monotherapy" | cBioPortal; paper |
| **Prior ICI** | **UNDOCUMENTED.** The paper records "number of therapies received before ipilimumab" but not their type; ipilimumab was the first approved ICI, so prior PD-1 is unlikely but unstated | paper (table S3 referenced, not opened) |

---

## 3. GSE135222 (Jung 2019, *Nat Commun*, PMID 31537801; also Clin Epigenetics 2020, PMID 32762727)

| Item | Status | Quote / location |
| --- | --- | --- |
| Aligner + version | SOURCED: "Alignment was performed using STAR (2.5.3)" | GEO sample data_processing (all 27) |
| Quantifier + version | SOURCED: "gene expression values were quantified using RSEM (1.3.1)" | GEO |
| Unit / transform | SOURCED: "gene expression matrix (tab-delimited text file; TPM unit)"; no log stated | GEO |
| Reference build | SOURCED: "Genome_build: hg19"; paper: "aligned to the human reference genome (hg19) with STAR" | GEO; PMC6753140 Methods |
| Annotation release / feature scope | **UNDOCUMENTED** | — |
| Platform | SOURCED: Illumina HiSeq 2500; "RNA was extracted from same tumour tissue using Allprep DNA/RNA Mini Kit" | GEO |
| **Response definition** | SOURCED: "The clinical response was evaluated by… RECIST version 1.1 with a minimum 6-month follow-up… Partial response (PR) or stable disease (SD) that lasted more than 6 months was considered as DCB/responder. Progressive disease (PD) or SD that lasted less than 6 months was considered as NDB/non-responder." | PMC6753140, Methods "Clinical data of the SMC cohort" |
| **Where per-patient labels live** | GEO carries only `progression-free survival (pfs)` (event 1/0) and `pfs.time`, **not DCB/NDB**. The paper puts the clinical data for the 60-patient SMC cohort (which includes the 27 RNA-seq patients) in **Supplementary Table 3**: "were enrolled for this study (Supplementary Table 3)". It is in the Supplementary Information PDF (`41467_2019_12159_MOESM1_ESM.pdf`). Its columns (DCB, agent, timing) are **UNVERIFIED** (not opened) | PMC6753140 |
| **Timing** | **UNDOCUMENTED.** Neither GEO nor the paper's Methods says whether the profiled tissue was collected before ICI start. The GEO design only says "RNA-seq for a total of 27 advanced non-small cell lung carcinoma patients who were treated with anti-PD-1/PD-L1" | GEO; paper |
| **Agent per patient** | **UNDOCUMENTED in GEO** (no agent field). The paper says "anti-PD-1/PD-L1"; per-patient agent is probably in Supplementary Table 3 (UNVERIFIED) | — |
| **Prior ICI** | **UNDOCUMENTED** | — |

---

## 4. GSE136961 (Hwang 2020, *Sci Rep*, PMID 31959763)

| Item | Status | Quote / location |
| --- | --- | --- |
| Assay | SOURCED: targeted RNA panel, "Oncomine™ Immune Response Research Assay", "sequencing of a 395-gene panel" (GEO: "about 400 genes"); Ion Torrent S5 XL; FFPE; Ion AmpliSeq library kit 2.0 | GEO extract_protocol; PMC6971301 Methods |
| Alignment / counting + version | SOURCED: "Alignment of the sequences to the reference immuneresponse V3.1 and counting of the sequencing reads were performed using the ImmuneResponseRNA Report plug-in in Torrent Suite software (Version 5.2)" | GEO data_processing |
| Reference build | SOURCED: "Genome_build: hg19". The panel reference is "immuneresponse V3.1" (amplicon reference, not a genome annotation release) | GEO |
| Units | SOURCED: raw counts: "Scores represent raw read counts"; TPM: "generated by calculating TPM… by normalizing each gene length and the total read counts" (panel-level TPM, so not comparable to whole-transcriptome TPM) | GEO |
| Feature scope (paper) | SOURCED: "Among the 395 genes, 2 genes which were not expressed in any patients, and 11 housekeeping genes were excluded" (from the analysis). Whether the deposited files keep them is UNVERIFIED | PMC6971301 |
| **The 5 extra raw-count columns** | **UNVERIFIED but explained by the paper:** "Of the twenty-six samples included in sequencing, we removed five samples for which total read counts were less than 1 million." 26 sequenced − 5 removed = 21 GEO samples, which matches 5 extra columns. Which columns they are must not be inferred. GEO also notes "The submitter is unable to locate the raw data for" eleven named cases (sequence files, not matrix columns) | PMC6971301 Methods; GEO overall design |
| **DCB definition** | SOURCED: "Cases showing a partial or complete response to anti-PD-1 antibody (nivolumab or pembrolizumab) by RECIST v1.1 lasting >24 weeks or stable disease lasting >24 weeks were considered as having a durable clinical benefit (DCB). Cases showing progression of disease or stable disease lasting ≤24 weeks were considered as [NDB]" | GEO growth_protocol (all samples); paper Methods |
| **Per-patient DCB/NDB source** | SOURCED in aggregate: there is no response characteristic in GEO. The **sample titles carry a D or N prefix** (9 D, 12 N), matching the paper's "Nine (43%) showed a durable clinical benefit (DCB), while the remaining 12 (57%)… non-durable benefit (NDB)". Using the title prefix as the label is a mapping rule a reviewer must approve | GEO sample titles (aggregate count only); paper abstract |
| **Timing** | SOURCED study-wide: GEO "The mRNA expression of non-small cell lung cancer patinets before anti-PD-1 immunotherapy were measured"; paper: "we analyzed the transcriptomes of tumor tissues before treatment". There is no per-sample timing field | GEO overall design; PMC6971301 |
| Agent | SOURCED study-wide: "single-agent anti-PD-1" (nivolumab or pembrolizumab). Per-patient agent **UNDOCUMENTED** in GEO | GEO; paper |
| **Prior ICI** | **UNDOCUMENTED.** Table 1 gives "Prior systemic therapy" counts (1, 2, 3, ≥4 lines by DCB/NDB) but not their type | PMC6971301, Table 1 |

---

## 5. GSE176307 (Rose et al. 2021, *Br J Cancer*, PMID 34294892)

**Paper:** "Fibroblast growth factor receptor 3 alterations and response to immune checkpoint inhibition in metastatic urothelial cancer: a real world experience" (GEO `Series_pubmed_id` 34294892). The PMC record (PMC8548561) holds the **abstract only**. The publisher page redirects to a Nature sign-in/cookie flow, which was not followed. **The paper's full Methods were therefore not read**, and the facts below come from GEO.

| Item | Status | Quote / location |
| --- | --- | --- |
| Aligner / quantifier | SOURCED: "Reads were aligned with STAR aligner to (GrCH38 version 22) human assembly using the STAR/Salmon pipeline"; "Expression was quantified using the RSEM package… and the GrCH38 human transcriptome reference". Versions **UNDOCUMENTED** | GEO data_processing |
| Reference | SOURCED: "Genome_build: GrCH38 v.22". Whether "version 22" means GENCODE v22 or something else is **UNVERIFIED** (ambiguous wording) | GEO |
| **Gene filtering / feature count** | SOURCED: "Genes were filtered for a minimum expression count (at least 10 reads in at least 5 samples), and for a protein coding annotation by Ensemble (final set of genes = 16,901)." The pipeline's matrix (`GSE176307_BACI_log_trans_normalized_RNAseq.csv`) has 16,383 feature columns per the worksheet. **The 518-gene difference is UNDOCUMENTED** in GEO; the paper's Methods are not reachable | GEO; worksheet |
| **Transform / median-centring** | SOURCED: the BACI file is "Log transformed and filtered read count output". For other analyses: "all expression values were log2(1+x) transformed, median centered and upper quartile scaled". Whether the deposited BACI file is the median-centred version or only log-transformed is **UNVERIFIED**; GEO describes the file as "log transformed and filtered" only | GEO data_processing |
| Other deposited files | SOURCED: `salmon_tpm_gene.matrix.tsv` = "TPM values"; it "replaced GSE176307_BACI_tpm_gene.matrix.tsv" on 2023-07-12. An RSEM header file and a sample-name key are also deposited | GEO overall design / supplementary files |
| Duplicate profile | SOURCED: "Sample [one case] was sequenced twice" | GEO overall design |
| Raw data | SOURCED: "raw data are unavailable due to patient privacy concerns" | GEO |
| **Response** | SOURCED (field): GEO `io.response` = CR 7 / PR 9 / SD 4 / PD 69 / NA 1 (90 samples; aggregate). The **definition** (RECIST version, investigator- or central-assessed, real-world assessment) is **UNDOCUMENTED** in GEO; the abstract says only "Objective response rate to ICB". Per-sample `pfs`, `progressed` and `duration.of.io.tx` are also in GEO | GEO characteristics |
| Agent | SOURCED (field): `io.therapy` = pembrolizumab 47, atezolizumab 35, nivolumab 5, durvalumab 2, avelumab 1 | GEO characteristics (aggregate) |
| **Timing** | **UNDOCUMENTED per sample.** GEO says only "RNA sequencing of patients with advanced UC" (source "Patient with metastatic UC treated with…"); there is no collection-date or pre/post field. Real-world FFPE specimens; whether they predate ICI is not stated | GEO |
| **Prior ICI** | **UNDOCUMENTED.** GEO has `io.lot` (line of the ICB therapy: 1 = 21, 2 = 62, 3 = 5, 4 = 2). Line > 1 means prior therapy, not necessarily prior ICI | GEO characteristics |

---

## Plain summary: what V3 can now pass, and what stays unknown

1. **Braun 2020**
   - Now pinned: the processing chain (STAR + RSEM TPM → upper-quartile normalized to 1000 → log2 → ComBat across 4 batches → +21 offset); the CB/ICB/NCB definitions ("ICB" = intermediate benefit); CRPR = pooled complete or partial response; tissue that is mostly archival and pre-anti-angiogenic.
   - Prior ICI: excluded by CheckMate 009 eligibility. CheckMate 010/025 registry text is silent.
   - Still unknown: tool versions, reference build/annotation, and the per-sample timing columns in S1 (not opened).
2. **Van Allen 2015**
   - Now pinned: pre-treatment timing (study-wide); the clinical-benefit composite (CR/PR, or SD with OS > 1 year).
   - Corrected: the `DURABLE_CLINICAL_BENEFIT` field actually holds best response (CR/PR/SD/PD/X).
   - Still unknown: RPKM vs FPKM, the whole quantification pipeline, the meaning of "X", and prior ICI.
3. **GSE135222 (Jung 2019)**
   - V3 processing can pass: STAR 2.5.3, RSEM 1.3.1, TPM, hg19. The DCB/NDB definition is pinned.
   - Still unknown: per-patient DCB and agent (GEO has only PFS; they are probably in the paper's Supplementary Table 3, not opened), biopsy timing, annotation, and prior ICI.
4. **GSE136961 (Hwang 2020)**
   - Now pinned: the panel processing (Oncomine Immune Response, Torrent Suite 5.2 plug-in, immuneresponse V3.1 reference, hg19, raw counts plus panel TPM); the DCB definition; study-wide pre-treatment timing.
   - Per-patient DCB/NDB comes from the D/N title prefix (9/12, matching the paper), which needs reviewer approval as a mapping rule.
   - The 5 extra raw-count columns match the paper's 5 low-read samples removed from 26, but they must not be assigned to patients.
   - Still unknown: per-patient agent and prior ICI.
5. **GSE176307 (Rose 2021)**
   - Now pinned from GEO: STAR/RSEM on GRCh38 "v22"; protein-coding filter to 16,901 genes; the deposited file is "log transformed and filtered"; median-centring and upper-quartile scaling were applied "for all other analyses".
   - Still unknown:
     - the 16,901 vs 16,383 gap;
     - whether the deposited file is median-centred;
     - the response definition;
     - per-sample timing;
     - prior ICI (`io.lot` gives line of therapy only).
   - The paper's full text is abstract-only in PMC, and the publisher page requires a sign-in flow that was not followed.

---

## A. recount3 as source (Gide, Kim) and sensitivity (Riaz, Hugo)

Sources:
- Wilks et al. 2021, *Genome Biol*, PMID 34844637 (PMC8628444);
- the recount3 Bioconductor package source, `LieberInstitute/recount3` (branch `devel`, file `R/transform_counts.R`);
- `langmead-lab/monorail-external` and `langmead-lab/recount-pump` READMEs;
- the recount3 S3 release bucket (`recount-opendata.s3.amazonaws.com/recount3/release/human/`), read with HEAD requests plus the per-project sample metadata (`sra.sra.<project>.MD.gz`, `sra.recount_project.<project>.MD.gz`).

No gene_sums file was downloaded.

| Fact | Status | Quote / location |
| --- | --- | --- |
| What `gene_sums` values are | SOURCED: **base-pair coverage sums**, not read counts. Paper: "Megadepth produces a bigWig file representing depth of coverage at every genomic base… Monorail's aggregator uses a custom tool to sum these back into the full set of annotated genes and exons. The result is a… file containing coverage sums across all genes and exons". Package: "Note that the raw counts are the sum of the base level coverage" | PMC8628444, Methods "Monorail: gene and exon quantification"; `transform_counts.R` roxygen |
| Annotation of G026 | SOURCED: G026 = GENCODE v26. The package's annotation options include "gencode_v26", "gencode_v29", "fantom6_cat", "refseq", "ercc", "sirv"; the gene-sum files are named `sra.gene_sums.<project>.G026.gz` | `R/annotation_options.R`; bucket paths (HEAD 200) |
| Reference | SOURCED: "Reference indexes + annotations are already built/extracted for human (HG38, Gencode V26)" | monorail-external README |
| Tool versions | SOURCED for the aligner: "the versions of the 3 tools that use them in recount-pump are: STAR 2.7.3a, Salmon 0.12.0, HISAT2 2.1.0" (gene sums come from the STAR alignment). **Megadepth version UNDOCUMENTED.** recount-pump says its README links "versions of scripts/configurations that were actually used to run `sra_human_v3`", but those links are cluster job configs that do not state a Megadepth version | monorail-external README; recount-pump README |
| **Conversion 1: `transform_counts()`** (scaled counts, the default) | SOURCED: `by = c("auc", "mapped_reads")`, `targetSize = 4e7`, `L = 100`, `round = TRUE`. With `by = "auc"`: `scaleFactor <- targetSize / x[[auc]]`, with the AUC column `recount_qc.bc_auc.all_reads_all_bases` ("L cancels out… since the raw counts are the sum of base-level coverage"). With `by = "mapped_reads"`: `targetSize * L * ifelse(paired_end, 2, 1) / (mapped_reads * avg_mapped_read_length^2)`, using `recount_qc.star.all_mapped_reads` and `recount_qc.star.average_mapped_length` | `R/transform_counts.R`, `compute_scale_factors()` |
| **Conversion 2: `compute_read_counts()`** (approximate read counts, unscaled) | SOURCED: `counts <- t(t(assays(rse)$raw_counts) / colData(rse)[[avg_mapped_read_length]])`, then `round()`, with `avg_mapped_read_length = "recount_qc.star.average_mapped_length"`. Documented as computing "the read counts" from base-pair counts | `R/transform_counts.R` |
| Paired-end handling | SOURCED: `is_paired_end()` sets `ratio <- round(recount_qc.star.average_mapped_length / recount_seq_qc.avg_len, 0)`; paired if the ratio is 2 (NA with a warning if neither 1 nor 2). For paired data `average_mapped_length` is the summed mate length, so `compute_read_counts()` returns **fragment-level** counts. This is inferred from the code (UNVERIFIED wording) | `R/transform_counts.R` |
| **Run → sample → patient linkage** | SOURCED: `sra.sra.<project>.MD` has one row per run with `external_id` (run accession), `sample_acc` (ENA/SRA sample accession), `experiment_acc`, `sample_name`, `sample_title` and `sample_attributes` (pipe-separated `key;;value`). Observed fill (aggregate): Gide 91 runs / 91 distinct samples, all with `sample_title` and attributes (ENA "Title", "Sample Name", "Description"); Kim 45 / 45 (attributes include `tissue_type`, `sex`, "Title"); Riaz 109 / 109 (attributes `response`, `source_name`, `tissue`); Hugo 28 / 28 (attributes include `patient id`, `biopsy time`, `anti-pd-1 response`). The BioSample (SAMEA/SAMN) accession is **not** a column; it is reached from `sample_acc` through the ENA sample record | recount3 bucket metadata (aggregate inspection only) |
| Layout | SOURCED: all four projects paired-end, all RNA-Seq | `library_layout`, `library_strategy` |

**V3 consequence:** for Gide and Kim, unit = GENCODE v26 gene-level base-pair coverage sums on hg38 from STAR 2.7.3a. The conversion must be named in the field map:
- `compute_read_counts()` for count-based work; or
- `transform_counts(by = "auc")` for library-size-scaled counts.

The conversion's metadata columns (`recount_qc.star.average_mapped_length`, `recount_qc.bc_auc.all_reads_all_bases`) come from the project's QC metadata. The Megadepth version stays UNDOCUMENTED.

---

## B. Kim 2018 gastric (*Nat Med*, PMID 30013197; ENA PRJEB25780 / ERP107734)

| Item | Status | Finding / quote / location |
| --- | --- | --- |
| Paper access | Not in PMC. The publisher page redirects to a Nature sign-in/cookie flow (not followed). The abstract is SOURCED: "61 patients with mGC who were treated with pembrolizumab as salvage treatment in a prospective phase 2 clinical trial" | PubMed abstract |
| **Prior ICI** | **SOURCED (study-level exclusion):** ClinicalTrials.gov NCT02589496 ("Study of Pembrolizumab in Subjects With Advanced Gastric or Gastroesophageal Junction Adenocarcinoma Who Progressed After First-Line Therapy With Platinum and Fluoropyrimidine…"), exclusion 16: "Has received prior therapy with an anti-PD-1, anti-PD-L1, or anti-PD-L2 agent." Prior anti-CTLA-4 is not named. That NCT02589496 is the paper's trial is UNVERIFIED (the paper text was not reachable), though the title and design match | ClinicalTrials.gov API |
| **45 vs 78 runs** | SOURCED (aggregate ENA metadata). ENA PRJEB25780 has 188 runs: 110 WXS + 78 RNA-Seq, one run per sample. The 78 RNA runs fall into two groups: **45** with titles "PB-#-#", `tissue_type` = Gastric, first public 2018-04-08 (**exactly the 45 runs in recount3**); and **33** with titles "PB-#-#-N", no `tissue_type`, first public 2019-11-05. All 33 "-N" RNA samples share a base ID with one of the 45, so 33 patients have two RNA samples. In WXS, the same "-N" suffix marks 55 matched germline/normal samples alongside 55 tumour samples. **What the 33 "-N" RNA samples are (normal tissue? a second timepoint?) is UNVERIFIED**; the ENA records give no tissue type or timepoint. recount3 includes only the 2018 tumour-labelled set | ENA filereport / sample search (aggregate patterns only) |
| Biopsy timing | **UNDOCUMENTED** from reachable sources. The 45 tumour RNA samples carry no timepoint in ENA. iAtlas has a `Kim_NatMed_2018_Sample_Treatment` grouping over 45 samples (values not retrieved) | ENA; iAtlas API |
| **Where per-patient RECIST response is** | Searched: **(1)** ENA sample attributes: no response field (tissue_type, sex, Title only). **(2)** The paper's supplement PDF has clinicopathology but no response (per the brief); the paper figures and source data could not be read (publisher sign-in). **(3)** ORCESTRA `ICB_Kim`: its clinical data are read from a file named `gas_korean_cli_data.csv` (`ICB_Kim-snakemake/scripts/Format_Data.R`: `read.table( file.path(input_dir, "gas_korean_cli_data.csv") …)`). The response is recoded as `clin$recist = ifelse( clin$recist %in% 0 , "PD" , ifelse( clin$recist %in% -1 , "SD" , ifelse( clin$recist %in% 1 , "CR" , NA ) ) )`, a **3-level code that labels every responder "CR"** (PR is not distinguishable). **The origin of `gas_korean_cli_data.csv` is UNDOCUMENTED** in the repository. Expression in ORCESTRA comes from kallisto (`Kim_kallisto.zip`). **(4)** iAtlas (`Kim_NatMed_2018`, 45 samples) has `Response`, `Responder`, `Clinical_Benefit`, `Progression` and `Prior_ICI_Rx` groupings (API cohort list); values not retrieved, and iAtlas processing is undocumented. **(5)** ICBatlas / TIDE: unreachable or BLOCKED (see the harvest note) | ORCESTRA GitHub; iAtlas API; ENA |
| Response definition | **UNDOCUMENTED** from reachable sources (the paper's Methods could not be read). The trial registry lists ORR as the primary outcome (UNVERIFIED wording) | — |

**Kim verdict:**
- **Prior ICI:** NONE for anti-PD-1/PD-L1/PD-L2, by trial eligibility. Anti-CTLA-4 is not covered by the criterion.
- **Expression:** recount3 holds exactly the 45 tumour-labelled RNA runs.
- **Response:** no primary per-patient response source was reachable. The two secondary sources are ORCESTRA's coarse recode, from an undocumented file, and iAtlas, which is undocumented. Their counts are not checked here. Response stays **UNKNOWN** until the paper's figures and supplementary tables are read by someone with journal access, or the user approves a secondary source as CROSS_CHECK.
