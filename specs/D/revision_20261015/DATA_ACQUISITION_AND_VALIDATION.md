# Data acquisition and validation sub-kit

## Required source classes

1. observational single-cell;
2. longitudinal ICI single-cell;
3. spatial transcriptomics/protein;
4. chemical perturbation single-cell;
5. genetic perturbation single-cell;
6. cytokine perturbation single-cell;
7. bulk perturbation;
8. protein/functional perturbation;
9. combination-therapy data;
10. tumour-growth/immune-killing data;
11. prospective project wet-lab data.

## Source record fields

Every object records study, publication, repository, release, access route, licence, donor/model, cancer/disease state, cell type, specimen, treatment identity, dose, duration, sequence, controls, modality, feature space, preprocessing, replicate structure, cell count, biological N, training overlap, permitted role, validation role, and limitations.

## Gates G0–G10

| Gate | Meaning | Evidence required |
|---|---|---|
| G0 | source discovered | resolvable lead; no eligibility claim |
| G1 | original study resolved | publication, experiment, object identity |
| G2 | measurement validated | units, platform, IDs, transform, controls |
| G3 | perturbation identity validated | parent/salt, exact dose, duration, sequence |
| G4 | biological unit validated | patient/donor/experiment/plate/cell nesting |
| G5 | ontology compatible | exact/parent/ambiguous/unsupported mapping |
| G6 | model compatible | genes/order/transform/context/vocabulary/output |
| G7 | training overlap resolved | training/development/test/unknown |
| G8 | benchmark role approved | training/calibration/development/test/corroboration |
| G9 | parameterisation approved | parameter, unit, prior, uncertainty, role |
| G10 | prospective validation approved | assay, contrast, prediction, success/falsification frozen |

A source may pass one role and fail another. Cells are never independent patients or experiments.

## Split rules

Split at the highest relevant unit: study, patient, donor, experiment, plate, cell line, drug, or context. All cells and technical subdivisions from one independent unit remain together. Unknown model pretraining overlap blocks an independent-test claim.

## Acquisition default

Public metadata inspection and small lawful tracers first. Large downloads, controlled access, paid transfer, author contact, and new licence acceptance require separate approval.
