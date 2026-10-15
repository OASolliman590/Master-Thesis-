# Decision log

The user approved the Phase 1 defaults on 15 October 2026. These decisions control this review package. Future changes require a dated amendment; implementation findings do not silently rewrite them.

## D01 — package location — APPROVED

Use `specs/A_DATA_ACQUISITION_VALIDATION/` as a standalone sibling package. It serves A, A.1 and downstream interfaces and versions independently from `specs/A/`.

## D02 — public/private boundary — APPROVED

Keep patient-level registries, crosswalks, split assignments and matrices outside public Git by default. Commit patient-free schemas, code, synthetic fixtures and aggregate receipts only.

## D03 — untouched final-test standard — APPROVED

Reserve `UNTOUCHED_FINAL_TEST` for study families not used or inspected for current outcome-associated feature selection, tuning, threshold selection or performance assessment. Previously inspected studies remain usable under honest labels.

## D04 — raw-data reprocessing — APPROVED

Processed-first is the default. FASTQ/BAM/IDAT/raw-MS/raw-image reprocessing requires a source-specific approved amendment.

## D05 — controlled-access work — APPROVED

Controlled access is an optional lane initially. Apply only when a named branch is materially blocked and the expected gain justifies access burden.

## D06 — A.1 synthesis threshold — APPROVED

Require at least two independent admitted study families with compatible endpoints/windows for a cross-study longitudinal synthesis. One study can support a descriptive/mechanistic module, not a general meta-analysis.

## D07 — endpoint admission — APPROVED

Use exact objective-response mapping where CR/PR/SD/PD are recoverable. Source-binary response is separately labelled. PSA, pathological and time-to-event endpoints remain distinct.

## D08 — historical implementation migration — APPROVED

Preserve the historical GitHub repository and NMRbox archive unchanged. Adapt reusable utilities into new paths with characterization tests; never grandfather historical outputs.

## D09 — protocol denominator — APPROVED

Treat approximately six cohorts/~200 patient samples as a planning estimate, not an implementation quota. Report verified patients, specimens and assays separately.

## D10 — paired multi-omics terminology — APPROVED

Use “paired” only after verified same-patient linkage. Report same-timepoint and same-specimen denominators separately.

## D11 — branch and PR disposition — APPROVED BY TASK AUTHORIZATION

Create the review branch `review/a-data-acquisition-validation-speckit-20261012`, open a draft PR, do not merge automatically and do not close issues #1 or #7.
