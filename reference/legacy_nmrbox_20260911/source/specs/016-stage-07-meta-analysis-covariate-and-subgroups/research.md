# Research: Spec 016 — Stage 07 Meta-Analysis Hardening

## 1. Core Estimator Status
The FE/RE inverse-variance implementation is mathematically sound; Round-3 work focuses on contract safety and inference framing.

## 2. Contract Risks Addressed
- Mixed-scale effects from heterogeneous Stage-06 inputs can invalidate pooled logFC interpretation.
- k=1 genes can masquerade as pooled evidence.
- Over-parameterized subgrouping is underpowered at current cohort count.

## 3. Locked Decisions
- Enforce common-scale input guard before meta pooling.
- Keep subgrouping constrained; expose low-dimensional cancer-group moderator.
- Separate k=1 rows to `meta_single_cohort.tsv` with explicit `meta_basis`.
- Support Knapp-Hartung as an optional inference sensitivity mode.

## 4. Scientific Validity
These controls reduce false confidence from thin or incomparable evidence while preserving the established inverse-variance meta core.
