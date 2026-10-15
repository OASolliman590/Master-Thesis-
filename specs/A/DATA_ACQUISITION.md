# Paper A acquisition interface

## Authority

Use ../A_DATA_ACQUISITION_VALIDATION as the sole source-discovery, identity, endpoint, episode, overlap, exposure and admission authority. The package inherited from draft PR #9 is augmented by INTEGRATION_AMENDMENT_20261015.md; no independent A patient registry is permitted. SOURCE_CANDIDATE_QUEUE.tsv remains the original 77-reference queue, not an admitted roster. Shared source matrices and the prior source-by-question table describe candidates only.

## Pipeline boundaries

Discovery produces source-located candidate records. Resolution groups publications/accessions into originating studies. Retrieval first searches permitted caches and verifies complete bytes, source version, licence and SHA-256; a filename is not evidence. Parsers preserve source identifiers as strings, raw values and provenance. Curation creates normalized records and episode bindings. Admission is branch-specific and reviewer-backed. Only then may materialized matrices and their split/coverage/build receipts be released.

Processed-first does not mean count-free: deposited integer count matrices are processed objects. Do not fetch FASTQ/BAM/IDAT or reprocess raw proteomics/spatial images by default. Controlled access is catalogued separately and requires action-specific authorization before application, credentials or downloading. No automatic author outreach. Recovered reports without their matrices remain historical evidence.

## Source by question

The shared SOURCE_BY_QUESTION_COVERAGE.tsv carries candidate status separately for baseline biology, A-P2 development, independent testing, A-P1, A1 pairing and orthogonal corroboration. An endpoint-bearing source is not automatically a model test set. A processed matrix is not automatically score-compatible. ICI clinical populations, non-ICI mechanistic systems, vaccines/cell therapies and untreated TCGA must not enter one denominator.

## Search release

The search plan must cover catalogue resolution (ICBatlas/TIGER/IOhub/Cancer-Immu and historical lists), original papers/supplements/trial families, official repositories, longitudinal/comparative studies, linked modalities and current methods. One integrator merges evidence packets. Log actual pagination/export coverage and access caps; a schedule or two unproductive result pages is not completion. Search version completion and branch-specific data release are separate: a bounded explicitly declared source universe may support a released branch without claiming a globally complete systematic search.

## Patient materialization contract

A consumes baseline_patient_matrix, endpoint_matrix, assay_feature_coverage, split_registry and analysis_membership plus immutable admission/build/validation receipts. Primary key and join integrity, episode-linked endpoint, one selected baseline specimen, source-correct units and protected-family exclusion are mandatory. Parsing success cannot authorize analysis. Any required frozen source failing later marks the dependent aggregate INCOMPLETE_REQUIRED_SOURCE; no silent disappearance or renormalization.
