# Plan: Spec 021 — Stage 12 TCGA Projection Framing

## Architecture
- Keep `cmd_tcga_project` as orchestrator.
- Use z-scored signature score for continuous Cox.
- Keep KM grouping as visualization only.
- Add optional Layer-4 vs Thorsson association as primary TCGA biological context path.

## Milestones
- **M1** Audit current projection and survival modeling behavior.
- **M2** Lock prognostic framing and output schema.
- **M3** Implement z-score + continuous Cox contract.
- **M4** Wire optional Thorsson association and tests.
- **M5** Add optional age/stage covariate support and preserve model-contract output.
- **M6** Runbook/changelog sign-off.

## Dependencies
- Stage-11 TCGA map artifacts.
- Layer-4 registry and GMT coverage (spec 018).

## Rollback
- Contract-level and artifact-level updates only; no forced full rerun in this cycle.
