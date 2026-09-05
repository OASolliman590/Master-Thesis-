# LUAD secondary comparison: real metadata contract

6 September 2026, Cairo. **Source audit only.** The retained PRAD/LUAD contrast now has a concrete LUAD candidate manifest. No differential expression, methylation association, immune score, drug query, sample QC or biological validation was performed. The contrast remains secondary and tissue-confounded; these counts do not choose Paper B's primary.

## What was verified

The GDC `/files` response was filtered to open TCGA-LUAD Gene Expression Quantification and Methylation Beta Value records. All 1,311 returned file IDs were unique, and the returned count equalled the API's pagination total. The 997,384-byte response has SHA256 `3230295913d19f2345cc1b224434080a52f09b537a5023d2384c02b036d20336`. `inspect_luad.py` records the exact filters, requested fields, URL and checksum. This is a metadata query, not a full molecular-data download. [GDC API documentation](https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/).

The separately fetched status endpoint reported **Data Release 46.0, 10 August 2026**, API tag 8.5.0. This is the status observed during retrieval; it does not prove the creation release of every individual file. Per-file creation/update timestamps and advertised MD5 values are retained in the source response. Source-advertised MD5 values are not independently verified molecular-object checksums. [GDC status endpoint](https://api.gdc.cancer.gov/status).

| Metadata unit | STAR Counts RNA | SeSAMe 450K methylation |
|---|---:|---:|
| Files, all sample types | 601 | 507 |
| Primary-tumour files | 540 | 473 |
| Distinct primary-tumour sample UUIDs | 529 | 469 |
| Distinct primary-tumour case UUIDs | 517 | 458 |
| Cases with multiple primary sample UUIDs | 12 | 11 |
| Primary samples with multiple files | 11 | 4 |

The two modalities share **455 primary-tumour case UUIDs and 466 primary-tumour sample UUIDs**. There are 62 RNA-only and 3 methylation-only primary cases. These are separate case and sample intersections; counts alone do not establish RNA/DNA from the same portion or focus. The source also lists 150 SeSAMe 27K and 53 SeSAMe EPIC-v2 files; these are outside the current 450K-compatible manifest, not missing data mislabeled as 450K. One STAR file lacks a platform field, so eligibility is keyed to the verified workflow and specimen fields rather than silently discarding it for absent platform metadata.

## Bounded real-format evidence

A deterministic first file-ID-sorted RNA record among metadata-paired primary samples, `0052ae83-7ae5-470a-a125-5cd94a9fa9e9`, was inspected for its first 2,048 bytes. Its comment is `# gene-model: GENCODE v36`, followed by the same nine-field STAR layout as the existing PRAD example: gene ID/name/type, three count fields, TPM, FPKM and FPKM-UQ. This is direct header evidence for one LUAD file, not complete gene coverage or cohort-wide consistency. The prefix SHA256 is `dae5899b4014412d880dc526f7e539c0eeeb85e083bfd4b6af71d1e934fd72c6`; it must never be presented as the full file's checksum. [Actual public object](https://api.gdc.cancer.gov/data/0052ae83-7ae5-470a-a125-5cd94a9fa9e9).

GDC documents GENCODE v36 and STAR's augmented output, while warning that pipeline versions may vary among downloaded files. Matching a workflow name or header is not evidence of identical biological composition, library effects or assay QC. [GDC mRNA workflow](https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Expression_mRNA_Pipeline/).

## Consequences for the specifications

- Close the **LUAD metadata-acquisition subgate** of B E7 and C's patient-query source register. Retain the previously verified PRAD metadata ceiling of 497 cases; do not add the two counts into a final independent analysis N.
- Before any contrast, construct a source-backed case/sample/portion/aliquot map and one-patient selection rule. Multiple RNA files or methylation files for one sample cannot be treated as independent tumours or selected for favourable effects.
- Resolve actual object completeness/checksums, gene/probe coverage, missingness, processing differences and required covariates. The same tissue-type label across modalities does not establish matched cellular composition.
- Keep within-PRAD and PRAD/LUAD signatures separate. A lineage contrast cannot validate prostate ICI response or prove immune-cold tumour-cell silencing. The B-to-C query still needs a signed, discovery-only frozen definition; this audit creates no query.

The successful response bodies total **999,653 bytes**: 997,384 metadata + 221 status + 2,048 RNA prefix. No full molecular object, controlled data or software environment was downloaded. Raw metadata and the prefix stay in the local source bundle. Publish only retrieval records, aggregate coverage and candidate file-reference metadata. The scripts are evidence-audit utilities, not released production pipeline stages.
