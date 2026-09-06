# B-R1 expression platform and historical annotation contract audit

Date: 6 September 2026 (Africa/Cairo). Status: factual research checkpoint; neither B-P nor B-R selected. No molecular score, association, sample-selection policy, or annotation policy was implemented. All artifacts remain outside the canonical repository.

## Finding

The public metadata identifies the two actual arrays and the authors' common **BrainArray custom CDF version 18** processing. Source-versioned annotation packages for **both** arrays are accessible without a patient-matrix download. Their nonmissing Entrez mappings share **24,937 candidate identifiers**, including all eight proposed genes. This is an annotation intersection, **not the final analysis universe U**: it has not been intersected with the actual processed CPC feature IDs or a frozen TCGA GENCODE-to-Entrez crosswalk. The previously verified CPC matrix has 24,598 feature rows; the different counts cannot be treated as interchangeable.

The legacy 73-patient source-linked subset remains a mixture of arrays: **17 HuGene 2.0 ST and 56 HTA 2.0**. It does not remove platform heterogeneity. Author metadata specifies use of `sva` for between-array correction but does not disclose the precise function, fitting design, protected covariates, or fitted parameters. That uncertainty remains material to either proposed primary.

## Patient/platform facts

The cached GSE107299 sample SOFT contains 213 GSM records with 213 distinct CPCG patient codes. These codes equal the patient-ID set in the existing full-expression header audit. The following counts derive only from metadata joins; they are not final eligible analysis counts. The per-record evidence is in `patient_platform_map.tsv`, including GSM, original platform, original batch, raw CEL URL, and separate paired-code/legacy-source flags.

| Original platform and batch | All 213 records | 210 methylation-paired code candidates | Legacy GSE84042 73 codes |
|---|---:|---:|---:|
| GPL16686 HuGene 2.0 ST / Batch1 | 10 | 9 | 8 |
| GPL17586 HTA 2.0 / Batch2 | 66 | 66 | 56 |
| GPL16686 HuGene 2.0 ST / Batch3 | 54 | 53 | 9 |
| GPL16686 HuGene 2.0 ST / Batch4 | 80 | 79 | 0 |
| GPL16686 HuGene 2.0 ST / Batch5 | 3 | 3 | 0 |
| Total | 213 | 210 | 73 |

Thus the paired-code set contains **144 HuGene + 66 HTA**. Platform and the published batch labels are confounded: every HTA record is Batch2, and the other batches are HuGene. A regression cannot interpret their effects as separately identified from these labels alone. This is a design implication of the table, not evidence of a measured molecular platform effect.

GSM2981373 / CPCG0398 is a single current GSM on GPL17586, Batch2, with CEL filename E1547. The series describes an already averaged technical replicate in its processed column. This does not create a 214th patient or establish a new replicate-selection policy. Biological specimen/focus and purity gates remain those documented in the prior specimen-resolution audit. [GSE107299](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107299), [GSM2981373](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM2981373).

## Author processing versus manufacturer annotation

All 213 sample records contain the same `!Sample_data_processing` provenance: R 3.4.3; modified `affy` 1.48.0 obtained from BrainArray; RMA on raw intensities; custom CDF v18 mapping to Entrez IDs for HTA 2.0 and HuGene 2.0 ST; `sva` 3.24.4 for batch effects between arrays. This establishes microarray RMA processing, not RNA-seq TPM. It does not recover the executable batch-correction specification. In particular, the package name alone does not prove a particular ComBat call, outcome protection, or training-only fitting. Future preprocessing must preserve the historical source processing as provenance rather than silently claiming it satisfies a new train/test design. Exact transformed scale still belongs in the agreed input contract. [Original sample processing record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM2981373).

The cached full family SOFT supplies original GPL tables, without any new full-family retrieval:

| Source | Verified annotation provenance | Actual cached fields and consequences |
|---|---|---|
| GPL16686 | HuGene 2.0 ST transcript/gene version; description names `HuGene-2_0-st-v1.na33.hg19.transcript.csv`, 15 Nov 2012; GEO public 14 Feb 2013, last update 21 Feb 2020 | 53,981 rows. Fields `ID`, `RANGE_STRAND`, `RANGE_START`, `RANGE_END`, `total_probes`, `GB_ACC`, `SPOT_ID`, `RANGE_GB`. This table has no explicit Entrez column. That is a field limitation, not evidence that the eight genes are absent. |
| GPL17586 | HTA 2.0 transcript/gene version; r1 library, hg19/GRCh37; NetAffx build 34, annotation date 15 Oct 2013; create date 22 Jan 2014; GEO public 20 Aug 2013, last update 5 May 2021 | 70,753 rows. `gene_assignment` contains compound transcript entries with Entrez in the fifth ` // ` field and alternatives separated by ` /// `. Exactly 54 vendor rows match at least one of the eight target Entrez IDs using that field; this is not 54 specific oligonucleotide probes. |

[GPL16686](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL16686), [GPL17586](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL17586). Neither manufacturer table is a direct map from the authors' custom-CDF processed identifiers. Joining vendor transcript-cluster IDs to processed Entrez IDs without the historical custom annotation would be unsupported. `vendor_platform_inspection.json` preserves headers, provenance and the target-matching evidence.

## Selectable historical annotation evidence; selection not made

The original [BrainArray version 18 ENTREZG release page](http://brainarray.mbni.med.umich.edu/Brainarray/Database/CustomCDF/18.0.0/entrezg.asp) lists both arrays and links their CDF, probe and annotation packages. HTTPS timed out; public HTTP returned the release and small annotation packages. Checksums below identify downloaded bytes; they are not authenticated signatures or the unreported checksums of the exact files originally used by the authors.

| Annotation package | Bytes | Mapping rows / nonmissing distinct Entrez IDs | SHA-256 |
|---|---:|---:|---|
| `hta20hsentrezg.db_18.0.0.tar.gz` | 814,118 | 26,194 / 26,191 | `e3e2e8f24951e6f067f08417e9677b571c58dc0832a5d7d3c11dfdf0b121add1` |
| `hugene20sthsentrezg.db_18.0.0.tar.gz` | 781,983 | 25,088 / 25,087 | `4edaefa017ed2bd2c82aeeed52c25bdc781170d636c2b65b26e7c2f10350d928` |

Direct source packages: [HTA v18](http://brainarray.mbni.med.umich.edu/customcdf/18.0.0/entrezg.download/hta20hsentrezg.db_18.0.0.tar.gz), [HuGene v18](http://brainarray.mbni.med.umich.edu/customcdf/18.0.0/entrezg.download/hugene20sthsentrezg.db_18.0.0.tar.gz).

Both package DESCRIPTION files specify version 18.0.0 and Artistic-2.0; both were packaged 29 Jan 2014. Their embedded SQLite metadata identifies `HUMANCHIP_DB` schema 2.1, central identifier ENTREZID, taxon 9606, Entrez source date **2013-Sep12**, Ensembl source date **2013-Sep3**, and a UCSC hg19 source dated 2010-Mar22. The inspection used SQLite read-only access; no R package was installed or executed. Only DESCRIPTION and SQLite members were extracted into explicit owned paths; `package_member_inventory.json` records all archive members and extraction status.

HTA has three NULL mappings (`100996402_at`, `101928749_at`, `101928757_at`); HuGene has one (`101928749_at`). All rows have `is_multiple=0`, which does not establish genomic probe specificity. The nonmissing Entrez sets intersect at 24,937; HTA-only 1,254 and HuGene-only 150. The local candidate-universe TSVs are reproducible annotation outputs, not approved U.

The [GEO BrainArray platform GPL19803](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL19803), also explicitly linked by GPL16686 as an alternative representation, identifies HuGene ENTREZG BrainArray 18.0.0. Its [description mapping](https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL19nnn/GPL19803/suppl/GPL19803_hugene20st_Hs_ENTREZG_desc.annot.txt.gz) has 25,088 mappings, including `101928749`, which is NULL in the package database. Therefore stripping `_at` or trusting the description table without a recorded precedence/missing-mapping rule would conceal a source discrepancy. No resolution policy was chosen.

## Eight-gene coverage and specificity boundary

Each of the eight proposed genes maps to exactly one `${Entrez}_at` probeset in **each** v18 annotation database. The HuGene [released probe-sequence table](https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL19nnn/GPL19803/suppl/GPL19803_hugene20st_Hs_ENTREZG_probe_tab.txt.gz) supplies 459,819 probe rows over 25,088 probesets, with probe coordinates, sequence, interrogation position and target strandedness.

| Proposed gene | Entrez ID | HuGene v18 25-mer probe rows |
|---|---:|---:|
| HLA-A | 3105 | 24 |
| HLA-B | 3106 | 12 |
| HLA-C | 3107 | 14 |
| B2M | 567 | 12 |
| TAP1 | 6890 | 27 |
| TAP2 | 6891 | 33 |
| PSMB8 | 5696 | 22 |
| PSMB9 | 5698 | 16 |

None of these target sequences occurs in a different probeset within the released HuGene table. This is only an exact sequence-duplication check. No genome alignment, HLA allele/SNP evaluation or cross-hybridization validation was performed; HTA probe sequences were not retrieved. The result establishes historical annotation coverage, not biological specificity or approval of the eight-gene score. Probe-table SHA-256: `f6df0dd3c252cd28283bac818fb1b35a4d94ce65451a75bb96bd5d6dd2e98af3`.

## Grilling ledger and remaining gates

| Question | Evidence-supported answer | Gate / proposed next contract requirement |
|---|---|---|
| Can the two expression assays be identified per record? | Yes: all 213 GSMs, with published platform and batch labels. | Metadata mapping can close; preserve source fields, do not infer specimen identity from array identity. |
| Is manufacturer annotation the processed feature dictionary? | No: authors explicitly used custom CDF v18 for both arrays. | Carry raw feature ID, historical Entrez ID, platform and annotation-source hash separately. |
| Is a source-versioned candidate Entrez universe available? | Yes: both original v18 databases inspected. | Annotation-source availability can close; final U remains open. |
| Can missing mappings be filled by suffix stripping? | Sources disagree for at least HuGene `101928749`. | Retain NULL/conflict status; choose and freeze precedence only in an approved annotation policy. |
| Are all eight annotated on both arrays? | Yes, one v18 probeset per gene on each. | Mapping coverage can close; specificity/score approval cannot. |
| Does the 73-source-linked subset remove assay differences? | No: 17 HuGene and 56 HTA. | Any cohort policy must retain platform/batch uncertainty and evaluate transport implications. |
| Is original SVA fitting recoverable here? | Package/version and broad purpose only. | Function/design/parameters and transformed-scale justification remain unresolved; avoid claiming protected covariates or independent preprocessing. |
| Can this define final U without a matrix rerun? | Not from counts alone. | Obtain/retain only a verified processed feature-ID list from existing approved artifacts; intersect with a versioned TCGA crosswalk, record losses/duplicates/retired IDs. No such intersection was run here. |
| Are historical annotations biologically current and specific? | Versioned, not guaranteed current or specific. | Preserve original IDs; any current-ID update, alias resolution or HLA-specific probe assessment needs a separately approved source and rule. HTA sequence evidence remains open. |

These are requirements/options for the future gene-ID mapping contract, not implementation or a choice between predictive B-P and replicated-association B-R. Clinical covariate/specimen gates and the prohibition on using the mislabeled portal WGS agreement field as purity remain unchanged.

## Access, receipts and limitations

New successful download bodies total **8,608,045 bytes**, below the 15,000,000-byte task cap. Largest object: HuGene probe table, **6,755,578 bytes**, below 10,000,000. `requests.json` records exact URL, timestamp, response type, last-modified, size, SHA-256 and the failed HTTPS attempt. No full patient matrix or controlled-access data was downloaded. The pre-existing 16,322,790-byte compressed family SOFT was read locally for metadata/platform tables only; it is not a new download. No CEL file, full CDF, or HTA probe archive was retrieved. No environment or source data was changed.

`hash_register.json` records all local artifacts and reused source hashes; `metadata_summary.json`, `annotation_inspection.json`, and `package_member_inventory.json` supply machine-readable evidence. Scripts only inspect public metadata/annotation and record provenance. Package metadata states Artistic-2.0, but no blanket redistribution conclusion was made for GEO supplementary sequences, manufacturer annotations, or patient-level metadata. Raw downloaded content, mapping exports and per-patient tables remain outside Git. The general BrainArray methods page was inspected only as supplementary context; no separate SNP-filtering package was assumed to have been used by the authors.
