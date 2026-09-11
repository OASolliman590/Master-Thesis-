# Plan: Spec 017 — Stage 08 Signature Derivation

## Architecture

Stage 08 should become a small, auditable signature module rather than a threshold block inside the CLI.

Proposed module boundary:

```text
src/pipeline/modules/_08_signature/
  thresholds.py
  derive.py
  modules.py
  loco.py
  audit.py
```

The existing CLI entrypoint should be preserved, but it should delegate to the module and emit a complete reproducibility bundle.

## Milestones

- **M1** Spec package and contract lock: finish `spec.md`, `plan.md`, `research.md`, `benchmarks.md`, `quickstart.md`, and expanded `tasks.md`.
- **M2** Corrected-output audit: identify the current run root and confirm Stage 06/07 common-scale meta outputs are valid for signature derivation.
- **M3** Tests-first: mixed-scale blocking, deterministic tiering, provenance completeness, and circularity guardrails.
- **M4** Implementation: configurable tier thresholds, module assignment, signature audit, and LOCO/nested manifest.
- **M5** Reproducibility: runbook, threshold YAML, checksums, and report-build integration.
- **M6** Sign-off: focused tests, full suite where feasible, and downstream report build from the selected run root.

## Dependencies

- **Blocks on**: corrected Stage 06/07 outputs from specs 015/016 and analysis design registry from spec 026.
- **Soft-blocks on**: Stage 09 output verification for immune-score-supported module summaries.
- **Feeds**: Stage 10 validation framing, Stage 12 TCGA projection, visualization, reports, and wet-lab handoff.

## Rollback

- Keep old CLI behavior behind a clearly labelled legacy path until new output parity is reviewed.
- Emit new outputs into a new run directory; do not overwrite earlier signature files.
- If corrected common-scale meta outputs are absent, emit a blocked audit rather than partial signatures.

## Constitutional Checks

Six-file template: yes.  
Tests-first: required before implementation.  
Scientific validity: corrected effects, no circular validation, TCGA projection language preserved.  
Reproducibility: thresholds, provenance, and run-root metadata required.
