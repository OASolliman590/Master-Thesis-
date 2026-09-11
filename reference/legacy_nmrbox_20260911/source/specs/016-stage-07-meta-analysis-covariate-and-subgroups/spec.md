# Feature Specification: Stage 07 — Meta-Analysis Inputs, Subgroups, and Covariate

**Feature Branch**: `016-stage-07-meta-analysis-covariate-and-subgroups`
**Created**: 2026-05-30
**Status**: Complete (implementation + tests landed in Round 3)
**Scientific-priority rank**: **7 of 8** (the math is correct; inputs and policy need fixing). Severity S1 inherited / S2 local.
**Input**: 2026-05-30 review §"Stage 07".

## Context Lock

`cmd_meta_run` (cli.py L4735). The inverse-variance fixed + DerSimonian–Laird random-effects implementation (`_compute_meta_stats`, L4859) is **correct**: weights `1/se²`, Q, I², τ², RE weights `1/(se²+τ²)`, z-test, BH-FDR, leave-one-cohort-out, forest plots. The problems are inputs and policy, not the estimator.

## Findings addressed

- **07a (S1, inherited):** pools incompatible effect sizes/SEs from Stage 06 (Welch vs DESeq2). Resolved upstream by spec 015 (common-scale effect/SE); this spec verifies the meta only consumes commensurable inputs.
- **07b (S2):** still emits `cancer_type`/`drug_class` subgroups (`_write_subgroup_meta` L5152; loop L5214) despite the 2026-05-28 amendment dropping cancer subgrouping (too thin in 6/9 cancers).
- **07c (S2):** single-cohort genes (k=1) get a "meta" row (RE=FE, I²=0) that flows into signature/FDR as if pooled.
- **07d (S3):** cancer-as-fixed-effect-covariate (the amendment's intended replacement for subgrouping) is unimplemented — no meta-regression.

## Draft Functional Requirements

- **FR-001 (D2):** the meta MUST refuse to pool unless all contributing effects share the documented common log2 scale + honest SE from spec 015's harmonize-then-uniform-effect path (guard + clear error). Primary pooled quantity stays **inverse-variance logFC + SE** (the existing correct estimator). Input MUST already exclude `methylation_beta`/`unreadable` cohorts and the deduplicated gse126044.
- **FR-002**: Reconcile subgroups with the locked decision: either **remove** `cancer_type` subgrouping or re-enable it with an explicit power justification; keep `drug_class` only if powered. Document the choice.
- **FR-003 (constrained per D4):** implement cancer as a **between-study meta-regression moderator** (NOT a within-cohort covariate — it is constant within most cohorts), collapsed to **{melanoma, NSCLC, HNSCC, other}** with **≤1–2 moderators total** (≥10-studies-per-moderator rule; 21 cohorts cannot support a 9-level moderator). Replaces ad-hoc subgroup tables.
- **FR-004**: k=1 genes MUST be flagged (`meta_basis=single_cohort`) and excluded from the pooled FDR family by default (or reported separately), not treated as pooled evidence.
- **FR-005**: Define and document the multiple-testing family across contrasts/subgroups (cross-cutting X4).
- **FR-006 (refinement, low-priority)**: For small numbers of cohorts (k), the current normal-approximation z p-value is anti-conservative; evaluate the Knapp–Hartung adjustment (t-distribution on k−1 df) as the default RE inference.

## Success Criteria (sketch)
- Meta consumes only common-scale inputs; guard tested.
- Subgroup behaviour matches the documented decision; meta-regression covariate implemented and tested.
- k=1 genes no longer silently enter the pooled signature.

## Out Of Scope
- Fixing the DE inputs (spec 015).
- Signature thresholds (spec 017).

## Implementation Notes (Round 3)
- Stage-07 now enforces the common-scale input contract before pooling.
- k=1 genes are surfaced in `meta_single_cohort.tsv` with `meta_basis=single_cohort` and excluded from pooled FDR by default.
- Low-dimensional cancer grouping (`melanoma`, `nsclc`, `hnscc`, `other`) is available as meta-regression output.
- Knapp-Hartung option is exposed and covered by regression tests.
