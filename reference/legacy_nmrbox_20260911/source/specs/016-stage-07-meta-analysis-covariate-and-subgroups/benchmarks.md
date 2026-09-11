# Benchmarks: Spec 016 — Stage 07 Meta Hardening

## Correctness Benchmarks
- Common-scale guard rejects incompatible Stage-06 inputs.
- k=1 rows are excluded from pooled FDR and emitted separately.
- Optional Knapp-Hartung path runs and emits stable outputs.

## Performance Benchmarks
- Runtime overhead for guard checks and k=1 split should be minimal versus baseline meta runtime.
