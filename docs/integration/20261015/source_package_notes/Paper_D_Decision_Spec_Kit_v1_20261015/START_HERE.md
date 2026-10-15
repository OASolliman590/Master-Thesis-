# START HERE — Paper D approved decision and specification kit

**Package:** `Paper_D_Decision_Spec_Kit_v1_20261015`  
**Decision status:** **D-A through D-H approved by the user on 15 October 2026**  
**Scientific status:** specification and implementation handoff only; no new biological analysis, model inference, simulation, calibration, or prospective experiment has been run by this package.

## Read in this order

1. `APPROVAL_RECORD.md`
2. `specs/D/revision_20261015/DECISIONS_DA_DH.md`
3. `specs/D/revision_20261015/DEPENDENCIES_AND_RELEASES.md`
4. `specs/D/revision_20261015/ANALYSIS_AND_ENDPOINTS.md`
5. `specs/D/revision_20261015/DATA_ACQUISITION_AND_VALIDATION.md`
6. `specs/D/revision_20261015/VIRTUAL_CELL_ARCHITECTURE.md`
7. `specs/D/revision_20261015/TICKETS_AND_ACCEPTANCE.md`
8. `CODEX_HANDOFF_PROMPT.txt`

## Controlling scientific structure

- **D1 remains the historical conditional molecular benchmark.** Its human-prostate target population, supported chemical–dose–duration task, full ordered measured output genes, exact `theta`, and fixed same-drug comparator are preserved.
- **D2-PAIR is an independently gated measured-data-driven tumour–T-cell model.** It may proceed after its own assay, parameter, and validation gates even when D1 data are unavailable or STATE fails.
- **D2-TISSUE is conditional.** Myeloid, fibroblast, recruitment, and additional spatial components are added only with measured calibration and independent validation targets.
- **D2-LEARNED is conditional.** Learned molecular predictions enter only after task-specific D1 validity and a measured molecular-to-phenotype bridge.
- **Patient-specific digital twins are deferred.** Paper E retains PBPK/PKPD–QSP, exposure, induction/recovery, virtual populations, and schedule optimisation; Paper D owns spatial/contact-dependent behaviour and the incremental value of molecular predictions.

## Immediate implementation release

The first bounded implementation packet is **D-R02 / D-R03 / D-R05 / D-R07**:

- public-source and object inventory;
- typed condition, feature, control, and overlap validators;
- exact D1 arithmetic evaluator;
- reusable provenance/intake adapters.

D-R04 (Lin source/rights resolution) and D-R10 (wet-lab/Paper E interface) are read-only parallel packets. No model training, large atlas download, controlled-data action, author contact, AIU/GPU job, or real scientific scoring is authorized by this package.

## Truth labels

Every statement and artifact must distinguish:

- `OBSERVED_DATA`
- `SOURCE_DERIVED_FACT`
- `DESIGN_CHOICE`
- `LITERATURE_PRIOR`
- `FITTED_PARAMETER`
- `MODEL_PREDICTION`
- `RULE_BASED_ASSUMPTION`
- `SIMULATION_OUTPUT`
- `PROSPECTIVE_TEST`
- `UNKNOWN`

`UNKNOWN` is an acceptable and required value when evidence is not available.
