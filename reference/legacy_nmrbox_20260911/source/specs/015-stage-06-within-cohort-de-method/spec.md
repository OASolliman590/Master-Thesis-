# Feature Specification: Stage 06 — Within-Cohort DE Method Correctness

**Feature Branch**: `015-stage-06-within-cohort-de-method`
**Created**: 2026-05-30
**Status**: Active (implementation cycle complete under no-results-mutation policy; full-run output regeneration/sign-off pending approval)
**Scientific-priority rank**: **2 of 8** (after the X1 assay contract). Severity **S1**.
**Input**: 2026-05-30 review §"Stage 06" + cross-cutting X1. Depends on spec 010 (`assay_type` contract) being Active.

## Context Lock

`cmd_de_run` (cli.py L4273). Today: count-based DE (DESeq2/edgeR via `scripts/rna_deseq2.R` / `rna_edger.R`) runs **only** when `input_class=="raw_counts" AND _looks_like_count_matrix` (L4561). All other cohorts fall to a **per-gene Welch t-test on log2(x+1)** (`welch_t_test_log2`, L4641–4664). The `se_or_stat` column carries different quantities by path (06c). TREATMENT_DELTA uses a Welch t-test on per-gene deltas (06d).

## Findings addressed

- **06a (S1):** unmoderated Welch t-test on normalized/microarray cohorts → unstable variance at small n; field standard is limma-voom (counts→logCPM) or limma (microarray).
- **06b (S1):** fragile double-gate for count DE; mis-routing silent. Replace with spec-010 `assay_type`.
- **06c (S2, refined Step-4 audit):** `rna_deseq2.R` emits **unshrunken MLE log2FC + Wald `lfcSE`** (no `lfcShrink`) — so it is already meta-compatible; the real incommensurability is the **Welch naive-SE** path vs proper model SE. `se_or_stat` must carry a single, documented SE on the common log2 scale so Stage 07 pools validly.
- **06d (S2):** moderate the DELTA test too.
- **X3 (S2):** decide purity/composition covariate handling (coordinate with spec 018).

## Draft Functional Requirements

> **Design note (study_design_decisions_2026-05-30.md D2):** the approach is **harmonize-to-common-scale THEN one uniform effect**, NOT a per-assay model zoo. This *simplifies* the stage and salvages the existing correct inverse-variance meta (it only needs honest per-cohort SEs).

- **FR-001**: Each cohort's matrix MUST be **harmonized to a common log2 scale** before modelling, driven by spec-010 `assay_type`: verified `raw_counts`→VST/rlog (or `log2(CPM+1)`); linear `tpm/fpkm`→`log2(x+1)`; `log_normalized`→as-is; `methylation_beta` and `unreadable`→**hard-excluded** from RNA DE. No magnitude heuristic.
- **FR-002**: A **single uniform per-cohort effect computation** on the common scale MUST emit `log2fc` + an honest `se` (true standard error on the log2 scale) + `model_class`. Primary pooled quantity remains **inverse-variance logFC + SE** (existing meta). Hedges' g / SMD is a sensitivity-only alternative (rejected as primary: inflates low-variance genes).
- **FR-003**: The unmoderated Welch t-test MUST be replaced by an empirical-Bayes-moderated test (limma `eBayes`, `trend=TRUE` where appropriate); raw Welch retained only as an explicitly-flagged fallback. For verified counts, DESeq2/edgeR or limma-voom (voom is valid only on counts) is acceptable provided it emits a comparable log2 effect + SE.
- **FR-004**: TREATMENT_DELTA MUST use a moderated within-subject model (paired limma / `duplicateCorrelation`) rather than Welch on deltas.
- **FR-005**: The R DE scripts MUST be audited so the design and reported `se_or_stat` (lfcSE) are documented and match the meta-analysis's SE assumption (Step-4 source audit).
- **FR-006**: A migration report MUST list every cohort whose representation/model changed vs the prior run and the effect on its top genes.
- **FR-007 (X3 — REVISED per D5, mediator-not-confounder)**: Immune infiltration is a **mediator**, not a confounder. The **primary** signature is **composition-UNADJUSTED** (the total response association — the thesis-relevant quantity). A composition-adjusted variant MAY be reported but MUST be labeled **"survives infiltration adjustment"** (a stricter, possibly over-conditioned subset), NOT "tumor-intrinsic epigenetic signal." Separating tumor-intrinsic from infiltration-driven effect requires an explicit **mediation/decomposition** analysis (composition from spec 018 as mediator), NOT default covariate adjustment.

## Success Criteria (sketch)
- Every cohort's DE method is determined by `assay_type` and recorded; zero cohorts use magnitude-guess routing.
- `se` is a true standard error on the log2 scale for all paths (verified against a simulated dataset with known effect).
- Re-run reproduces or corrects the meta inputs; migration report committed.

## Out Of Scope
- The meta-analysis pooling itself (spec 016).
- Assay-type detection (spec 010).

## Implementation Notes (Round 3)
- Stage-06 now routes by `assay_type` with common-scale harmonization and `methylation_beta`/`unreadable` hard exclusion.
- Normalized/log cohorts use moderated limma-trend (`scripts/rna_limma.R`) by default; Welch is retained only as explicit `--allow-welch-fallback`.
- Verified count cohorts remain on DESeq2/edgeR paths with meta-compatible `log2fc + se_or_stat`.
- TREATMENT_DELTA uses moderated limma on within-subject deltas (`*_delta` model classes), replacing the legacy Welch default.
- Primary-vs-secondary signature framing is implemented as composition-unadjusted primary and composition-adjusted labeled secondary.
