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

### Amendment record: B-KIT-20260907-MODULES-v0.2

| Field | Recorded value |
|---|---|
| UTC timestamp | `2026-09-10T11:41:04Z` |
| Author / scope authority | User request dated 7 September 2026; standing integration authorization reconfirmed 10 September 2026 |
| Reviewer / integrator | Codex parent review, 10 September 2026 |
| Triggering source | User-supplied `B_kit_amendment_20260907.zip`, SHA-256 `28260ec713cef24805bca19b42d514f3ba70a5e9c4501b214daa233c62671058`; interpreted as proposed content and corrected against the canonical repository |
| Based-on commit | `a0eb7dbfa5beb2d64aa147f6c3d0ba44255a5e4c` |
| Prior contract hashes | `ANALYSIS.md` SHA-256 `2778e98cb512f4f069f417067500c26427878c1561b2000d8991bd37f7e2cb23`; `SECONDARY_PROGRAMS.md` SHA-256 `8c39acd9d3cc737a0d711193aedc832d953455539b9a807452be77520d44ee2c`; this ledger SHA-256 `c05b2c8a83b4748e6270c54bf94d44a393455feac6fa1974e0a093a8630e6ac4` |
| New contract hashes | `ANALYSIS.md` SHA-256 `be3d49bf112679e6b1f3623d5e2bedb4bfdec160e03ff598bb5c34c2ad86fa5a`; `SECONDARY_PROGRAMS.md` SHA-256 `3772b3e44b84afbece5eb6becbc5dfb7025e5e0748440b9ef5637432dad57957`; proposed registry SHA-256 `469bac01033a4946bcf605ee2b8a65cabe435054704af5ce8b375ebad33a9b75`; registry schema SHA-256 `0d027b587c55a755c00984feb4d903b2ec7315292d6ce600c4b29799b7a6520b` |
| Outcome-access state | No CPC-GENE outcome score, association or performance value was used for the amendment or registry membership. Prior header, identifier and coverage inspections remain acknowledged historical access, not prospective blindness. |
| Estimand effect | None. B-P external paired `Delta_R2` remains the single selected primary. |
| Population effect | None. TCGA-PRAD development and later locked CPC-GENE no-refit evaluation remain; LUAD is proposed secondary context only. |
| Multiplicity effect | None executable. The three planned secondary comparisons still require a valid frozen family/method; M0-M6 remain outside it and exploratory. |
| Membership / predictor effect | Proposed `P` is unchanged and still unfrozen. No M0-M6 member enters primary X; optional M1 promoter candidates remain out. |
| Classification | Specification-only amendment: planned-secondary registry plus exploratory/context scope. Not a score freeze, model run, real-cohort release or confirmatory promotion. |

The corrected v0.2 decision, human-readable module contract, registry/schema and B-G1 ticket are linked from [README.md](README.md). B-G1 may produce structural and annotation-coverage evidence only; it cannot alter this amendment record or close biological gates.

## Glossary and claim ceiling

Patient is the independent person; specimen/focus is a biological sample; assay/aliquot is a measurement source; reanalysis is a reused origin. Program score means relative bulk expression on the defined rank scale. Promoter association means an observational locus/program relationship. Incremental prediction means lower paired error relative to the baseline in the fixed external population. None is interchangeable with ICI response, drug efficacy, tumour-cell causality or a functional immune assay.

## Measurement grilling addendum — 6 September 2026

The [measurement checkpoint](../../docs/research/B_MEASUREMENT_CHECKPOINT.md) and its four source reports record verified answers, source fields/versions, audit methods and remaining choices for E1/E2/E4. Platform identity/v18 mapping availability, literal transcript-distance semantics and Qpure scale/TCGA field availability are resolved subquestions. Final U/Q, estimator comparability, exact specimen linkage, primary and precision are not resolved. These annotation and cellularity-value inspections are prior access; no molecular score/association was calculated. The earlier primary row describes the retained predictive proposal, not a decision selecting it over B-R.
