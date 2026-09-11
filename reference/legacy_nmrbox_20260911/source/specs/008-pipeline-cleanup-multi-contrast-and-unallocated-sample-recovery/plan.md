# Implementation Plan: Spec 008

## Architecture

Spec 008 introduces a contrast-first layer without breaking the legacy track path. The first production object is the allocation matrix: every sample is assigned to a bucket before routing or DE.

The implementation path is:

1. Build allocation audit from `configs/sample_manifest_curated.tsv`.
2. Extend DE contrast resolution for PRE, POST, ON, and DELTA.
3. Add router `--contrasts` mode that writes a `multi_contrast` manifest.
4. Update reports and docs to make all sample states explicit.

## Current Slice

Implemented in the first slice:

- `intake build-sample-allocation`
- `sample_allocation_matrix.tsv`
- `cohort_allocation_summary.tsv`
- `unallocated_samples.tsv`
- allocation reproducibility bundle
- POST_RESPONSE and ON_RESPONSE DE selection
- `router run --contrasts`

## Follow-On Slices

- Refactor contrast selection out of `src/pipeline/cli.py` into a dedicated Stage 06 module.
- Add contrast-first visualization and signature orchestration.
- Add full multi-contrast `run_full_pipeline.sh` mode.
- Add unallocated cohort recovery curation templates.

