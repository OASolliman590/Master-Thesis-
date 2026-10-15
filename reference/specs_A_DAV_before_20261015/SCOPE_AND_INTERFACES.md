# Scope and stable interfaces

## Status

Controlling acquisition specification. The package governs source discovery through validated matrix and split release. It does not perform the scientific analyses that consume those products.

## In scope

- agentic and manual source discovery with complete query logging;
- originating-study and publication-family resolution;
- exact processed-object discovery and retrieval provenance;
- patient, treatment, specimen, assay and endpoint identity;
- baseline and longitudinal time reconstruction;
- multi-omics pairing;
- overlap and prior-exposure auditing;
- branch-specific cohort admission;
- materialized patient matrices and receipts;
- development/validation/final-test role validation;
- privacy, access and redistribution controls;
- reconciliation and selective migration of historical code.

## Out of scope

This kit must not:

- fit a predictor or select genes from outcome effects;
- compute final differential expression, programme scores or meta-analysis effects;
- compare treatments or infer component-specific efficacy;
- nominate prostate intervention targets or drugs;
- reinterpret missing data as a negative result;
- call a processed object biologically valid merely because it parses.

Outcome-blind structural tracers, synthetic/adversarial fixtures and small public format tracers are permitted.

## Interface to `specs/A/`

The analysis specification consumes only versioned products whose source cohorts passed the named branch gates:

- `baseline_patient_matrix.tsv`;
- `endpoint_matrix.tsv`;
- `assay_feature_coverage.tsv`;
- `split_registry.tsv`;
- `analysis_membership.tsv`;
- cohort-admission, validation and matrix-build receipts.

Ad hoc sample lists or undocumented exclusions are prohibited. Paper A may apply its frozen statistical estimands only after R9 release for that branch.

## Interface to Paper A.1

A.1 consumes:

- `patient_timepoint_long.tsv`;
- `longitudinal_pair_matrix.tsv`;
- exact treatment episodes and time assertions;
- pair-quality and missing-follow-up states;
- longitudinal admission receipts.

A.1 must preserve separate on-treatment, post-treatment, progression and after-regimen-change branches. The acquisition layer does not choose the meta-analysis model.

## Interface to Paper B

The approved A→B interface is a frozen, versioned, patient-free scientific product with:

- exact endpoint definition and branch;
- study/cancer/regimen/timing context;
- source and exposure hashes;
- feature universe and coverage;
- development and validation provenance;
- explicit overlap and final-test restrictions;
- qualified longitudinal context where available.

Paper B must not access reserved Paper A final-test outcomes for discovery, feature repair or programme selection.

## Interface to Paper C

Paper C receives only downstream A/B handoff provenance. This kit does not rank drugs. Any candidate evidence records whether the source was development-only, previously inspected, overlapping or independently evaluated.

## Interface to workflow implementation

Proposed owned paths:

```text
tools/a_dav/
tests/a_data_acquisition_validation/
docs/validation/A_DAV_*/
private_data/a_dav/        # logical private location; never committed
```

Every stage has an input schema, output schema, deterministic configuration, failure taxonomy and completion receipt. File-name conventions never substitute for a declared schema.

## Interface versioning

- Schemas use semantic versions and immutable IDs.
- Materialized matrices include schema and build versions.
- An analysis release pins admission receipt IDs, split version, object hashes, code hash and config hash.
- Breaking changes require a new major schema version and an explicit migration receipt.
