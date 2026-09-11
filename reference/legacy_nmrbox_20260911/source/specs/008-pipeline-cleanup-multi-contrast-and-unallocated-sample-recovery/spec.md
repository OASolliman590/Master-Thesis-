# Feature Specification: Pipeline Cleanup, Multi-Contrast Routing, and Unallocated Sample Recovery

**Feature Branch**: `008-pipeline-cleanup-multi-contrast-and-unallocated-sample-recovery`
**Created**: 2026-05-10
**Status**: Active
**Input**: Spec 007 verified run `results/full_pipeline_20260508_204646` plus ClawBio `rnaseq-de`, `bio-orchestrator`, and `diff-visualizer` skill contracts.

## Context Lock

Spec 007 made the PRE_RESPONSE evidence path thesis-usable: 22 PRE_RESPONSE cohorts analyzed, 163 signature genes, patient-level artifacts present, and layered immune-state outputs present. However, the pipeline is still conceptually centered on baseline R-vs-NR analysis and does not account cleanly for every sample in the manifest.

Current manifest inventory:

- Total curated sample rows: 1,314
- Timing/response allocatable rows: 1,120
- Unallocated rows: 194
- Current unallocated reason: unknown response

Initial contrast capacity:

| Contrast | Definition | Current eligible cohort count |
|---|---|---:|
| PRE_RESPONSE | pre-treatment R vs pre-treatment NR | 22 |
| POST_RESPONSE | post-treatment R vs post-treatment NR | 5 |
| ON_RESPONSE | on-treatment R vs on-treatment NR | 1 |
| TREATMENT_DELTA | paired after-minus-pre delta, R delta vs NR delta | 3 |

## ClawBio-Informed Principles

- Every sample must be assigned to an explicit analysis bucket.
- DE must be driven by explicit metadata and contrast definitions, not hidden code branches.
- Outputs must include reproducibility commands, environment notes, and checksums.
- Unknown-response samples must not be silently included in response DE.
- Visualization/reporting should consume completed DE outputs and preserve provenance.

## Requirements

- **FR-001**: Add `intake build-sample-allocation` to produce a sample-level allocation matrix.
- **FR-002**: The allocation matrix MUST assign every sample to exactly one `assigned_bucket`.
- **FR-003**: Supported buckets are `PRE_RESPONSE`, `POST_RESPONSE`, `ON_RESPONSE`, `TREATMENT_DELTA`, `QC_ONLY`, and `UNALLOCATED_REQUIRES_CURATION`.
- **FR-004**: Unknown-response samples MUST be assigned to `UNALLOCATED_REQUIRES_CURATION`.
- **FR-005**: Emit `unallocated_samples.tsv` and `cohort_allocation_summary.tsv`.
- **FR-006**: Emit a reproducibility bundle with `commands.sh`, `environment.yml`, and `checksums.sha256`.
- **FR-007**: Add POST_RESPONSE and ON_RESPONSE support to Stage 06 DE.
- **FR-008**: Add contrast-first router mode via `router run --contrasts`.
- **FR-009**: Preserve legacy `--track ALL|A|B|C` behavior.
- **FR-010**: Extend comparison registry to support PRE_RESPONSE, POST_RESPONSE, ON_RESPONSE, and TREATMENT_DELTA.
- **FR-011**: Update documentation so every sample state is explainable.
- **FR-012**: Full multi-contrast reports MUST summarize analyzed, blocked, QC-only, and unallocated samples.

## Success Criteria

1. `results/spec_008/sample_allocation_matrix.tsv` exists and has one row per curated manifest row.
2. `results/spec_008/unallocated_samples.tsv` captures all currently unallocated samples.
3. No unknown-response sample enters response DE.
4. `cmd_de_run` can emit non-empty POST_RESPONSE and ON_RESPONSE outputs when cohorts have >=2 R and >=2 NR samples for those timings.
5. `router run --contrasts PRE_RESPONSE,POST_RESPONSE,ON_RESPONSE,TREATMENT_DELTA` builds a contrast-first route.
6. Existing Spec 007 PRE_RESPONSE path remains reproducible.
7. Tests pass.

## Out Of Scope

- Methylation integration. This is deferred beyond Spec 008.
- Forcing uncertain labels into response analysis.
- Replacing the entire pipeline with ClawBio. ClawBio is used as a reproducibility and contract model.

