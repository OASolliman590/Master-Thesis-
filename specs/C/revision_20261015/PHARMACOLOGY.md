# Pharmacology and translational-plausibility contract

## Purpose

The pharmacology layer asks whether an experimental exposure has a defensible relationship to documented human and experimental exposure. It does not transform a molecular score into a dosing recommendation.

## Required extraction

For every shortlisted parent compound and exact formulation:

- jurisdiction and regulatory status with access date;
- approved/investigational/withdrawn indication status;
- formulation, salt, route and release characteristics;
- human regimen and population;
- dose and schedule;
- single-dose and steady-state Cmax and AUC;
- total versus unbound concentration;
- plasma protein binding and measurement method;
- active metabolites and their exposure/activity;
- sampling time and accumulation;
- tissue/tumour or intracellular data where directly measured;
- primary label, regulatory review or original human PK source;
- unit conversions with formula and assumptions;
- uncertainty and missing fields.

## Comparability fields

For the experimental context also record:

- nominal medium concentration;
- medium composition and protein content;
- exposure duration and replacement schedule;
- washout/recovery;
- estimated free medium concentration only when supported;
- intracellular exposure only when measured;
- target-engagement evidence.

## Interpretation categories

- `supported_exposure_relationship`
- `possibly_compatible_high_uncertainty`
- `poorly_matched_exposure`
- `not_assessable`

A culture concentration below total plasma Cmax is not automatic feasibility. A concentration above Cmax is not automatic invalidity when formulation, local exposure, accumulation, metabolites or intermittent dosing differ. The reasoning and limitations must be explicit.

## Regulatory discipline

- ChEMBL/DrugBank/PubChem categories do not prove approval.
- Status is molecule-, formulation-, jurisdiction- and date-specific.
- A withdrawn indication is not described as current approval.
- Prostate use is not implied by approval in another disease.
- A commercial tablet is not automatically a research-grade reagent.

## Tazemetostat correction

FDA's withdrawn accelerated-approval list records withdrawal of both Tazverik indications effective 22 June 2026, and FDA separately described the safety-driven voluntary withdrawal. Paper C may retain tazemetostat as a mechanistic research compound, but it must record the withdrawal and cannot use current FDA approval as a translational advantage.

## Output

The pharmacology table remains separate from molecular ranking and must show contradictory or missing evidence. No compound is removed solely because one nominal concentration exceeds one total Cmax value without a complete exposure analysis.
