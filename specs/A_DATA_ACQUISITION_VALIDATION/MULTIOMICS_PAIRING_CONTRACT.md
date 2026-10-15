# Multi-omics pairing contract

## Pairing states

Every modality relationship is exactly one of:

- `SAME_SPECIMEN`;
- `SAME_PATIENT_SAME_TIME_DIFFERENT_SPECIMEN`;
- `SAME_PATIENT_DIFFERENT_TIME`;
- `UNPAIRED`;
- `UNKNOWN`.

Study-level co-availability, similar names or equal row order do not establish pairing.

## Pair record

```text
pair_id
study_id
patient_uid
modality_a/assay_uid_a/specimen_uid_a
modality_b/assay_uid_b/specimen_uid_b
pairing_state
time difference
same lesion status
link evidence and source locator
certainty
endpoint evaluability
branch eligibility
reviewer
```

## Denominator report

For every study and modality pair report separately:

- patients in modality A;
- patients in modality B;
- linked patients;
- same-timepoint patients;
- same-specimen patients;
- endpoint-evaluable linked patients;
- branch-eligible linked patients;
- ambiguous/unknown links.

The largest modality count is never reported as paired N.

## Analysis boundaries

- unpaired modalities are not concatenated into artificial patients;
- same patient/different time is not baseline multi-omics pairing;
- tumour and blood/plasma remain different compartments;
- bulk, single-cell and spatial evidence can be orthogonal rather than directly paired;
- a small paired subset cannot select features and then masquerade as an independent evaluation on the same patients;
- modality-specific missingness and selection mechanisms are reported.

## Multi-omics admission

`PAIRED_MULTIOMICS` requires V1–V6 plus a verified patient link. A same-specimen claim additionally requires a source-supported specimen crosswalk. Unknown pairing blocks the paired branch but may allow separate modality-specific evidence.

## Release receipt

The pairing receipt includes modality object hashes, all denominators, state counts, unresolved links, exclusions, branch use and overlap/exposure disposition.
