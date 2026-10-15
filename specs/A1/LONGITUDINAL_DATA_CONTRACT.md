# Longitudinal data contract

## Required normalized inputs

Use shared study, patient, treatment_episode, treatment_exposure, specimen, assay, clinical_outcome and episode_binding records, plus overlap/exposure/split and branch admission receipts. A patient's outcome belongs to an assessment and treatment episode, not all of their specimens. The binding validator must reject a follow-up from a new regimen paired to an old regimen baseline unless that precise transition is the prespecified contrast.

Required fields include patient_uid, study_id, treatment_episode_id, exposure components, exact source timing label, relative day or source-supported categorical window, tissue/lesion and preservation, assay/platform/unit/annotation, response endpoint/assessment time, repeat-biopsy selection and missing-follow-up reason. Every assertion has a source locator and confidence; UNKNOWN cannot be replaced by a typical trial schedule.

## Materializations and row grains

patient_timepoint_long: patient × specimen × selected assay representation, with original timing and exact known days retained. Different modalities remain separate assay records. longitudinal_pair_matrix: patient × index episode × prespecified contrast/window, with both specimen/assay IDs, timing, same-lesion/platform, pair quality, endpoint linkage and inclusion reason. A repeated-measures release may retain several windows per patient and explicitly account for dependence. endpoint_matrix: patient × episode × endpoint/assessment. Multiple baseline rows are not independent patients.

## Counts and missingness

For each study/window report eligible baseline patients, follow-up-sampled patients, endpoint-evaluable patients, assay-evaluable patients, verified pairs, same-lesion pairs and final model patients; also report specimens and assays separately. Retain patients lacking follow-up in an audit denominator even though they cannot enter a paired-change model. Missingness reasons include no scheduled biopsy, refusal, clinical deterioration/progression, inaccessible lesion, tissue insufficiency, assay QC failure, no public object, linkage unresolved and UNKNOWN. Never convert absence of biopsy to biological zero or nonresponse.

## Source-level admission

A source with pre/post labels alone is not admitted. Resolve index episode, follow-up collection mechanism, time window, endpoint assessment and measurement comparability. A progression biopsy is not a scheduled pharmacodynamic observation. A post-induction sample before ICI belongs to the induction contrast. Endpoint and timing systems need not be identical across all sources, but incompatible definitions cannot enter the same pooled estimand.

## Provenance and release

Each admitted pair inherits source-object hashes, mappings, annotation, outcome and timing versions, overlap and prior exposure, and selection config. The build receipt records patient/specimen/assay counts and all exclusions. Access to A1 data does not override A-P2 protected-set reservations. A source can be admitted for DELTA_R but blocked for RESPONSE_TIME_INTERACTION when NR pairs are absent; this is explicit branch membership, not a global usable flag.
