# Paper A + A.1 Data Acquisition and Validation Spec Kit

**Version:** `0.1.0-review.20261015`  
**Status:** approved design defaults, review package; no scientific-analysis release  
**Repository baseline:** `main@a8278c776da7c6b096cc14139d729979db286b50`  
**Review branch:** `review/a-data-acquisition-validation-speckit-20261012`  
**User approval:** 15 October 2026, “approve defaults”

This package defines the authoritative acquisition, identity, endpoint, timing, assay, overlap, admission, matrix and split contracts for Paper A and candidate Paper A.1 of the MSc thesis *Epigenetic Priming for Enhanced Immunotherapy: A Multi-Omics Strategy to Sensitise Prostate Cancer to Immune Checkpoint Blockade*.

**No cohort is admitted by this specification.** It contains contracts, schemas, templates, agent prompts, migration decisions and implementation tickets. It does not contain patient records, source matrices, fitted models, biological effect estimates, final-test assignments or a completed Paper A/A.1 dataset.

## Controlling scientific position

Paper A studies pretreatment immune-expression programmes associated with response to immune checkpoint blockade. A-P2 discovery is the selected primary direction; endpoint-definition sensitivity is secondary. Paper A.1 is a conditional longitudinal extension and does not become a promised standalone manuscript merely because acquisition support is specified.

The acquisition system answers one question before any biological analysis:

> Exactly which patients, specimens, assays, timepoints, treatments and outcomes support each analysis, and what evidence proves that they are correctly linked, nonduplicated, appropriately measured and independent where required?

## Package map

| Need | Controlling document |
|---|---|
| Boundaries and interfaces | [SCOPE_AND_INTERFACES.md](SCOPE_AND_INTERFACES.md) |
| Initial audit and feasibility | [A_DATA_ACQUISITION_VALIDATION_APPRAISAL.md](A_DATA_ACQUISITION_VALIDATION_APPRAISAL.md) |
| University protocol reconciliation | [PROTOCOL_CROSSWALK.md](PROTOCOL_CROSSWALK.md), `protocol_crosswalk.tsv` |
| Search and agent design | [SOURCE_DISCOVERY_STRATEGY.md](SOURCE_DISCOVERY_STRATEGY.md), [AGENTIC_SEARCH_ARCHITECTURE.md](AGENTIC_SEARCH_ARCHITECTURE.md), `agent_prompts/` |
| Source identity and processed-data rules | [PROCESSED_DATA_POLICY.md](PROCESSED_DATA_POLICY.md), [SOURCE_IDENTITY_AND_DEDUPLICATION.md](SOURCE_IDENTITY_AND_DEDUPLICATION.md) |
| Normalized patient model | [PATIENT_DATA_MODEL.md](PATIENT_DATA_MODEL.md), `schemas/` |
| Endpoint, treatment and timing | [ENDPOINT_ONTOLOGY.md](ENDPOINT_ONTOLOGY.md), [TREATMENT_AND_TIMEPOINT_ONTOLOGY.md](TREATMENT_AND_TIMEPOINT_ONTOLOGY.md) |
| Assay and multi-omics contracts | [ASSAY_AND_MEASUREMENT_CONTRACT.md](ASSAY_AND_MEASUREMENT_CONTRACT.md), [MULTIOMICS_PAIRING_CONTRACT.md](MULTIOMICS_PAIRING_CONTRACT.md) |
| Materialized matrices | [PATIENT_MATRIX_CONTRACT.md](PATIENT_MATRIX_CONTRACT.md), [LONGITUDINAL_PAIRING_CONTRACT.md](LONGITUDINAL_PAIRING_CONTRACT.md), `matrices/` |
| Admission, validation and split freeze | [COHORT_ADMISSION_AND_RELEASE.md](COHORT_ADMISSION_AND_RELEASE.md), [VALIDATION_FRAMEWORK.md](VALIDATION_FRAMEWORK.md), [SPLIT_AND_PRIOR_EXPOSURE_VALIDATION.md](SPLIT_AND_PRIOR_EXPOSURE_VALIDATION.md) |
| Privacy and access | [ACCESS_PRIVACY_AND_REDISTRIBUTION.md](ACCESS_PRIVACY_AND_REDISTRIBUTION.md) |
| Historical-code reconciliation | [IMPLEMENTATION_RECONCILIATION.md](IMPLEMENTATION_RECONCILIATION.md), `implementation_reconciliation.tsv` |
| Software and tickets | [SOFTWARE_ARCHITECTURE.md](SOFTWARE_ARCHITECTURE.md), [TICKETS_AND_TESTS.md](TICKETS_AND_TESTS.md) |
| Reproduction and readiness | [REPRODUCE_AND_READINESS.md](REPRODUCE_AND_READINESS.md) |
| Approved and unresolved decisions | [DECISION_LOG.md](DECISION_LOG.md), [UNRESOLVED_QUESTIONS.md](UNRESOLVED_QUESTIONS.md) |

## Binding rules

1. **Originating studies, not publications or accessions, are candidate cohort units.**
2. **Patients, specimens and assays are distinct entities.** Technical replicates and repeated sequencing do not create patients.
3. **Raw and canonical endpoints are stored separately.** Objective response, disease control, durable benefit, PSA response, pathological response and time-to-event outcomes are not interchangeable.
4. **Raw timing and exact relative time are preserved.** “Follow-up” is not a valid biological window.
5. **Unknown remains unknown.** Missing values are not zeros; unavailable evidence is not negative evidence.
6. **Branch admission is explicit.** There is no global `usable=yes` or universal include flag.
7. **Final-test claims require exposure and independence proof.** A new path or accession does not reset prior exposure.
8. **Processed-first is the default.** Raw reprocessing requires an approved source-specific amendment.
9. **Public Git is patient-free by default.** Public accessibility does not establish redistribution permission.
10. **Data validation is not biological validation.**

## Completion boundary

Specification completion means the contracts are reviewable and implementation tickets are bounded. **Implementation completion is separate** and requires populated registries, source adapters, private patient/specimen mappings, generated matrices, executed validations, receipts, reviewer sign-off and environment validation. Paper A/A.1 data readiness may be claimed only at branch-specific readiness level R9.
