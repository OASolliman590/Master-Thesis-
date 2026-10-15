# Paper A/A.1 Data Acquisition and Validation Spec Kit handoff

**Status:** review package complete; implementation and data population not started  
**Baseline:** `main@a8278c776da7c6b096cc14139d729979db286b50`  
**Review branch:** `review/a-data-acquisition-validation-speckit-20261012`  
**Approved defaults:** D01–D10, 15 October 2026

## Start here

Read `specs/A_DATA_ACQUISITION_VALIDATION/README.md`, then the appraisal, decision log and ticket register. The package is standalone and supplies contracts to `specs/A/`, candidate A.1, Paper B/C interfaces and later workflow code.

## What this branch adds

- approved acquisition-state appraisal and protocol crosswalk;
- normalized study/publication/source/patient/treatment/specimen/assay/outcome model;
- endpoint, timepoint, assay, pairing, overlap, exposure, admission, matrix and split contracts;
- twelve Draft 2020-12 JSON schemas;
- twelve header-only registry templates;
- seven materialized-matrix contracts;
- eight read-only agent prompts;
- three-way historical implementation reconciliation;
- fourteen bounded implementation tickets and adversarial test requirements;
- specification-level structural tests and validation receipts.

## Explicit non-claims

No source adapter, patient registry, source matrix, cohort admission, materialized analysis matrix, split, model, biological effect, final test or AIU run is included. Passing the package tests validates the specification structure only.

## Next authorized sequence after review

Implement DAV-T01 through DAV-T14 under TDD and the public/private boundary. Populate registries only after source-specific review. Do not release Paper A/A.1 analysis until the relevant branch reaches R9. Do not merge this branch automatically and do not close issues #1 or #7.
