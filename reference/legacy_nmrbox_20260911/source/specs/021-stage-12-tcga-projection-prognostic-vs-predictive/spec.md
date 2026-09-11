# Feature Specification: Stage 12 — TCGA Projection: Prognostic vs Predictive

**Feature Branch**: `021-stage-12-tcga-projection-prognostic-vs-predictive`
**Created**: 2026-05-30
**Status**: Complete (implementation + tests landed in Round 3)
**Scientific-priority rank**: **5 of 8** (framing). Severity **S2 (framing)**.
**Input**: 2026-05-30 review §"Stage 11/12"; spec 007 Layer-4-vs-Thorsson intent.

## Context Lock

`cmd_tcga_project` (cli.py L9093). Scores TCGA samples as `mean(up-genes) − mean(down-genes)` (L9261–9265), median-splits High/Low (L9267–9268), runs survival via `scripts/tcga_survival.R`.

## Findings addressed

- **12a (S2, framing):** TCGA patients are **not ICB-treated** → survival association tests **prognostic** value (general outcome under standard care), NOT **predictive** value (ICB-specific benefit). Conflation is defense-critical.
- **12b (S2):** projection score is a **raw mean of expression** (no per-gene z-scoring) → high-baseline genes dominate; not comparable across genes/projects.
- **12c (S3):** median dichotomization for survival discards information vs continuous Cox.
- **spec-007 intent:** the more defensible TCGA use is Layer-4 epigenetic sets vs **Thorsson 2018 immune subtypes** (subtype association), not survival-as-validation.

## Draft Functional Requirements

- **FR-001**: All TCGA outputs/reports MUST label the analysis **prognostic** (or exploratory prognostic context), never "validation" of an ICB-response signature.
- **FR-002**: The projection score MUST z-score (standardize) each gene before combining up/down, so no single gene's baseline dominates; document the scaling.
- **FR-003**: Survival MUST use the continuous score in a Cox model (median split only as a secondary visualization).
- **FR-004**: Implement the spec-007 Layer-4 vs Thorsson immune-subtype association (SKCM, BLCA, HNSC, LUAD, KIRC) as the primary, defensible TCGA analysis.
- **FR-005 (Step-4 audit CONFIRMED):** `scripts/tcga_survival.R` currently **median-splits** `signature_group` (Low/High) and runs `coxph(Surv ~ signature_group)` with **no covariates** (no stage/age). FR-003 (continuous Cox) replaces the split; add stage/age covariates where available.

## Success Criteria (sketch)
- No "validation" wording for TCGA; prognostic framing throughout.
- z-scored continuous-Cox projection implemented and tested.
- ≥3 Layer-4 sets show FDR<0.1 association with a Thorsson subtype (spec-007 success bar) or the negative result is reported honestly.

## Out Of Scope
- ICB-treated external validation (spec 019).

## Implementation Notes (Round 3)
- TCGA projection now emits z-scored signature inputs (`signature_score_z`) and uses continuous Cox framing.
- Projection status/report framing is prognostic-only (non-ICB context).
- Layer-4 vs Thorsson association path is wired and optional via `--thorsson-subtypes`.
- Survival script now supports optional age/stage covariates when available and reports model covariate contract.
