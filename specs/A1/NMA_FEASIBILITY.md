# Comparative and network meta-analysis feasibility

## Present decision

Clinical NMA is NOT released. No comparative-arm patient network has been admitted in this Spec Kit. Responders and nonresponders are outcome strata, not randomized treatment arms. Separate single-arm transcriptomic studies do not generate comparative relative treatment effects. A1's within-study molecular estimates and compatible-context synthesis do not require a clinical NMA.

| Required question | Current evidence state | Resolution and consequence |
|---|---|---|
| Are actual comparative treatment arms available? | UNKNOWN at admitted patient level | Resolve original trial randomization/arms and biopsy subset; R/NR is insufficient |
| Is the network connected for the specific outcome? | NOT ESTABLISHED | Build arm/treatment/outcome edges only from valid comparative designs |
| Are populations, lines and prior therapies compatible? | NOT ESTABLISHED | Compare eligibility and effect modifiers; do not assume cross-cancer exchangeability |
| Are endpoints and follow-up comparable? | NOT ESTABLISHED | Preserve ORR systems, landmarks, censoring and molecular windows |
| Are moderators sufficiently measured for transitivity? | NOT ESTABLISHED | Explicit clinical/statistical assessment; class labels alone are insufficient |
| Can inconsistency be assessed? | NOT ESTABLISHED | Require appropriate loops/design information; absence of testable loops is disclosed |
| Are molecular measurements/effect scales comparable? | NOT ESTABLISHED | Same assay/effect/window estimand or separately justified bridge |
| Does repeat-biopsy selection preserve the arm comparison? | NOT ESTABLISHED | Report selection and missingness by actual arm; randomization alone does not ensure an unbiased assayed subset |

## Allowed outcomes of the feasibility ticket

1. A separate clinical NMA protocol is feasible and requires new explicit release.
2. A molecular comparative synthesis is feasible for defined actual arms/outcomes.
3. Only a pairwise within-study/limited pooled comparison is defensible.
4. Only stratified response-associated molecular synthesis is defensible.
5. No comparative synthesis is identifiable; publish the evidence map and limitations.

Current default is option 4 where its own admission/compatibility gates pass, otherwise option 5. Do not label option 4 a treatment NMA. An ARM_TIME_INTERACTION, even in a randomized trial, requires the correct assayed population, time model and missingness assumptions; it is distinct from RESPONSE_TIME_INTERACTION. No drug superiority or component-specific efficacy claim is licensed by this document.
