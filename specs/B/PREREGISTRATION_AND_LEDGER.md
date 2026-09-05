# B preregistration proposal and evidence ledger

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
| Can replicate labels be averaged? | Biological meaning unknown. | rep1–rep4 titles in patient_multiplicity.tsv; no verified focus/technical interpretation. | No averaging until source evidence; blocking. |
| Are all eight genes measured externally? | Yes, all eight have unique gene-ID rows and 213/213 finite values in the complete object — verified audit fact. | [Full-expression audit](../../docs/research/B_readiness/GSE107299_full_expression_audit.json), 2026-09-05 20:44:59 UTC; 24,598 rows and full-object SHA256. Earlier partial audit remains provenance. | Close eight-row existence/finite-value subgate only; common annotation U, platform mapping and scale remain open. |
| Are purity and grade available for everyone? | 73 code candidates have WGS purity/grade/age; same-focus bridge unresolved. | [CPC2017 clinical API](https://www.cbioportal.org/api/studies/prad_cpcg_2017/clinical-data?clinicalDataType=SAMPLE&projection=DETAILED&pageSize=100000); clinical_candidate_mapping.tsv. | Verify specimen link and TCGA comparability; assess target population/precision. |
| Does promoter anticorrelation prove silencing? | No — scientific inference boundary. | [Guo 2023](https://doi.org/10.1016/j.cell.2023.05.028) plus bulk measurement design. | Preserve direction, CNA/composition/domain alternatives; no causal label. |
| Is rank transport established for this endpoint? | Sample-wise scoring has precedent; exact program/platform invariance unknown. | [Foroutan 2018](https://doi.org/10.1186/s12859-018-2435-4); ANALYSIS defines a custom score. | Common annotation universe/transport review gate. |
| Why these eight equal-weight genes? | Proposed literature-informed program, exact membership not approved. | ANALYSIS.md; targeted membership citations still to be completed. | Biological citation review before freeze; cannot call published signature. |
| What is the one primary result? | Proposed paired external Delta_R2 of two frozen ridge models. | ANALYSIS.md exact formula; [Ridge API](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html). | Requires precision target and independent review. |
| Does B validate C's gene selection? | No; C receives a discovery-only frozen query — design choice. | ANALYSIS/VALIDATION documents and handoff ledger. | CPC outcomes cannot select C input; exact thresholds unresolved. |

## Amendment and exclusion records

Each amendment contains `amendment_id`, UTC timestamp, author/reviewer, prior/new contract hashes, triggering evidence/source, whether TCGA/CPC outcomes were already accessed, effect on estimand/population/multiplicity, and confirmatory versus exploratory status. No overwriting old specifications or query versions. A post-test amendment cannot restore confirmatory status merely by adding a new date.

Each exclusion contains source patient/specimen IDs (restricted storage if needed), stage, reason code, rule version, modality and missingness/QC evidence. Publish aggregate counts and a permitted pseudonymous manifest. Record all candidate analyses and stopped branches so an unreported failed primary cannot become a “setup run.”

## Glossary and claim ceiling

Patient is the independent person; specimen/focus is a biological sample; assay/aliquot is a measurement source; reanalysis is a reused origin. Program score means relative bulk expression on the defined rank scale. Promoter association means an observational locus/program relationship. Incremental prediction means lower paired error relative to the baseline in the fixed external population. None is interchangeable with ICI response, drug efficacy, tumour-cell causality or a functional immune assay.
