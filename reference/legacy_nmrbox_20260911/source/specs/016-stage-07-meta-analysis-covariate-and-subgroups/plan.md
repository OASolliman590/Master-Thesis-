# Plan: Spec 016 — Stage 07 Meta-Analysis Hardening

## Architecture
- Preserve the existing inverse-variance FE/RE estimator.
- Harden input contracts and inference policy:
  - common-scale guard (spec 015 compatibility),
  - k=1 segregation,
  - low-dimensional cancer-group moderator,
  - optional Knapp-Hartung path.

## Milestones
- **M1** Baseline math audit of existing estimator path.
- **M2** Contract lock with Stage-06 output schema.
- **M3** Implement guard + covariate + k=1 handling.
- **M4** Add test coverage for guard and k=1 side outputs.
- **M5** Runbook/changelog sign-off.

## Dependencies
- Upstream: spec 015 within-cohort DE harmonization.
- Downstream: spec 017 signature derivation and Stage-10 robustness framing.

## Rollback
- Core estimator remains unchanged; hardening is additive guards and side outputs.
