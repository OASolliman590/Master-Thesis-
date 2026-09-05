# Paper B readiness: specimen multiplicity, clinical fields and real table formats

**Correction, 6 September 2026:** the portal field previously interpreted below as WGS tumour purity is an SNP-call agreement measure. It is quarantined from purity adjustment. The original-table audit provides a stronger 73-patient study-protocol bridge and separate Qpure cellularity candidates; individual specimen linkage and final eligibility remain unresolved. [Correction](B_PURITY_FIELD_CORRECTION.md), [source audit](B_SPECIMEN_RESOLUTION.md). Historical source counts below retain their original route-specific scope.

Audit: 5 September 2026. This is an outcome-independent data-readiness check, not production analysis or approval of the previously proposed eight-gene endpoint. Read with [the paired-cohort/mechanism audit](B_paired_prostate.md).

**Update:** the dated full-expression addendum at the end supersedes the historical partial-scan limit for the eight proposed genes. Earlier bounded-audit statements below are preserved as the original audit record; E1 is only partially resolved. The factual results below supersede any earlier assumption that metadata intersections alone establish an analysis-ready external cohort.

## Decision for the proposed endpoint

**External incremental prediction of a fixed antigen-presentation expression score remains scientifically definable but is not ready to run as a fully adjusted primary endpoint.** Both modalities contain the 210 candidate CPC-GENE patient codes in their actual processed-table headers. However, the inspected public clinical source supplies candidate grade/purity links for only73 of those codes, and the tumour-focus linkage has not been verified. Full candidate CpG coverage, expression background, methylation replicate treatment and cross-platform score definition remain unresolved. This is a precise readiness boundary, not evidence that the endpoint cannot work.

An alternative using a prespecified smaller covariate-complete validation subset would change the target population and precision. It must be chosen before inspecting associations and justified as such. No estimate of adequate power or final N is established here. The eight-gene module is still a proposal; failure to verify two genes within a bounded file prefix must not trigger replacing them with successful genes.

## Actual work and provenance

Public requests and table-prefix extraction ran successfully on AIU with system Python3 in `/home/omics/projects/ici_thesis_pipeline/planning/2026-09-05/B_readiness`. No shared environment, previous run, queue or production model was modified. Local standard-library scripts performed metadata joins and format summaries; equivalent scripts are supplied for reproducibility. Source bodies total52,286,278 bytes across this bounded audit, including24MB of a partially streamed expression object; no complete object exceeded25MB. No controlled data or huge whole-cohort methylation matrix was downloaded.

[fetch_log.json](B_readiness/fetch_log.json) records exact URLs, byte counts, SHA256 hashes and successful retrieval timestamps. The two compressed GEO prefixes and the24MB expression scan are explicitly **partial**; their hashes are not full-file checksums. The target scan retained only candidate rows, not the24MB stream. Failed article requests are preserved as errors. The locally saved Nature HTML is a short access response and must not be treated as article text.

Source interfaces: [GEO download documentation](https://www.ncbi.nlm.nih.gov/geo/info/download.html), [GDC files/data API documentation](https://docs.gdc.cancer.gov/API/Users_Guide/Getting_Started/), [cBioPortal REST documentation](https://docs.cbioportal.org/web-api-and-clients/). Scripts: [audit.py](B_readiness/audit.py), [fetch_more.py](B_readiness/fetch_more.py), [target_check.py](B_readiness/target_check.py), [inspect_tables.py](B_readiness/inspect_tables.py), [resolve.py](B_readiness/resolve.py).

## Multiplicity resolved to provenance, not to selected specimens

The394 GSE107298 methylation records represent286 distinct CPCG codes. Multiplicity is199 singletons,70 doubles,13 triples and4 quadruples. Their title suffixes comprise286 `rep1`,87 `rep2`,17 `rep3` and4 `rep4` records. The210 codes paired to expression comprise288 methylation records:149 singletons,48 doubles,9 triples and4 quadruples. No record has been chosen on clinical outcomes, expression, correlation or fit quality.

All300 explicit reanalysis edges target300 distinct older GSM accessions:160 belong to GSE83917 and140 to GSE84493. The140 newly resolved edges have matching CPCG codes in original records. Thus the discrepancy is explained by patient multiplicity and reanalysis provenance, rather than300 new patients. Remaining94 current records have no explicit reanalysis relation. Their absence of that field alone does not establish independence.

The `rep` label and shared patient code do not establish whether these are technical assays, portions, extraction repeats or different tumour foci. The supplied metadata does not resolve that biological distinction. Preserve every record until a source-grounded aggregation/selection policy is frozen. [GSE107298](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107298), [GSE84493](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE84493), [original example GSM2237935](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM2237935).

Exports: [patient_multiplicity.tsv](B_readiness/patient_multiplicity.tsv) has286 rows and modality membership; [reanalysis_edges_resolved.tsv](B_readiness/reanalysis_edges_resolved.tsv) has300 original/current links; [readiness_summary.json](B_readiness/readiness_summary.json) contains independent counts. Original metadata files remain available for verification.

## Coverage and real-format evidence

| Check | Verified fact | Remaining boundary |
|---|---|---|
| TCGA specimen pairing | `TCGA-HC-A6AO-01A`; RNA aliquot `TCGA-HC-A6AO-01A-11R-A30B-07`, DNA aliquot `TCGA-HC-A6AO-01A-11D-A30F-05` | Same primary sample and portion11, different analytes; one format example does not establish whole-cohort QC |
| TCGA RNA | Actual STAR file has GENCODEv36 comment, header, four `N_` summary rows and60,660 distinct gene IDs; counts, TPM, FPKM and FPKM-UQ are separate columns. All eight proposed symbols occur with finite TPM; no missing gene-row TPM in this file | Strip summary rows correctly; freeze gene-ID/symbol handling and chosen abundance column |
| TCGA methylation | Actual file has **no header**,486,427 distinct IDs,417,183 finite betas,69,244 `NA`; finite range0.00586–0.99417. Includes482,421 `cg` IDs,3,091 `ch` IDs and other probe classes | An importer must retain the first probe. Freeze eligible CpGs and missingness policy; a single sample does not define cohort missingness |
| CPC-GENE methylation processed prefix |394 beta columns and394 adjacent detection-P columns; all286 codes and210 paired codes occur in header. Header has788 fields, each checked data row789: leading probe-ID header label is omitted | Reconstruct the missing first label explicitly. Preserve the deposited misspelling `_Dectection_Pval`. Detection P is not another beta/sample |
| CPC methylation feature prefix |77 complete probe rows checked; finite beta range0.0346–0.9482 | This does not establish full CpG count, program-promoter coverage or missingness across the matrix |
| CPC expression processed header | Seven annotation columns (`GeneID`, `Symbol_UCSC`, `Name_UCSC`, `Chr_UCSC`, `Start_UCSC`, `End_UCSC`, `RefSeq_UCSC`) plus213 distinct patient columns; all210 paired codes present | Declared Entrez custom-CDF/RMA processing is different from TCGA RNA-seq; reference coordinates/gene background need pinning |
| Proposed expression program | Within24MB compressed prefix/18,277 complete feature rows, HLA-A/B/C, B2M and PSMB8/9 were located, each with no missing value across213 columns | TAP1/TAP2 were not reached before the cap; **not proven absent**. Full common gene background and all eight features remain unverified |

Exact TCGA objects: [RNA UUID a4980c9c-6c37-46da-8db3-c60a1c29081f](https://api.gdc.cancer.gov/data/a4980c9c-6c37-46da-8db3-c60a1c29081f), [methylation UUID9cebe5e9-f133-479a-b0f6-e91d8b06ab38](https://api.gdc.cancer.gov/data/9cebe5e9-f133-479a-b0f6-e91d8b06ab38). RNA SHA256 `8339cb0b1bf80236a7fff6ec9ee18b5d8779a35fa32adf4f43c20e2495fd6d2c`; methylation SHA256 `11d9fa63a4b9b69b9131ebdb535501fe221751cfe172b8295526d70003d40cf7`. The API metadata includes file sizes, official MD5s and workflow revisions.

GEO directory listings report the methylation processed object at1.3GB and expression at31MB. These exceeded the audit’s complete-object limit; only bounded prefixes were streamed. The linked Figshare methylation RDS is902,658,853 bytes and was not downloaded; its metadata establishes a public CC-BY4.0 object, not missing clinical coverage. [Methylation directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107298/suppl/), [expression directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107299/suppl/), [Figshare DOI10.6084/m9.figshare.16574486.v1](https://doi.org/10.6084/m9.figshare.16574486.v1).

## Public clinical coverage and overlap

The original [Fraser et al., Nature2017, DOI10.1038/nature20788](https://doi.org/10.1038/nature20788) is represented by public cBioPortal study `prad_cpcg_2017`. Its current study metadata describes477 samples pooled from CPC-GENE and other projects, including TCGA. Actual clinical IDs include205 `TCGA` and130 `CPCG` entries. Importing this entire study as an independent CPC validation cohort would contaminate the design with discovery patients.

The130 CPC entries use `CPCG####-F1` as both patient/sample IDs. Removing only the exact `-F1` suffix provides73 candidate code matches to the210 paired GEO codes. Raw exact string matching correctly yields zero; the derived mapping is explicit in [clinical_candidate_mapping.tsv](B_readiness/clinical_candidate_mapping.tsv). It is a patient-code bridge, not proof that the GEO methylation/expression assays came from this same focus. No ambiguous substring or approximate matching was used.

| Public field | Nonmissing candidate coverage /210 | Interpretation |
|---|---:|---|
| AGE |73|137 lack coverage through this inspected source |
| GLEASON_SCORE |73|Original string patterns, e.g. `3+4`; do not equate total7 with one Grade Group |
| WGS_BASED_PURITY_ESTIMATION |73|**Incorrect prior biological interpretation:** original WGSvsOS SNP-call agreement; quarantined from purity use. |
| CELLULARITY |70|Histologic tumour-content field, expressed in percent in inspected examples; three of73 lack it |
| PLOIDY |18|Ploidy is not locus-specific copy number |
| Candidate joint grade + pathologic cellularity |70|Before focus verification and molecular QC; the mislabeled WGS field adds no purity evidence. |

The public molecular-profile endpoint lists the study’s mutation profile; its study metadata reports zero CNA-profile samples. Therefore no gene-level CNA adjustment source is established by this cBioPortal route. This is not a claim that public CPC-GENE CNA data do not exist elsewhere. The original publication’s supplementary tables and PRAD-CA derived-data migration are possible next source checks, not verified missing-field replacements. [cBioPortal study API](https://www.cbioportal.org/api/studies/prad_cpcg_2017), [clinical sample API](https://www.cbioportal.org/api/studies/prad_cpcg_2017/clinical-data?clinicalDataType=SAMPLE&projection=DETAILED&pageSize=100000), [molecular profiles](https://www.cbioportal.org/api/studies/prad_cpcg_2017/molecular-profiles).

For the single TCGA example, GDC diagnosis supplies Gleason7 with primary pattern4/secondary3 and age_at_diagnosis19,298 days. No whole-TCGA clinical completeness count or common-purity method has been established by this bounded sample check. [Actual GDC case](https://api.gdc.cancer.gov/cases/4045f40b-d42a-4598-9ee2-0d371a776d3f?expand=diagnoses,demographic,samples.portions.slides,samples.portions.analytes.aliquots).

## Design recommendations, separate from facts

1. Freeze the scientific endpoint only after the missing-feature and source gates below. If incremental R² is chosen, train both covariate-only and covariate-plus-methylation models within TCGA development folds, lock both, and compare their predictions on exactly the same external patient set. Do not recalibrate to CPC outcomes or choose the better-performing subset.
2. A fixed within-sample rank module is one proposed RNA-seq/array transport strategy; its common background, ties and absent-feature rule must be explicit. Rank scoring does not prove absolute repression or remove cell-mixture confounding. No method is approved solely because it yields a convenient R².
3. Keep purity and gene copy number conceptually distinct. A baseline with grade and one prespecified purity variable can be proposed without claiming adjustment for CNA; a mandatory CNA-adjusted endpoint remains blocked until a real compatible source is joined.
4. Resolve replicate biology before selecting or averaging methylation columns. Detection-P and IDAT provenance are useful QC evidence, but no replicate should be chosen using outcome, gene recovery or association significance.
5. Retain the Guo2023 counterexample and both methylation directions from the earlier audit. This readiness exercise does not establish causal tumour-cell repression or clinical ICI benefit.

## Exact remaining gates for the B spec

- **E1 expression universe:** verify TAP1/TAP2, complete common annotated gene background and cross-platform endpoint definition. The current partial check establishes six measured candidates only.
- **E2 CpG universe:** pin compatible probe/gene annotation; quantify program promoter/domain probe coverage, masked/NA probes, detection-P criteria and common eligible features in full matrices.
- **E3 independent specimen rule:** resolve meaning of methylation `rep1–rep4`, possible focus/portion differences and relationship to the processed expression sample; implement one patient contribution without outcome selection.
- **E4 baseline covariates:** resolve the clinical `-F1` bridge; obtain grade/purity for137 currently uncovered pairs or predeclare a limited target population. Match purity definition and scale across cohorts. Verify full discovery covariate completeness.
- **E5 optional CNA:** no verified gene-level CPC CNA table joined today; do not claim this adjustment or substitute ploidy for it.
- **E6 inference contract:** declare primary module, estimand, common external denominator, missing-data policy, frozen preprocessing, independent-split design and precision assessment. No proposed design can promise positive incremental value or adequate power.

Proceed to a **conditional full specification kit** with these executable acceptance gates. It is premature to label the external fully adjusted endpoint implementation-ready or preregister an analysis-ready N of210.


## Addendum — complete external expression coverage, 5 September 2026

A subsequent root-orchestrated AIU audit retrieved the **complete** [GSE107299 processed expression object](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107299/suppl/GSE107299_Matrix_processed_data.tsv.gz) at **2026-09-05 20:44:59.490284 UTC**. The saved [full-expression audit](B_readiness/GSE107299_full_expression_audit.json) reports 32,357,821 compressed bytes, matching the HTTP Content-Length, 24,598 feature rows, 213 sample columns and zero malformed rows. Its full-object SHA256 is `09d866ce89adb7122879354a523ae0c1fdac03572c555a2d647b64a35c342f2b`. This is a complete-object checksum, distinct from the earlier retained compressed-prefix hashes. The complete expression matrix was **not retained**, and no Y score, patient association or prediction was computed in this audit.

All eight proposed program genes occur as single gene-ID rows and have finite values in **213/213 samples each**: HLA-A (3105), HLA-B (3106), HLA-C (3107), B2M (567), TAP1 (6890), TAP2 (6891), PSMB8 (5696) and PSMB9 (5698). The former TAP1/TAP2 uncertainty reflected the bounded stream ending before those rows; it was never evidence of absence. These locally verified row counts supersede the earlier six-gene coverage finding, while preserving its historical provenance.

**E1 remains open in part.** Eight-row presence and finite-value coverage are now resolved for this deposited expression matrix. This does not yet establish the complete common TCGA/CPC annotation universe, cross-platform gene mapping and probe specificity, biological approval of the proposed module, or transportability of its custom rank scale. It also does not resolve methylation promoter coverage, rep/focus semantics, clinical linkage, comparable purity or primary-endpoint precision. The earlier audit's 52,286,278-byte total and complete-object cap describe that earlier bounded job only; the later full-expression transfer is a separate documented audit. No final primary validation n or model readiness follows from this update.
