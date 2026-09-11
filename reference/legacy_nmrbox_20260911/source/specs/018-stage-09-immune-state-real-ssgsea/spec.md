# Feature Specification: Stage 09 — Real ssGSEA, Real Deconvolution, Layer-4 Gene Sets

**Feature Branch**: `018-stage-09-immune-state-real-ssgsea`
**Created**: 2026-05-30
**Status**: Active (implementation cycle complete under no-results-mutation policy; full-run output regeneration/sign-off pending approval)
**Scientific-priority rank**: **3 of 8**. Severity **S1** (the "ssGSEA" claim).
**Input**: 2026-05-30 review §"Stage 09"; spec 007's unmet "real ssGSEA" + Layer-4 requirements.

## Context Lock

`cmd_immune_score` (cli.py L6147). `_score_gene_sets` (L6247) computes the **mean percentile rank** of set genes per sample (`expr_log.rank(pct=True).loc[genes].mean()`), method-labelled `ssgsea_rank_mean_python`. `gseapy` is imported to check availability (L6174) and then **never used** — even when present, the rank-mean backend runs. ESTIMATE/EPIC are placeholders: `estimate_score = immune_score`, `stromal_score`/`purity_proxy` = `nan`, `epic_fractions` empty, `score_scale="IMMUNE_SCORE_proxy_deprecated"`. HOPE subtype = within-cohort CD274/CD8B median split (L6362).

## Findings addressed

- **09a (S1):** mean-percentile-rank is NOT ssGSEA (no KS-style rank-weighted enrichment). spec 007's "real ssGSEA" unmet.
- **09b (S2):** ESTIMATE/EPIC are fake; X3 (purity adjustment) depends on real deconvolution.
- **09c (S3):** HOPE median split is cohort-dependent.
- **09d:** verify Layer-4 epigenetic GMTs (PRC2_IMMUNE_TARGETS, SWI_SNF_ICB, DNMT_IMMUNE_LOCI, HISTONE_WRITERS_ICB, EPIGENETIC_CHECKPOINT, RETROELEMENT_SENSING, T_CELL_EXHAUSTION_EPIGENETIC, T_CELL_MEMORY_EPIGENETIC — per spec 007) actually ship in the registry and are scored.

> **Step-4 source audit (2026-05-30):** the real backends **already exist** — `scripts/ssgsea_gsva.R` (GSVA `ssgseaParam`/`method="ssgsea"`), `scripts/estimate_scores.R`, `scripts/epic_scores.R` — but `cmd_immune_score` never calls them (it runs the Python rank-mean proxy). **So most of this spec is WIRING, not new methods.** Layer-4 ships only **2 of 8** named sets. Minor: the older-GSVA-API branch in `ssgsea_gsva.R` sets `abs.ranking=TRUE` (non-standard for directional ssGSEA) — review.

## Draft Functional Requirements

- **FR-001**: `cmd_immune_score` MUST dispatch to `scripts/ssgsea_gsva.R` (real GSVA ssGSEA) — mirroring how `cmd_de_run` dispatches to `rna_deseq2.R` — and remove the Python rank-mean backend; method label MUST reflect the real backend and fail loudly if R/GSVA unavailable (no silent fallback). Fix the `abs.ranking` flag for directional sets.
- **FR-002**: ssGSEA input MUST be the correct expression representation per spec-010 `assay_type` (e.g. log2-normalized; not raw counts).
- **FR-003**: ESTIMATE and EPIC MUST be wired to the existing `scripts/estimate_scores.R` / `scripts/epic_scores.R` (which already exist) or be **removed** with the placeholder columns deleted — no `*_proxy_deprecated` masquerading as scores.
- **FR-004**: The **6 missing** Layer-4 epigenetic GMTs (PRC2_IMMUNE_TARGETS, SWI_SNF_ICB, DNMT_IMMUNE_LOCI, HISTONE_WRITERS_ICB, RETROELEMENT_SENSING, T_CELL_EXHAUSTION_EPIGENETIC, T_CELL_MEMORY_EPIGENETIC — spec 007) MUST be authored (with cited gene membership), shipped in `inputs/gene_sets/epigenetic_layer/`, registered, scored, and unit-tested. Only EPIGENETIC_IMMUNE_PRIMING + EPIGENETIC_CHECKPOINT_REGULATION currently ship.
- **FR-005**: Purity/composition estimates (FR-003 deconvolution) MUST be exposed as the **mediator** in the Stage-06 mediation/decomposition analysis (study_design_decisions_2026-05-30.md **D5**: infiltration is a mediator in epigenetic-state→infiltration→response, NOT a confounder to adjust out). Deconvolution quantifies the mediator; it does not justify default covariate adjustment.
- **FR-006**: HOPE subtype thresholds MUST be documented; consider a fixed/external reference rather than cohort-median where defensible.

## Success Criteria (sketch)
- ssGSEA scores match the reference implementation on a fixture within tolerance; rank-mean backend removed.
- ≥3 Layer-4 sets scored across all cohorts; registry test green.
- Deconvolution either produces real fractions or the stage no longer claims to.

## Out Of Scope
- The TCGA Layer-4 vs Thorsson subtype association (spec 021 / a dedicated spec).

## Implementation Notes (Round 3)
- `cmd_immune_score` dispatches to `scripts/ssgsea_gsva.R` by default and fails loudly without R/GSVA.
- Legacy rank-mean scoring remains only behind explicit `--legacy-rank-mean`.
- ESTIMATE/EPIC scripts are wired and proxy-deprecated score semantics removed from outputs.
- Layer-4 registry/test coverage includes all required epigenetic sets.
- Legacy GSVA API branch now uses directional scoring (`abs.ranking = FALSE`) for ssGSEA compatibility.
