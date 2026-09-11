# Feature Specification: Spec 026 — Analysis Design Contrast Registry

**Feature Branch**: `026-analysis-design-contrast-registry`
**Created**: 2026-05-30
**Status**: Draft for implementation
**Scientific-priority rank**: design-critical. Severity S1.

## Context Lock

The previous pipeline treated available execution tracks as if they were the study design. This spec adds a design layer that explicitly defines every analysis axis before Stage 06 DE, Stage 07 meta-analysis, and downstream reporting consume it.

All analysis axes are co-equal discovery families, while their biological interpretation remains distinct:

- `PRE_RESPONSE`: baseline predictive responder vs non-responder signal.
- `ON_RESPONSE`: early pharmacodynamic responder vs non-responder signal.
- `POST_RESPONSE`: post-treatment response-state responder vs non-responder signal.
- `DELTA_RESPONSE`: paired treatment-induced change by responder status.
- `DRUG_STRATIFIED_RESPONSE`: timing-aware response contrasts within therapy groups.
- `ICI_COMBINATION_RESPONSE`: timing-aware response contrasts for any ICI-containing combination regimen.
- `CANCER_STRATIFIED_RESPONSE`: timing-aware response contrasts within cancer groups.
- `PAN_ICB_RESPONSE`: timing-aware response contrasts pooled across cancer and therapy, with moderators retained.

## Functional Requirements

- **FR-001**: The pipeline MUST materialize a normalized sample-level analysis manifest before DE/meta execution.
- **FR-002**: The contrast registry MUST assign a stable `analysis_id` to every planned analysis family and include timing, pairing, drug scope, cancer scope, interpretation label, feasibility status, and blocker reason.
- **FR-003**: PRE/ON/POST response contrasts MUST be timing-specific and MUST NOT silently pool timepoints.
- **FR-004**: DELTA analyses MUST be paired only and MUST distinguish pre-to-on from pre-to-post membership.
- **FR-005**: Drug-stratified and cancer-stratified analyses MUST preserve both collapsed groups and raw labels.
- **FR-006**: Pan-ICB analyses MUST retain cohort, drug, and cancer fields for downstream moderators.
- **FR-007**: Feasibility gates MUST be explicit; infeasible candidate analyses are represented as blocked registry rows, not silently omitted.
- **FR-008**: `design build` MUST write `analysis_sample_manifest.tsv`, `analysis_contrast_registry.tsv`, `analysis_contrast_membership.tsv`, and `analysis_design_audit.md`.
- **FR-009**: Legacy `PRE_RESPONSE` and `TREATMENT_DELTA` contrast commands MUST remain supported during migration.
- **FR-010**: Router dry-runs MUST be able to consume an analysis registry and report planned `analysis_id`s without running DE.
- **FR-011**: Any ICI-containing combination regimen MUST be available as a separate `ICI_COMBINATION_RESPONSE` family, independent of the broader drug-stratified rows.
- **FR-012**: Optional execution-readiness gating MUST align design feasibility with Stage 06 assay and expression-file constraints.
- **FR-013**: When `assay_type` is absent but an expression matrix is readable, design and Stage 06 MUST classify assay type from file content instead of treating `bulk_rna_seq` as unreadable.

## Success Criteria

- **SC-001**: A mixed PRE/ON/POST/DELTA fixture produces deterministic sample, registry, membership, and audit outputs.
- **SC-002**: DELTA membership contains only paired patients and never mixes unpaired after-treatment samples.
- **SC-003**: Drug and cancer manifests retain raw labels while exposing collapsed analysis groups.
- **SC-004**: Router dry-run lists feasible analysis IDs from the registry and does not run Stage 06/07.
- **SC-005**: Existing legacy PRE/DELTA tests keep passing.
