# A data contract

Status: proposed, verified facts distinguished below. Evidence checked 5 September 2026. Resource totals are not analysis eligibility.

| Question | Source and actual metadata coverage | Primary eligibility today | Validation role and limits |
|---|---|---|---|
| Can endpoint definitions be compared in melanoma? | GSE91061: 109 profiles, 51 baseline title-derived patient codes; baseline PD23, SD16, PRCR10, unknown2 | At most49 baseline labelled codes before expression, regimen and overlap QC; final N unknown | Candidate development/replication cohort. PRCR can support combined objective response, not separate CR and PR counts |
| Is another cancer represented? | GSE176307: 90 records; CR7, PR9, SD4, PD69, NA1 | At most89 labelled records; baseline/patient uniqueness not fully verified | Candidate urothelial replication; four SD records mean a small endpoint-switch group |
| Can binary response identify SD? | GSE126044: 16 records, binary responder5/nonresponder11 | Not from these fields alone | Secondary original-endpoint validation only after timing/criteria verification |
| Can survival labels supply RECIST? | GSE135222: 27 records with PFS time/event fields | No categorical response from inspected fields | Separate durable-benefit/survival work only when event/censoring rules are supported |
| What happens with no SD? | GSE78220: 28 records, complete/partial response15 and PD13 in metadata; no SD label | Same ORR/DCR labels if absence is genuine; patients/timing still need review | Structural zero sensitivity; show separately, do not call robust clinical benefit or force SD labels |
| Is public prostate trial RNA available? | GSE229555 COMBAT: 30 profiles from15 subjects, Pretx15/C4D1 15; Pretx PSA50 yes7/no8, radiographic yes4/no11 | Not eligible for the paired CR/PR/SD/PD primary from current labels | Exploratory sequential BAT/nivolumab-regimen endpoint only; timing and expression units unresolved |
| Can a more direct prostate ICI cohort be used? | Guan 2022 Nature reports pretreatment single-cell n8 and separate bulk n16 with PSA-decline endpoint | Public complete expression/label package not secured | Candidate separate clinical endpoint; not ORR by relabelling |
| How do immune scores behave in untreated prostate? | TCGA-PRAD and selected PCaDB sources; independent cohort and gene coverage audit pending | No ICI response labels | Molecular transport, score coverage/range and cell-composition association only |

Metadata recount: ../../docs/research/A_clinical_transfer/candidate_label_coverage.json. COMBAT summaries and source workbook inventory are adjacent. Original GEO URLs, publication dates and access uncertainties: ../../docs/research/A_clinical_transfer.md. Source records: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061 and the corresponding accession endpoints for each row.

## Inclusion, identifiers and missingness

The unit is a patient in an originating trial/cohort. Preserve study_id, accession, original patient identifier, specimen, sample_id, visit, biopsy timing relative to each treatment, regimen and response-assessment system. Never infer independence from different accessions. Match clinical/expression records one-to-one after a declared specimen rule; accession/GSM mismatches must stop the affected cohort, not silently drop rows. Multiple baseline specimens: select by timing, tissue and assay QC under a written source-specific rule before scores or association results are inspected.

Keep original labels and mapping reason/locator. Allowed primary mapping: CR or PR or explicitly combined PRCR → ORR1/DCR1; SD → ORR0/DCR1; PD → ORR0/DCR0. UNK, NA, NE, missing and undocumented binary labels remain unevaluable for this primary. iRECIST confirmed and unconfirmed progression require original trajectory rules; no automatic equivalence. Do not turn short censored follow-up into durable nonbenefit. Clinical labels are never imputed for sample-size gain.

CYT requires both GZMA and PRF1, valid gene identity and a common declared abundance scale. Prefer TPM for the proposed primary. Complete nonnegative FPKM can be converted using the declared full feature universe and source annotation; do not normalize only the two immune genes. Log abundance, count, FPKM and TPM fields must remain distinguishable. Do not silently exponentiate author-transformed values or resolve ambiguous gene aliases by best association. Gene-level mapping and transcript collapse are source-versioned and must precede scoring.

Catalogue each original file's URL, access route, publication, release/download date, SHA-256, byte count, assay, unit, genome/identifier annotation, transformation, license, redistribution status and originating study. Current audits establish public metadata access; exact matrix licenses and redistribution are still gates. Store restricted/large matrices outside Git and Notion; publish manifests and eligible aggregate evidence only.

## Snapshot and exposure contract

Freeze the cohort manifest and feature/label transforms before confirmatory scoring. Inventory past exposure to each cohort and old run; metadata inspection is disclosed. Do not claim an unseen test set merely because files moved into a new repository. Reserve independent, not previously used development studies if available; if none can be established, label validation retrospective and do not claim prospective preregistration.

## Branch-specific frozen admission manifests

Maintain separate manifests for A-P1 endpoint-switch primary, its no-SD sensitivity, discovery development, discovery final test and each prostate branch. A-P1 requires O/SD/PD all represented; discovery ORR requires O and non-O but does not require SD. Preserve branch exclusions explicitly. The same study cannot appear as both discovery development and final test, including through an atlas/reanalysis accession. All final-test patients remain outside feature filtering, normalization fitting, tuning and the gene handoff.

The current table contains only candidate coverage. At present it does not establish the at-least-three-development-plus-independent-test structure proposed in DISCOVERY.md. GSE78220's source categories may admit it to discovery even if it supplies a structural-zero A-P1 sensitivity; binary GSE126044 requires proof of the exact response definition. Audit atlas/old-run original sources as candidates without treating catalogues as independent cohorts or inventing eligible counts.

TCGA-LUAD and original PCaDB prostate cohorts are proposed in TRANSPORT.md; exact A manifests, measured feature coverage, specimen rules and assay scales remain gates. Public GDC metadata alone does not establish source-linked pathologist cellularity. COMBAT/Guan retain their source-specific regimen and response definitions. Record whether each branch is unavailable, conditionally specified or admitted, rather than hiding unmet gates in one generic cohort list.

Freeze cohort/cancer weights and branch denominators with these manifests. Any subsequent required-source failure yields an incomplete corresponding aggregate; it cannot automatically remove the study and renormalize surviving weights. Reduced-source exploratory outputs require separate identifiers and explicit exposure disclosure.
