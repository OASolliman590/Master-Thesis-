# Implementation Plan: Spec 026 — Analysis Design Contrast Registry

## Milestones

- **M1**: Write the spec-kit documents and I/O contracts.
- **M2**: Add tests-first fixtures for mixed timing, paired DELTA, drug/cancer strata, unknown labels, and hard-excluded assay types.
- **M3**: Implement normalized sample manifest and contrast registry generation.
- **M4**: Wire `design build` CLI and router dry-run registry consumption.
- **M5**: Add optional `analysis_id` support to DE/meta outputs while preserving legacy contrast commands.
- **M6**: Verify with targeted unit/integration tests and record benchmark commands.

## Constraints

- Do not mutate committed `results/` artifacts during implementation.
- Keep PRE/DELTA legacy commands backward-compatible.
- Treat all analysis axes as co-equal discovery families, with interpretation encoded in metadata rather than priority.

