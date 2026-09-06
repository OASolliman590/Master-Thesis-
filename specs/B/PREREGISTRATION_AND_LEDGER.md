# B preregistration proposal and evidence ledger

**Primary decision, 6 September 2026:** B-P external prediction improvement is selected as the one Paper B primary. Selection fixes the external Delta_R2 estimand but does not complete the preregistration freeze fields below. [Decision record](../../docs/decisions/B_PRIMARY_BP_20260906.md).

**Source correction, 6 September 2026:** the CPC portal `WGS_BASED_PURITY_ESTIMATION` field matches original WGS/OncoScan SNP-call agreement, not tumour purity. It must not populate a purity covariate or count toward purity availability. Genuine cellularity alternatives require their own method/specimen/scale validation. [Verified correction](../../docs/research/B_PURITY_FIELD_CORRECTION.md).

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** No preregistration tag is created by this document. Current table/metadata audits are prior knowledge, not unseen-data claims.

## Freeze record to complete before fitting

Record dated scientific approval, repository commit, protocol alignment, exact patient population/specimen rule, eight-gene membership and supporting citations, U and Q hashes, annotation/mask releases, baseline definition and purity comparability, full QC/eligibility rules, alpha grid/folds/seeds, primary Delta_R2/interval and minimum meaningful effect/precision target. Record planned missingness summaries, secondary families and C-query selection separately. Unfilled fields are blocking decisions, not defaults silently adopted by code.

List all prior dataset access and observed results, including the historical six-gene partial inspection, the later complete eight-gene coverage audit (no Y score computed), clinical candidate coverage and any inherited historical analyses. Hash historical outputs and distinguish their scientific reuse from code reuse. Do not claim prospective blindness for outcomes already inspected. The independent reviewer must decide whether any inherited information requires a separate locked holdout or an explicitly retrospective analysis.

Freeze two dated boundaries: (1) scientific/analysis contract before modelling; (2) final TCGA-fitted model and transforms before external endpoint/error evaluation. Store eligibility mask construction rules before external scoring. A positive-effect hypothesis does not authorise one-sided selection or sign filtering. Report all primary results and exclusions regardless of direction.

## Grilling ledger

Source-reported facts, locally verified metadata, proposed choices and unresolved claims must remain distinguishable. Evidence retrieval/audit date: 2026-09-05, unless a linked artifact says otherwise.

| Question | Answer/classification | Source / field / verification | Spec impact and status |
|---|---|---|---|
| Is 210 the external primary n? | No; metadata-paired patient-code count — verified fact, eligibility unknown. | [GSE107298](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107298), [GSE107299](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107299); actual processed headers and B_readiness.md. | n must be derived after specimen/covariate/QC gates; open. |
| Are the older series extra validation? | Explicit reanalysis provenance; 300 edges, not 300 added patients — verified fact. | B_readiness/reanalysis_edges_resolved.tsv and [GSE84493](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE84493). | Collapse origin duplicates, retain provenance; resolved at edge level only. |
| Can replicate labels be averaged? | Physical barcode matching now establishes technical-replication provenance for300 assays, with94 unresolved; one replicate suffix changed. | [Original source resolution](../../docs/research/B_SPECIMEN_RESOLUTION.md), Shiah S1 physical slide/array and patient joins. | Technical provenance does not choose processed-beta aggregation or establish RNA–DNA focus identity. Freeze a source-backed policy; no suffix-only averaging. |
| Are all eight genes measured externally? | Yes, all eight have unique gene-ID rows and 213/213 finite values in the complete object — verified audit fact. | [Full-expression audit](../../docs/research/B_readiness/GSE107299_full_expression_audit.json), 2026-09-05 20:44:59 UTC; 24,598 rows and full-object SHA256. Earlier partial audit remains provenance. | Close eight-row existence/finite-value subgate only; common annotation U, platform mapping and scale remain open. |
| Are purity and grade available for everyone? | The earlier73-code portal route has age/grade, but its mislabeled WGS field is SNP-call agreement and is prohibited as purity. Original-table cellularity options and a stronger study-protocol bridge are now documented; exact policy remains open. | [CPC2017 clinical API](https://www.cbioportal.org/api/studies/prad_cpcg_2017/clinical-data?clinicalDataType=SAMPLE&projection=DETAILED&pageSize=100000); clinical_candidate_mapping.tsv. | Verify specimen link and TCGA comparability; assess target population/precision. |
| Does promoter anticorrelation prove silencing? | No — scientific inference boundary. | [Guo 2023](https://doi.org/10.1016/j.cell.2023.05.028) plus bulk measurement design. | Preserve direction, CNA/composition/domain alternatives; no causal label. |
| Is rank transport established for this endpoint? | Sample-wise scoring has precedent; exact program/platform invariance unknown. | [Foroutan 2018](https://doi.org/10.1186/s12859-018-2435-4); ANALYSIS defines a custom score. | Common annotation universe/transport review gate. |
| Why these eight equal-weight genes? | Proposed literature-informed program, exact membership not approved. | ANALYSIS.md; targeted membership citations still to be completed. | Biological citation review before freeze; cannot call published signature. |
| What is the one primary result? | Selected paired external Delta_R2 of two frozen TCGA ridge models evaluated once in CPC-GENE. | Decision record; ANALYSIS.md exact formula; [Ridge interface](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html). | Estimand selected; population, feature, precision and full lock/review fields remain open. |
| Does B validate C's gene selection? | No; C receives a discovery-only frozen query — design choice. | ANALYSIS/VALIDATION documents and handoff ledger. | CPC outcomes cannot select C input; exact thresholds unresolved. |

## Amendment and exclusion records

Each amendment contains `amendment_id`, UTC timestamp, author/reviewer, prior/new contract hashes, triggering evidence/source, whether TCGA/CPC outcomes were already accessed, effect on estimand/population/multiplicity, and confirmatory versus exploratory status. No overwriting old specifications or query versions. A post-test amendment cannot restore confirmatory status merely by adding a new date.

Each exclusion contains source patient/specimen IDs (restricted storage if needed), stage, reason code, rule version, modality and missingness/QC evidence. Publish aggregate counts and a permitted pseudonymous manifest. Record all candidate analyses and stopped branches so an unreported failed primary cannot become a “setup run.”

## Glossary and claim ceiling

Patient is the independent person; specimen/focus is a biological sample; assay/aliquot is a measurement source; reanalysis is a reused origin. Program score means relative bulk expression on the defined rank scale. Promoter association means an observational locus/program relationship. Incremental prediction means lower paired error relative to the baseline in the fixed external population. None is interchangeable with ICI response, drug efficacy, tumour-cell causality or a functional immune assay.

## Measurement grilling addendum — 6 September 2026

The [measurement checkpoint](../../docs/research/B_MEASUREMENT_CHECKPOINT.md) and its four source reports record verified answers, source fields/versions, audit methods and remaining choices for E1/E2/E4. Platform identity/v18 mapping availability, literal transcript-distance semantics and Qpure scale/TCGA field availability are resolved subquestions. Final U/Q, estimator comparability, exact specimen linkage, primary and precision are not resolved. These annotation and cellularity-value inspections are prior access; no molecular score/association was calculated. The earlier primary row describes the retained predictive proposal, not a decision selecting it over B-R.
