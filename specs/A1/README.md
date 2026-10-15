# Paper A.1 — active longitudinal workstream v1.0.0

**Fully specified for implementation planning; no real-data analysis released.** Thesis inclusion is the default. A separate manuscript is conditional on distinct evidence and precision, not statistical significance. This directory is an engineering boundary, not a declaration of manuscript count or completed preregistration.

## Scientific question

Which immune-expression programmes change during treatment, do within-patient changes differ between eventual responders and nonresponders, and which differences in cancer, regimen, sequence, timing and prior therapy are identifiable from independent data?

The central estimand within a qualified study/window is Delta_g = E[X_followup−X_baseline | R] − E[X_followup−X_baseline | NR]. It is response-associated differential change, not a randomized ICI effect, a parallel-trends estimate or proof of drug superiority. Cross-sectional ON_R_NR is not the same estimand.

## Authority and inputs

The shared ../A_DATA_ACQUISITION_VALIDATION package owns studies, patients, episodes, specimens, assays, outcomes, pairing and split/exposure controls. A1 consumes released patient_timepoint_long, longitudinal_pair_matrix and outcome/episode bindings; it never reconstructs patients from column order or keeps a parallel registry. All assays belonging to reserved A-P2 final-test families remain protected from A1 development.

## Read order

LONGITUDINAL_DATA_CONTRACT.md → TIMEPOINT_ONTOLOGY.md → PAIRING_CONTRACT.md → LONGITUDINAL_ANALYSIS.md → PHARMACOLOGICAL_CONTEXT.md → NMA_FEASIBILITY.md → VALIDATION_AND_FIGURES.md → TICKETS_AND_TESTS.md → READINESS.md. contrast_registry.tsv records estimands and distinct release needs. Numeric windows and model settings are not frozen here.

## No global deadlock

Pairing, direct response-by-time estimation, compatible-study synthesis, each moderator, optional corroboration and separate publication have independent gates. Two independent admitted families are the inherited minimal condition for cross-study synthesis, not a precision guarantee; one qualified study may support its own explicitly limited longitudinal analysis. An unidentifiable drug-class comparison blocks that comparison, not a valid within-regimen estimate. Clinical NMA is not required for A1. Missing paired methylation/spatial data does not halt the RNA workstream.

## Outputs and boundaries

The principal product is longitudinal_support.tsv plus full study-level effect tables, time/selection audit and versioned receipts. A1 evidence can contextualize A/B/C or D/E models only with observational/time/regimen limitations. It cannot silently select or repair A-P2 features after test access, duplicate baseline Paper A results as independent evidence, or become a causal kinetic model.
