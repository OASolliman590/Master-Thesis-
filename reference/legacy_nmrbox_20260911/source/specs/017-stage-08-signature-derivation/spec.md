# Feature Specification: Stage 08 — Signature Derivation

**Feature Branch**: `017-stage-08-signature-derivation`
**Created**: 2026-05-30
**Updated**: 2026-06-05
**Status**: Active next RNA-seq cycle; full 6-file spec package now defined, implementation pending
**Scientific-priority rank**: **8 of 8** (depends on 06/07 being fixed first). Severity **S2**.
**Input**: 2026-05-30 review section "Stage 08"; downstream continuation refocus after corrected Stage 06/07 outputs.

## Context Lock
`cmd_signature_derive` (cli.py L6068). Tiered FDR/effect thresholds (tier_1 FDR≤0.05 & |effect|≥1.0 → tier_3 FDR≤0.50 & |effect|≥0.3), `min_meta_cohorts` floor (default 2).

## Findings addressed
- **08a (S2):** signature selected on the same data later "validated" on the same data — circularity (resolved jointly with spec 019's independent validation).
- **08b (S3):** |effect|≥1.0 (2-fold) floor on a meta of mixed-scale effects (X1) is not interpretable until Stage 06/07 emit common-scale effects.

## Current downstream role

Stage 08 is now the key RNA-seq continuation point. Stage 09 implementation is recorded as complete but still needs output regeneration/sign-off on corrected run roots; Stage 08 remains the stage that turns corrected Stage 06/07 meta-analysis outputs into a frozen responder/non-responder signature registry.

The stage must consume analysis-aware, corrected common-scale meta outputs and produce signatures that can feed Stage 10 validation framing, Stage 12 TCGA projection, visualization, reports, and wet-lab handoff.

## Functional Requirements

- **FR-001**: Thresholds MUST be applied only to corrected common-scale meta effects from Stage 06/07. If effect scales are mixed or missing, the analysis MUST block rather than silently derive a signature.
- **FR-002**: Tier thresholds MUST be explicit, configurable, and justified by scientific use: core wet-lab panel, broader exploratory biology, and sensitivity/appendix tiers.
- **FR-003**: Signature derivation MUST support nested or leave-one-cohort-out derivation so derivation and evaluation can be separated for Stage 10.
- **FR-004**: Every signature row MUST preserve provenance: `analysis_id`, analysis family, timing label, contrast direction, contributing cohorts, gene identifier, effect, standard error if available, FDR, heterogeneity metrics if available, evidence tier, module assignment, and blocked/missing-data flags.
- **FR-005**: Same-sample concordance MUST NOT be labelled external validation. Stage 08 outputs must carry labels that Stage 10 can use for internal robustness versus held-out/LOCO evaluation.
- **FR-006**: Module assignment MUST be reproducible from a registry or rule table, not from manual prose only.
- **FR-007**: Extract signature logic to `_08_signature` or the repository's current module pattern; add tests, reproducibility metadata, and a runbook.

## Outputs

Required outputs:

```text
signature_registry.tsv
responder_signature_core.tsv
responder_signature_tiered.tsv
signature_derivation_audit.tsv
signature_thresholds.yaml
signature_module_assignment.tsv
signature_loco_derivation_manifest.tsv
```

## Success Criteria

- Stage 08 refuses mixed-scale or uncorrected meta effects.
- Tiered signatures are reproducible from `signature_thresholds.yaml`.
- At least one LOCO/nested derivation manifest is emitted or the run declares why held-out evaluation is blocked.
- All signature rows trace back to `analysis_id` and contributing cohorts.
- Stage 10 can consume the emitted files without reclassifying same-sample concordance as external validation.
