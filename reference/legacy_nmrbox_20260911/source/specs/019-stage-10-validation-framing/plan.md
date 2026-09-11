# Plan: Spec 019 — Stage 10 Validation Framing

## Architecture
- Keep `cmd_validate_run` as orchestration surface.
- Separate two concepts:
  - internal cross-method concordance (same-sample robustness),
  - independent held-out/nested evaluation (external evidence).

## Milestones
- **M1** Audit wording and current artifacts.
- **M2** Lock held-out input schema + readiness status vocabulary.
- **M3** Implement framing and held-out schema guards.
- **M4** Add tests for missing/malformed/out-of-range held-out metrics.
- **M5** Runbook + changelog sign-off.

## Dependencies
- Upstream: corrected signature/meta outputs.
- Related: spec 021 for TCGA prognostic framing.

## Rollback
- Changes are additive artifacts and stricter contracts; no pipeline-wide rerun required.
