# Consumer model and patient-matrix requirements

The normalized entity definitions live only in ../A_DATA_ACQUISITION_VALIDATION/PATIENT_DATA_MODEL.md and its schemas. This document defines A's joins and acceptance invariants, not a second store.

## Identity and episode joins

study_id identifies an originating study, not an accession. patient_uid is a stable project pseudonym within that resolved study; its private alias crosswalk preserves exact strings, including leading zeros and punctuation. A pseudonym algorithm does not prove independence. Confirmed/suspected overlap connects study, publication, patient, specimen, assay and data-object nodes; unresolved potentially overlapping families cannot straddle development and final test.

The episode_binding schema links each exposure component, specimen and clinical outcome to a treatment_episode_id. The binding is source-supported. An outcome is not a permanent patient attribute: best response to an earlier ipilimumab episode cannot label the subsequent nivolumab baseline. Missing prior therapy remains UNKNOWN, not treatment-naive. For a released row, patient/episode/endpoint/specimen/assay foreign keys and biological compartments must agree.

## Baseline materialized row

One row per patient per branch, with study/cancer/subtype, episode/regimen/class/prior treatment, selected specimen and assay, source matrix column, raw outcome and criteria, ORR/DCR evaluability, inclusion/exclusion reason, expression unit/annotation, role and prior exposure. Full column contract is shared matrices/BASELINE_PATIENT_MATRIX.md; the shared materialized_matrix.schema.json adds an executable record contract. Raw IDs remain private.

Select the source-supported pre-index specimen using a frozen source-specific hierarchy: temporal relevance to the index episode; qualified tissue/assay; prespecified lesion preference; stable opaque tie-breaker. Outcomes and model scores cannot break ties. Unknown timing does not become baseline by study reputation. Different lesions are not independent patients. Technical resequencing is resolved before biological specimen selection and combined only when the assay contract permits it.

## Branch membership and roles

Membership is a separate patient × branch record with reasons and receipt IDs. A patient may be eligible for A-BIO but ineligible for CYT/A-P2 owing to assay coverage. Global final-test reservation overrides all discovery membership for the patient's related assays, including A1. Fold membership is nested evaluation metadata, not a contradictory permanent role. Count unique patients, specimens and assays independently at every flow stage; include excluded/blocked records and reasons in private audit tables.

## Missingness

Null with a reason denotes unknown/not observed; zero is a measured value. Never infer missing genes as zero, infer response from cohort totals or column order, or infer a specimen-patient bridge from array position. Raw endpoint values are immutable. Conflicts trigger a review packet rather than a parser-specific precedence rule.
