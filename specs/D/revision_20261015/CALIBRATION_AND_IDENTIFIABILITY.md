# Calibration and identifiability

## Parameter registry fields

Name, component, unit, prior/range, source, calibration dataset, test dataset, uncertainty, identifiability status, sensitivity rank, frozen version, and claim limit.

## Staged calibration

1. tumour growth/death and direct drug effects;
2. immune viability/motility/contact behaviour;
3. pairwise recognition and killing;
4. checkpoint mechanism;
5. spatial/field parameters if present;
6. multicellular composition/functional outcome;
7. learned molecular bridge only after earlier stages.

Do not fit all parameters simultaneously to one endpoint.

## Methods

Use method appropriate to dimensionality and simulator cost: profile/likelihood methods, Bayesian calibration, ABC/likelihood-free inference, ensemble calibration, Bayesian optimisation, surrogate models, Morris/Sobol global sensitivity, and practical identifiability diagnostics.

## Reporting rule

The specification currently identifies **risk of structural and practical nonidentifiability**. It does not claim a demonstrated structural-identifiability result until the actual equations, observables, and analysis are run.
