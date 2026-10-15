# Prostate tumour–immune initialization

## Initial level: D2-PAIR experiment archetype

Initialize the actual qualified co-culture experiment, not a patient digital twin.

Required inputs:

- tumour model identity, passage/batch, baseline viable count, growth/death distributions;
- immune-system identity, donor/clone/batch, viable count, activation state, receptor eligibility;
- geometry and seeding layout;
- measured contact/killing observables;
- measured or frozen exposure/PD drivers;
- assay timepoints and observation model;
- parameter uncertainty and random seed.

## Conditional D2-TISSUE extension

Cohort archetypes such as immune-quiescent, myeloid-dominant, inflamed, or stromal-excluded may be represented only when the compartments and observer variables exist. A B-cell/TLS-enriched archetype is prohibited without B/TLS representation and observation mapping.

## Validation

Initialization must reproduce baseline counts, viability, growth, receptor/ligand eligibility, and spatial arrangement within prespecified tolerances before treatment simulation.
