# Riaz clinical evidence review — 26 Oct 2026

Scope: public primary-source evidence for outcome definition, specimen timing, and exclusions in the Riaz GSE91061 ingestion worksheet. This review did not inspect expression values or execute source code, and it does not resolve or sign worksheet items. Patient-level names, rows, and sample accessions are omitted. Worksheet item identifiers below are SHA-256 prefixes computed from the private item IDs.

## Documented source facts

The primary report describes CA209-038 / NCT01621490: nivolumab was given at 3 mg/kg every two weeks; radiographic response was assessed approximately every eight weeks, progression was generally confirmed by a repeat CT about four weeks later, and response is best overall response unless specified otherwise. The assessment criterion was RECIST v1.1. Biopsies were taken 1–7 days before first dose and again at the same site on cycle 1 day 29, within days 23–29. These are protocol windows, not participant-specific biopsy dates. [Riaz et al., Cell 2017, article and STAR Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC5685550/).

Official GEO describes 109 RNA-seq specimens from 65 patients, 51 pretreatment and 58 on-treatment. [GSE91061 record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061). The GEO sample-level `response` field is a corroborating label. Under the approved field-map/source-role policy, the author clinical table's `BOR` is the source of record. In the three outcome items, the author value is `NE` and GEO's corroborating value is `UNK`:

| Worksheet category | Hashed item ID | Evidence |
|---|---|---|
| `OUTCOME_LABEL_DISAGREEMENT` | `I-0c01e94e1428c298b680` | On-treatment; author `BOR=NE`; GEO corroboration `UNK` |
| `OUTCOME_LABEL_DISAGREEMENT` | `I-0f3a9ce2c18297d65dcb` | Baseline; author `BOR=NE`; GEO corroboration `UNK` |
| `OUTCOME_LABEL_DISAGREEMENT` | `I-47f3dec5f3e9b814f6da` | Baseline; author `BOR=NE`; GEO corroboration `UNK` |

The frozen shared acquisition ontology maps `NE`/unknown to not evaluable for ORR, requires discrepancy handling without overwriting source labels, and requires evaluable objective-response mapping for `A_BASELINE_BIO` and A-P2. Paper A's endpoint ontology gives the same null/evaluability rule. Thus neither raw code supports a positive or negative ORR label. [Shared endpoint ontology](../../specs/A_DATA_ACQUISITION_VALIDATION/ENDPOINT_ONTOLOGY.md); [Paper A endpoint ontology](../../specs/A/ENDPOINT_ONTOLOGY.md). The public [GEO family SOFT object](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE91nnn/GSE91061/soft/GSE91061_family.soft.gz) is the primary GEO record for those raw specimen annotations.

The pinned author script [`TableS6.A.R`](https://raw.githubusercontent.com/riazn/bms038_analysis/137111c38a32f8626ee6a436e14ac667bd31b1e7/rnaseq/TableS6.A.R) first removes samples with missing sample-table `Response`, intersects sample IDs with its count matrix, selects pretreatment samples, then explicitly removes four named pretreatment sample records (code comment: “Exclude 4 samples”; script lines 84–121). The script gives no rationale for those removals and does not state that they are universal cohort exclusions. The script then filters genes and fits a PRCR-vs-PD model. The report says its baseline transcriptomic analysis used 45 patients and separately describes excluding a PCA outlier; the current deposited annotation still contains that record. These are distinct documented exclusion statements. The four code removals give an arithmetic route from 49 response-evaluable baseline records to 45, but that arithmetic alone does not prove the exact table-analysis set: the full count-matrix intersection and complete script execution were not checked. [Published article](https://pmc.ncbi.nlm.nih.gov/articles/PMC5685550/); [pinned author script](https://raw.githubusercontent.com/riazn/bms038_analysis/137111c38a32f8626ee6a436e14ac667bd31b1e7/rnaseq/TableS6.A.R).

The timing item covers 58 on-treatment specimens and carries the source label `On` (item `I-6e356c35dc2585083392`). The source does not attach individual collection days in the reviewed GEO metadata. The paper's protocol schedule supports calling them on-treatment, but does not justify imputing each specimen's day.

## Recommended baseline policy (not applied)

Retain the original author `BOR` and GEO corroborating value separately. Apply the frozen endpoint ontologies: `NE`/`UNK` remain unevaluable/null, never PD or a binary ORR class. The three flags are a raw-label vocabulary crosswalk, not evidence that the cases have different clinical outcomes; pointer metadata identifies two as baseline and one as on-treatment. A named public-source reviewer can accept this documented crosswalk when signing the worksheet; until then the worksheet remains unsigned and unchanged. Retaining source records does not establish ORR-branch eligibility: the two baseline records remain unevaluable and cannot enter an ORR-evaluable cohort.

Keep source-available pretreatment specimens in the source/field-map record; this is record retention, not analytical inclusion or cohort admission. Do not inherit the four script removals as general eligibility criteria. Before any future analysis or admission, define and approve an outcome-independent QC/eligibility policy for baseline specimens. If exact reproduction of the publication's baseline Table S6A is needed, define that as a separate analysis population and clarify the count-matrix intersection and the relationship to the publication's PCA exclusion. Do not select or remove baseline specimens to force N=45.

## Remaining human decisions and evidence gaps

- The public reviewer must accept the BOR-to-GEO `NE`/`UNK` crosswalk and confirm that these are unevaluable for the declared ORR branch; the frozen ontology already rules out assigning them positive or negative ORR.
- A future reproduction decision must establish whether the four explicit script removals, the article's PCA exclusion, or both are part of that reproduction's population, and identify the intended count-matrix intersection. Neither the paper nor the script rationale reviewed here explains the four removals or reconciles these distinct statements.
- No reviewed public metadata establishes actual collection day for an individual on-treatment specimen. If a downstream estimand requires exact elapsed days or a landmark, the required source evidence is absent; do not infer it from the protocol window.

## Baseline blockers

The on-treatment timing uncertainty does not block retaining baseline source records when `On` specimens are excluded. The outcome flags affecting baseline records remain unevaluable under the frozen ontologies; their crosswalk still needs public reviewer signoff, and those records are not ORR-eligible. The four-exclusion/PCA ambiguity does not block retaining source-available pretreatment records. It does block asserting exact replication of Table S6A or its reported N=45. Analytical inclusion and cohort admission still require an explicit, approved, outcome-independent baseline QC/eligibility policy. These findings do not establish matrix suitability, complete cohort eligibility, a clinical model, or any biological result.
