# Feature Specification: Stage 10 — Validation Framing & Independent Validation

**Feature Branch**: `019-stage-10-validation-framing`
**Created**: 2026-05-30
**Status**: Complete (implementation + tests landed in Round 3)
**Scientific-priority rank**: **5 of 8**. Severity **S1 (framing)**.
**Input**: 2026-05-30 review §"Stage 10" + §"Stage 08" (circularity).

## Context Lock

`cmd_validate_run` (cli.py L6738). Computes GOLD/SILVER/BRONZE concordance between the **indirect meta** (per-cohort DE → meta) and the **mega** (pooled ComBat-Seq + DESeq2) analyses — **both on the same samples**.

## Findings addressed

- **10a (S1, framing):** same-sample concordance is *internal robustness / cross-method agreement*, NOT external validation. Calling it "validation" overstates it.
- **10b (S1, inherited):** the mega arm is invalid under X1 (ComBat-Seq on mixed data types) until spec 015/mega fix; agreement may reflect shared artifacts.
- **08a (S2):** the signature is derived and "validated" on the same data — circularity.

## Draft Functional Requirements

- **FR-001**: Rename/reframe the concordance output as **cross-method robustness** (indirect-vs-mega agreement), with documentation that it is NOT independent validation.
- **FR-002**: Add a **true external validation** path: hold out ICB cohorts with response labels never used in signature derivation, or implement nested/leave-one-cohort-out signature derivation+evaluation, and report AUC/effect concordance on the held-out set.
- **FR-003**: Validation MUST consume the corrected mega (spec 015 / mega data-type fix) before its agreement is reported as meaningful.
- **FR-004**: Report language MUST distinguish prognostic vs predictive where TCGA enters (coordinate with spec 021).

## Success Criteria (sketch)
- No artifact labels same-sample concordance as "validation" without the caveat.
- At least one genuinely held-out evaluation is reported (or LOCO-derived signature evaluation), with effect sizes.

## Out Of Scope
- Signature derivation thresholds (spec 017); mega data-type fix (spec 015).

## Implementation Notes (Round 3)
- Stage-10 outputs now frame indirect-vs-mega concordance as internal robustness (not external validation).
- Added external held-out/nested evaluation contract via `--heldout-evaluation`.
- Held-out schema guard enforces required columns (`auc`, `effect_concordance`), numeric typing, and `[0,1]` bounds.
- Validation summary/status artifacts include external-validation readiness and aggregate held-out metrics.
