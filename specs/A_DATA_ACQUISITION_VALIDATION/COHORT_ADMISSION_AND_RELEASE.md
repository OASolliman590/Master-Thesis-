# Cohort admission and release

## Admission unit

Admission is evaluated for `study_id × branch_id × admission_version`. A cohort can pass one branch and fail another. A successful parser is not admission.

## Named branches and minimum criteria

| Branch | Minimum admission criteria |
|---|---|
| `A_BASELINE_BIO` | clinical ICI study; source-supported pre-index tumour expression; evaluable exact ORR or explicitly named source-binary endpoint; V1–V6 passed |
| `A_P2_DEVELOPMENT` | baseline criteria plus assay compatibility, sufficient class representation under analysis rules and development role frozen before feature selection |
| `A_P2_OUTER_VALIDATION` | baseline criteria plus originating-study holdout and no training/tuning use in current model |
| `A_P2_FINAL_TEST` | baseline criteria plus untouched-final-test exposure policy, required feature coverage and prospective freeze |
| `A_P1_ENDPOINT_SENSITIVITY` | recoverable CR/PR/SD/PD categories on the same patients; endpoint mapping versions frozen |
| `A1_ON_R_NR` | verified baseline and on-treatment pair/window; evaluable endpoint; no disqualifying treatment change |
| `A1_POST_R_NR` | verified baseline and post-treatment pair distinct from progression unless explicitly defined |
| `A1_RESPONSE_TIME_INTERACTION` | repeated/paired observations, response groups and declared time model; missing-follow-up audit |
| `A1_PROGRESSION` | baseline/progression pair, progression timing and intervening-treatment state |
| `A1_ARM_TIME_INTERACTION` | actual comparative arms, arm assignment and compatible serial sampling |
| `PAIRED_MULTIOMICS` | verified patient link and stated same-time/same-specimen status; modality-specific assay gates |
| `PROSTATE_TRANSPORT` | eligible prostate molecular cohort and transport-specific assay/specimen contract; no claim of observed ICI response unless treated outcomes exist |

## Admission receipt

Each admitted branch requires:

```text
study and publication family
source objects and complete hashes
retrieval date
verified patients/specimens/assays
baseline/longitudinal/response counts
endpoint definitions
assay/platform/unit
specimen and timing rules
feature coverage
overlap and prior-exposure disposition
approved and blocked branches
exclusions and reasons
validator/reviewer
code/config/schema versions
unresolved limitations
```

No patient identifiers are included in the public receipt.

## Admission outcomes

- `ADMITTED`: all mandatory gates pass;
- `ADMITTED_WITH_LIMITATIONS`: only when the branch explicitly permits the limitation;
- `SENSITIVITY_ONLY`: unsuitable for the primary branch but usable for a named sensitivity;
- `BLOCKED_UNKNOWN`: required evidence is unresolved;
- `EXCLUDED`: criteria fail;
- `SUPERSEDED`: replaced by a later reviewed receipt.

## Release sequence

1. V0–V6 evidence complete;
2. independent source reviewer signs the candidate record;
3. admission engine evaluates named branch;
4. reviewer approves V7 receipt;
5. matrix is built and validated at V8;
6. split/exposure review approves V9;
7. release bundle is immutable and analysis-facing.

## No silent denominator changes

Any change in source object, endpoint mapping, specimen rule, feature universe, exposure state or split creates a new admission/matrix version. A downstream analysis cannot silently drop a required source and renormalize weights.
