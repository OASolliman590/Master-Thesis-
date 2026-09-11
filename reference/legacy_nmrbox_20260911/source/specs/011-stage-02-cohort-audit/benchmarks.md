# Benchmarks: Spec 011 — Stage 02 Cohort Audit

## Functional Benchmarks
- Audit outputs are deterministic for the same manifest inputs.
- Exclusion reasons are explicit and stable for dedup/drop/assay gates.

## Performance
- Stage-02 runtime should remain negligible compared with Stage-06+.
- No heavy memory growth expected; operations are manifest-sized.
