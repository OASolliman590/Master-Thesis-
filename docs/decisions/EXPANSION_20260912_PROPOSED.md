# Expansion proposal — 12 September 2026

## Authority and status

The user requested a structured appraisal-to-action approach, expanded sources for all papers, reuse of historical work, processed-data-first analysis, longitudinal comparisons, cellular/spatial evidence, TCGA multi-omics, and Codex handoffs with inline GitHub diagrams. The user endorsed the pretreatment immune-expression programme aim.

This record authorizes a **reviewable specification proposal** and source-feasibility work. It is not external preregistration, supervisor/university approval, a release for all real analyses, or proof that new data are available. Baseline reviewed: `a8278c776da7c6b096cc14139d729979db286b50`.

## Decisions preserved and proposed

Preserve A-P2 as A's selected primary; A-P1 remains secondary. Add an explicit biological-discovery product alongside the predictor. Preserve B-P in the fixed APM module, and keep A-derived/expanded programmes separate. Preserve every agreed C source and D's conditional status. No existing code or recovered-archive bytes are changed.

Propose shared kit [S0](../../specs/S0_EVIDENCE_EXPANSION/README.md). A.1 is a candidate longitudinal/regimen-context module and possible later manuscript, not a new committed publication. TCGA expansion belongs mainly to B with a shared A transfer interface; it does not become an independent ICI-response validation cohort.

The no-raw-reprocessing preference applies to this expansion: inspect/reuse deposited count matrices, normalized matrices, beta values, protein tables and processed cell/spatial objects. Do not initiate FASTQ/BAM, IDAT, raw MS or raw image reconstruction. Missing required processed inputs mean a blocked or narrower module, not a silent change of preference.

## Submitted-protocol crosswalk

The user-supplied eight-page proposal, pages 4–6, specifies cross-cancer responder discovery, pre/on-treatment comparisons, PRAD/LUAD RNA and methylation comparisons, intervention prioritisation and in-vitro validation. The expansion makes baseline and longitudinal inference explicit and adds qualified omics/composition context. General pan-cancer clinical mining, additional assays, A.1 comparative synthesis and D are extensions rather than evidence that institutional approval exists.

Do not reproduce the signed administrative pages or patient-level records in Git. The submitted detection-P wording, equal-size comparison, PRAD/LUAD batch handling and named-drug provenance require separate methodological/supervisor reconciliation. This proposal does not silently rewrite the submitted document or alter wet-lab commitments.

## Initial source-code observations

The recovered `06_within_cohort_de/harmonize.py` fills missing expression with zero and applies a common log transform to several different assay categories. `de_models.py` routes all non-excluded, non-count-qualified inputs to limma-trend. These inspected helper behaviours conflict with the new measurement policy unless upstream checks make the relevant cases impossible; caller paths and tests must be audited. No historical result is declared invalid or reproduced from these observations alone.

## Next decision

Review the X0/X1 source/reuse handback, then approve source-specific analysis contracts. Do not choose a final manuscript count or execute every proposed method before that evidence exists.
