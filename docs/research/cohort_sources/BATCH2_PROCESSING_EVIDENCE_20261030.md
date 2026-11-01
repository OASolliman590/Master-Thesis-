# Batch 2 processing and prior-ICI evidence (2026-10-30)

For `docs/decisions/BATCH2_CBIOPORTAL_20261030.md`, item 5 (still open). This is documentation and metadata only: no expression or clinical data file was downloaded, and no patient-level values are reproduced here. Clinical fields are summarised as aggregate counts from the cBioPortal API (`projection=SUMMARY`).

Pinned datahub commit: `e1b75cd25bf7436d16719b7d76117ad8f3f66e54`. Datahub meta files below are cited at that commit, as `https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/<study>/<file>`.

**Status key:** **SOURCED** = stated in a primary document quoted here. **UNDOCUMENTED** = searched for and not found in any public source reached. **UNVERIFIED** = plausible but not confirmed from a source.

---

## 1. iAtlas processing of the ICI RNA-seq (IMvigor210, Liu, Gide)

### What the datahub files state

| Study | Meta file | Quote | Status |
| --- | --- | --- | --- |
| `blca_iatlas_imvigor210_2017` | `meta_mrna_seq_tpm.txt` | "profile_name: mRNA expression (TPM)"; description only "Expression levels" | Unit only |
| `blca_iatlas_imvigor210_2017` | `meta_mrna_seq_tpm_zscores_ref_all_samples.txt` | "mRNA expression z-scores (log TPM)" | Implies the base file is linear TPM, logged before z-scoring (UNVERIFIED for the base file) |
| `mel_iatlas_liu_2019` | `meta_mrna_seq_tpm.txt` | "profile_name: mRNA expression"; file name `data_mrna_seq_tpm.txt` | Unit only from the file name |
| `mel_iatlas_gide_2019` | `meta_mrna_seq_expression.txt` | "profile_name: mRNA expression (log2 upper quartile normalized counts)" | Unit and transform; who normalized is not stated |
| all three | `meta_study.txt` | e.g. IMvigor210: "The reprocessing of raw sequencing data is coordinated by CRI iAtlas" | The description is about whole-exome and neoantigen data ("Whole-exome sequencing and neoantigen landscape analysis…"); it does not say RNA was reprocessed |
| all three | `meta_study.txt` | IMvigor210 and Gide: "reference_genome: hg38"; Liu iAtlas: "reference_genome: hg38" | Genome build declared at study level; not stated for the RNA profile |

The datahub pull requests that added these studies have no processing description:
- [cBioPortal/datahub#2248](https://github.com/cBioPortal/datahub/pull/2248), "Add 5 public studies from iAtlas" (merged 2025-12-12; IMvigor210, Liu): the body lists the study names only.
- [cBioPortal/datahub#2264](https://github.com/cBioPortal/datahub/pull/2264), "Add iatlas studies" (merged 2026-02-12; Gide): the body lists the study names only.

### What iAtlas documents

| Source | Quote / finding | Bearing |
| --- | --- | --- |
| Eddy et al. 2020, F1000Research, PMID 33214875 ([PMC7658727](https://pmc.ncbi.nlm.nih.gov/articles/PMC7658727/)), "Data" section | "The iAtlas app uses structured data and outputs from the Immune Landscape … and the TCGA PanCancer Atlas initiative" | Describes TCGA harmonisation only. No ICI-cohort RNA pipeline in this paper |
| iAtlas app `inst/markdown/about.markdown` ([CRI-iAtlas/iatlas-app, branch `staging`](https://github.com/CRI-iAtlas/iatlas-app/blob/staging/inst/markdown/about.markdown)) | "based on publicly available datasets that we have processed for use in iAtlas" | Says iAtlas processed them; no method, tool or annotation given |
| iAtlas notebooks `ici_query_iatlas_data.ipynb` ([CRI-iAtlas/iatlas-notebooks](https://github.com/CRI-iAtlas/iatlas-notebooks/blob/main/ici_query_iatlas_data.ipynb)) | "clinical data, immune features, scores of predictors of response to immunotherapy, and quantile normalized gene expression" | The iAtlas **database/API** expression is described as quantile normalized. Whether the cBioPortal TPM / UQ files are the same values is UNVERIFIED |
| iAtlas manifests `R/genes_to_samples_ici.R` ([CRI-iAtlas/iatlasManifests](https://github.com/CRI-iAtlas/iatlasManifests/blob/main/R/genes_to_samples_ici.R)) | Loads expression from Synapse entity `syn25981839` ("ici_genes_to_samples.feather", created 2021-07-13, in project "CRI iAtlas" `syn10337516`) | Synapse metadata is public but has **no provenance activity** ("No activity") and no annotations. The processing code is not linked |
| iAtlas dataset table `inst/feather/datasets_io_df_all.feather` (iatlas-app) | Columns: type, PMID, Citation, Paper, Sequencing.Method, Antibody, Study, Patients, Samples, Dataset | No processing or normalization column |
| `CRI-iAtlas/iatlas-workflows` README | "cwl workflows for public tools" | No RNA quantification workflow description found in the README |

### Answer to question 1

**UNDOCUMENTED.** No public source reached states one uniform iAtlas RNA-seq pipeline (aligner, quantifier, version, annotation) for the ICI cohorts.

The evidence points against one uniform TPM pipeline:
- Gide's iAtlas profile is "log2 upper quartile normalized counts", while IMvigor210 and Liu are TPM. A single reprocessing pipeline would be expected to give one unit.
- The iAtlas API documents "quantile normalized" expression, which is a third description.

This is inference, not a source statement. It is equally consistent with iAtlas carrying the **authors' own processed values** per cohort, but no document says so either.

**V3 consequence:** for the three iAtlas expression files, the following stay UNDOCUMENTED from source:
- quantifier and version;
- annotation release;
- feature scope.

Only the unit (TPM; log2 UQ counts) and the gene identifier columns present in the file can be recorded. Options:
- (a) Ask iAtlas (the portal lists a contact).
- (b) With authorization, compare numerically against the author tables: Liu DFCI TPM (already pinned) and the IMvigor210 package counts. A match would establish "author values".

---

## 2. Liu 2019 (`mel_dfci_2019`): authors' TPM

Source: Liu et al., Nat Med 2019, PMID 31792460 ([PMC6898788](https://pmc.ncbi.nlm.nih.gov/articles/PMC6898788/)), Methods, "Transcriptomic analysis".

| Fact | Quote | Status |
| --- | --- | --- |
| Aligner + quantifier | "aligned using STAR … and quantified with RSEM … to yield gene-level expression in transcripts per million (TPM)" | SOURCED (tools); **versions not stated** in the PMC text |
| Feature scope | snoRNA genes excluded: "excluding genes whose biotype was 'snoRNA' (n = 380 genes)" | SOURCED (gene level, snoRNA removed; other non-coding biotypes kept) |
| Annotation used for the biotype filter | "Ensembl biotype annotations (using the dataset 'hsapiens_gene_ensembl' and version 'GRCh38.p10')" | SOURCED for the filter. The alignment reference and GTF release are **UNVERIFIED** (not stated in the PMC text) |
| Renormalization | "We then regenerated a new TPM metric for each sample to normalize the total transcriptome sum to 1 million" | SOURCED (TPM re-summed after the snoRNA removal) |
| Transform | none stated; values are linear TPM | SOURCED by omission (no log stated) |
| Deposited matrix | "Supplementary Data 2 RNA-seq TPM matrix"; raw: "dbGaP (accession number phs000452.v3.p1)" | SOURCED |
| Response definition | "BOR to anti-PD1 ICB was assessed according to RECIST criteria v.1.1 by the participating sites" | SOURCED |

The datahub `mel_dfci_2019/meta_mrna_seq_tpm.txt` says only "Expression levels for genes in 144 metastatic melanoma samples (RNA Seq TPM)". It is consistent with, but does not cite, the paper's pipeline.

---

## 3. Gide 2019: "log2 upper-quartile normalized counts"

| Item | Finding | Status |
| --- | --- | --- |
| cBioPortal profile | "mRNA expression (log2 upper quartile normalized counts)" (`mel_iatlas_gide_2019/meta_mrna_seq_expression.txt`) | SOURCED (unit + transform) |
| Who normalized | Not stated in the meta files, the datahub PR #2264 or the iAtlas docs | UNDOCUMENTED |
| Authors' pipeline | Gide et al., Cancer Cell 2019, PMID 30753825, doi:10.1016/j.ccell.2019.01.003. **Not in PMC**; Europe PMC has no full text. The publisher page was not retrieved: automated access was blocked, and I did not work around it | **UNVERIFIED**: the methods need reading by a person with journal access |
| Raw data | ENA PRJEB23709, "Biomarkers of response and resistance to checkpoint blockade immunotherapy in metastatic melanoma" (public FASTQ, as resolved in the expanded cohort note). ENA sample records carry no clinical attributes | SOURCED |
| Author-side processed table to cross-check | None found in PMC, ENA or GEO. It may be in the paper's supplementary tables | **UNVERIFIED**; the cross-check stays open |

---

## 4. IMvigor210: prior ICI eligibility

**SOURCED: prior checkpoint blockade was an exclusion criterion.**

ClinicalTrials.gov [NCT02108652](https://clinicaltrials.gov/study/NCT02108652), Eligibility, Exclusion Criteria (record last updated 2024-03-28):

> "Prior treatment with CD137 agonists or immune checkpoint blockade therapies, including anti-cytotoxic T lymphocyte-associated antigen 4 (anti-CTLA-4), anti-programmed death-1 receptor (anti-PD-1), and anti-programmed death-ligand 1 (anti-PD-L1) therapeutic antibodies"

Notes:
- The criterion sits in the general Exclusion Criteria, not in the "Cohort 2-Specific" block. However, the current registry record lists only the Cohort 2 arm (310 enrolled). The record references both Rosenberg 2016 (PMID 26952546, cohort 2) and Balar 2017 (PMID 27939400, cohort 1).
- Cohort 1 had no prior treatment for metastatic disease. Balar 2017 ([PMC5568632](https://pmc.ncbi.nlm.nih.gov/articles/PMC5568632/)): "Cohort 1 enrolled patients without prior treatment for mUC." That supports ICI-naive status for cohort 1. The PMC texts of both Lancet papers say the full criteria are in the protocol on thelancet.com, which was not retrieved.
- The iAtlas study has 347 patients, all with `ICI_RX` = Atezolizumab (aggregate). Whether it pools cohorts 1 and 2 is UNVERIFIED; it has no cohort field in its clinical attributes.
- **For A-P2:** prior ICI can be set to **NONE (eligibility-documented)**, citing the NCT02108652 exclusion criterion, with cohort 1 covered by the "without prior treatment for mUC" statement. It is documented at study level, not per patient.

---

## 5. Liu and Gide: where prior ICI is documented

| Study | Field(s) | Aggregate | Level | Status |
| --- | --- | --- | --- | --- |
| `mel_dfci_2019` (author table) | `PRIOR_CTLA4` (patient attribute) | Yes 60 / No 84 (144 patients) | **Per patient, from the authors** | SOURCED. The paper analyses "ipilimumab-treated" vs "ipilimumab-naive" subgroups and says "Individual tumor characteristics are detailed in Supplementary Table 1" |
| `mel_iatlas_liu_2019` | `PRIOR_ICI_RX` (sample attribute; "ICI treatment(s) administered before the ICI treatment in the study") | aCTLA4 48; blank for the other 74 of 122 | Per sample, positives only | Blank is not "none": keep as UNKNOWN, as the existing source note already says (48/74 agree with the author table) |
| Gide `mel_iatlas_gide_2019` | No prior-ICI attribute. `ICI_RX` only (patient): Pembro 32, Nivolumab 9, Ipilimumab + Pembrolizumab 26, Ipilimumab + Nivolumab 8 (75 patients) | Study-arm level only | **UNDOCUMENTED per patient** in any source reached; the paper's supplementary tables are UNVERIFIED |

One timing caveat for Liu: the paper includes "ipilimumab-treated tumors biopsied prior to ipilimumab therapy" (15 tumours in an Extended Data analysis). So `PRIOR_CTLA4` = Yes describes the patient, not necessarily the biopsy. If the pipeline needs exposure **at biopsy**, the author Supplementary Table 1 is needed.

---

## Other finding

The iAtlas `RESPONSE` attribute is described identically in all three iAtlas studies as "Response to treatment following modified Response Evaluation Criteria in Solid Tumors (mRECIST) guidelines". The source papers state RECIST v1.1:
- Liu: "assessed according to RECIST criteria v.1.1".
- IMvigor210: "per Response Evaluation Criteria In Solid Tumors v1.1" (Balar 2017).

The iAtlas text looks like a generic template description. Record the endpoint as RECIST 1.1 from the papers, and note the iAtlas wording as a discrepancy.

## Plain summary

1. **iAtlas pipeline:** no public document gives the RNA-seq pipeline (aligner, quantifier, version, annotation) for the iAtlas ICI files. The cBioPortal meta files give units only. Gide is "log2 upper quartile normalized counts" while IMvigor210 and Liu are TPM, which argues against one uniform pipeline. For V3, those facts stay UNDOCUMENTED unless iAtlas is asked or a numeric comparison with the author tables is authorized.
2. **Liu (authors):** STAR + RSEM gene-level TPM, with 380 snoRNA genes removed (Ensembl GRCh38.p10 biotypes) and TPM re-summed to 1 million, linear scale. Tool versions and the alignment GTF are not stated in the PMC text.
3. **Gide:** only the profile label is sourced. The paper is not in PMC, the publisher page could not be read automatically, and no author-side processed table was found, so who normalized it and how is still open.
4. **IMvigor210:** prior anti-CTLA-4, anti-PD-1 and anti-PD-L1 therapy was an exclusion criterion (ClinicalTrials.gov NCT02108652), and cohort 1 was untreated for metastatic disease. A-P2 can document prior ICI as none at study level.
5. **Prior ICI per patient:** documented by the authors for Liu (`mel_dfci_2019` `PRIOR_CTLA4`: 60 yes / 84 no); iAtlas Liu marks positives only. For Gide, only the treatment arm is available, with no per-patient prior-ICI field.
