# Canonical data model and dictionaries
> **v2 operating contract:** Core numerical evidence is external public evidence. References to culture, assay, donor or experimental data below mean source-attributed published measurements in core, not a requirement to generate local data. Original project integration is exclusively E_LAST after core release. Core profiles and release gates are defined in CORE_COMPLETION_CONTRACT, not legacy D01–D14 labels. Technical observation/identity restrictions apply unchanged.


## Evidence graph

Publication family → original study → population/experiment → regimen → specimen/assay → observation → curated parameter → model version → validation claim. Source objects can support multiple nodes, but shared evidence is not independent replication. All entities have immutable IDs and versioned correction links; raw/source IDs remain in their permitted store.

## Tables and primary keys

| Table | Key / essential relationships | Scientific fields |
|---|---|---|
| publication_families | family_id; member source IDs | final/preprint/mirror/shared-study relationship and evidence. |
| studies | study_id; family_id | original design, species/context, trial/cohort/experiment identities. |
| source_objects/access | source_id/version | exact route/object, access/terms, retained bytes/hash, parser and verification. |
| compounds/biologics | compound_id | parent/target, identifiers, species reactivity, molecule versus clone. |
| formulations | formulation_id; compound_id | parent/salt/form, route/vehicle/concentration basis, lot evidence. |
| populations | population_id; study_id | individual/aggregate, source N/statistic/context, no fabricated individuals. |
| experimental_manifests | experiment_id | approval/state, hierarchy, materials/instruments, raw files and roles. |
| dosing_events | event_id; experiment/regimen | compound/formulation, time/unit/origin, amount/concentration, route, addition/removal/infusion/retention. |
| observations/assay_results | observation_id; experiment/assay | analyte/cell gate, raw/canonical value/unit, statistic/N, uncertainty, censoring and source locator. |
| parameter_evidence | parameter_id/version | symbol/unit, source/prior/status, numerical value or unresolved reason, transformations/permitted use. |
| model_assets | asset_id/version | equations/runtime/licence/source/calibration overlap/parity state. |
| role_assignments | assignment_id; model_version/group | exploratory/calibration/model_selection/independent_public/prospective/context role and freeze. |
| prospective_predictions | prediction_id; model/data/software hashes | scenario/observations/distribution, time grid, primary metric, exclusions, receipt/witness. |
| vpop_targets/scenarios | target_id/scenario_id | context/statistics/joint assumptions, dose/exposure/time constraints. |
| runs/validation_receipts | run_id/receipt_id | immutable inputs/config/code, solver/seed/environment, outputs and level-specific claim. |

Compatibility measurement contracts are the 22 schemas under schemas/, including handoff, decision and inventory. Five additional contracts in schemas_v2/ define core release, evidence profile, capability snapshot, extension activation and public-run input. Extension-related compatibility schemas remain available for published experiment descriptions or future handoffs; they are not required original-data acquisition gates. Dictionary semantics override neither source wording nor units. New fields require schema migration and compatibility tests, not arbitrary additional properties.

## Missingness, units and statistics

Unknown numerics are null plus an explicit reason; the string UNKNOWN belongs in status/description, not numeric fields. Time is canonically hours for modelling but source unit/origin is retained. Amount and concentration are distinct types; volume is required for conversion. PK concentration units must preserve analyte/matrix/binding basis. Cell counts, fractions and fluorescence units cannot be interchanged.

A biological N counts the declared independent unit, not events/wells/timepoints. A reported percentage has denominator and statistic. SD, SE, CI and extraction uncertainty are separate fields. BLQ is censored, not zero. qPCR Cq and transformed quantities are linked; flow MFI is arbitrary/calibrated fluorescence as actually measured, never copies/cell without calibration.

## Integrity rules

Foreign keys resolve before admission. Duplicate IDs with different payloads fail; exact duplicates are logged and deduplicated without adding N. Validation assignments are grouped by original study/experiment/donor as appropriate. Model-input manifests include only allowed roles; evaluation files are unavailable to development. A model version plus all input/config/software hashes determines run identity. Changed bytes invalidate cache and require a new receipt.
