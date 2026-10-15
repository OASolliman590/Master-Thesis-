# Data, source and clinical-state contract

PROPOSED. Source inventory is question-driven, processed-data-first and outcome-blind where an external role is reserved. `sources.jsonl` separates reported counts, repository-historical metadata counts, source-record counts and UNKNOWN eligible counts. It is a candidate manifest, not a download or admission manifest.

## Source-by-question architecture

| Question | Preferred source | Role and boundary |
|---|---|---|
| Which clinical programmes to investigate? | Frozen A development-only effects/programmes | Clinical anchor; no TCGA response labels |
| What varies in primary prostate specimens? | TCGA-PRAD RNA, methylation, clinical records | Discovery; same-patient modalities are not independent cohorts |
| What is altered relative to prostate reference tissue? | Verified TCGA tumour/adjacent pairs; independent paired RNA cohort if qualified | Explicit disease contrast; adjacent tissue is not healthy/ICI-positive truth |
| Do molecular associations/predictions transport? | CPC-GENE GSE107298/GSE107299 | External module after pairing/baseline/measurement lock; not automatically 210 eligible patients |
| Could genetic disruption explain the signal? | Same-specimen CNA/mutation; locus-specific HLA/LOH only if actually measured | Alternative explanation; ploidy is not locus CNA and absent calls are not wild type |
| Does protein support an RNA hypothesis? | TCGA RPPA when the analyte is covered; Sinha CPC proteogenomics MSV000081552 | Orthogonal assay, often overlapping patients; no new independent cohort by adding a modality |
| Does measured accessibility support regulation? | GDC Corces ATAC subset | Measured TCGA subset; PRAD paired N remains UNKNOWN |
| Does the hypothesis persist in advanced disease? | Mizuno GEO RNA/RRBS/histone series; WCDT; Abida SU2C | Separate treated/metastatic transport question; donor/site/treatment heterogeneity |
| Which cells express the programme? | Hirz GSE181294; independent source-qualified scRNA reference | Donor-aware localization; enriched sampling does not estimate native tissue fractions |
| Is spatial exclusion supported? | Kiviaho GSE278936, qualified HTAN processed spatial release | Region/patient-aware location, not merely low RNA |
| Can a newer source add a genuinely distinct question? | CELLxGENE/PCaDB/PRIDE/PDC/HTAN catalogues | Discover original studies and exact objects; a portal is not a cohort |

## Admission record

Each admitted object must carry study and originating-cohort IDs, accession/release, exact retrieval URL, checksum of actual full bytes, assay/platform, feature annotation/build, measurement units, processing history, access/redistribution terms, specimen/patient keys, clinical metadata sources, QC fields, overlap/exposure status and intended question. A partial stream hash is never a whole-file hash. A GEO archive named RAW can contain processed text; inspect payload semantics, not the filename alone. No FASTQ/BAM, IDAT or raw-MS reprocessing is authorised by this proposal.

Keep patient, biological specimen/focus, portion, aliquot, assay and reanalysis origin separate. One patient may have several metastases, modalities or technical replicates. Patient-code equality alone does not prove same-focus RNA–DNA pairing. Accept study-protocol adjacent-section support only under an explicitly reviewed evidence level, not as aliquot-level certainty.

Technical replicates may be combined only under a source-backed processed-data rule. Averaging intensities in a publication does not automatically authorise averaging deposited beta values. Never select a replicate on its association strength. The processed CPCG0398 expression value is reported as already averaged; avoid double aggregation.

## Clinical state

Retain literal values, source and canonical mappings for: age at diagnosis and at collection; diagnosis date; collection timing; clinical versus pathological TNM and their edition; primary/secondary Gleason patterns, sum and Grade Group; primary/metastatic/recurrent site; index-lesion status; treatment before sampling by modality; prior ICI, ADT, AR-pathway inhibitor, chemotherapy and radiotherapy; castration-sensitive/resistant designation with supporting evidence; recurrence/progression definitions and follow-up.

Use separate fields for `verified_treatment_naive`, `no_prior_ici_verified`, `no_systemic_therapy_documented`, `prior_treatment_verified` and `history_unknown`; do not collapse them to untreated/treated. Absence of an entry is not a negative history. A prostatectomy specimen is not the molecular state of a later metastasis. Grade, stage and sampling state are not interchangeable adjustment variables.

For the current B-P baseline retain its controlling proposed age/grade/purity definition until a reviewed freeze. Do not silently substitute ISUP for historical Gleason categories or diagnosis age for sampling age. For new biological models use source-supported clinically coherent coding, with collinearity/estimability checks and no p-value-based covariate selection.

## Core and optional views

RNA, methylation and identity/clinical data form the molecular backbone. CNA and mutation are core competing-explanation requests, not a requirement that every RNA patient has a complete all-omics record. miRNA enters only for a prespecified target relationship; protein/phosphoprotein only for covered analytes; ATAC only for measured compatible peaks. Do not label predicted protein, inferred cellular RNA or 450K domain overlap as measured protein, single-cell RNA or new whole-genome domain calls.

For each analysis report N for every modality, patient-linked intersections, same-specimen intersections, complete-view N, exclusions and missingness patterns. Compare assay-available and unavailable clinical subsets descriptively. New complete-case analyses identify a different eligible population; show that change rather than attributing differences to the added assay.

## Comparator policy

Keep prostate primary. Source cancers represented in A are the first clinical-context comparators; LUAD remains the registered secondary contrast whether or not it gives the largest separation. Additional contexts require a written pre-analysis biological rationale and finite list. Do not choose “hot” and “cold” cancers using the observed result.

Use harmonised annotation and source-compatible expression processing. Model identifiable technical variables without removing the cancer contrast. If platform/batch and cancer are perfectly confounded, acknowledge non-identifiability or use separate within-study contrasts; ComBat cannot supply the missing design. Gene-expression differences between organs include lineage differences and cannot be interpreted as a pure immune effect.

## Remaining source limitations

The review verified important primary-source leads, not every downloadable object in every portal. Exact final Arbet cohort overlap; PCaDB's original cohort roster; a qualified prostate PDC study; CELLxGENE's original publication/identity; many treatment fields; and most assay-specific eligible N remain UNKNOWN. The source manifest deliberately retains these failures or incomplete leads rather than treating an unsuccessful search as proof that a dataset does not exist.
