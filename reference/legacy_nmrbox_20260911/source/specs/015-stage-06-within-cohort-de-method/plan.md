# Plan: Spec 015 — Stage 06 Within-Cohort DE Method

## Architecture

Extract DE into `src/pipeline/modules/_06_within_cohort_de/` with:
- `harmonize.py` — assay_type-driven transform to common log2 scale (consumes spec-010 `assay_type`).
- `de_models.py` — uniform effect computation: dispatch to limma (`scripts/rna_limma.R`, new) / DESeq2 (`rna_deseq2.R`, existing) / edgeR; all emit `{log2fc, se, model_class}`.
- `mediation.py` — optional composition-mediation/decomposition (D5), consuming spec-018 deconvolution.

CLI `de run` preserved; dispatches to the module. The magnitude `is_log` heuristic is deleted.

## Milestones
- **M1** Spec kit (this commit + research/plan/benchmarks/quickstart).
- **M2** Tests-first: simulated dataset with known effect → SE-correctness per path; assay-routing tests.
- **M3** `harmonize.py` + delete `is_log` heuristic.
- **M4** `de_models.py` + new `scripts/rna_limma.R` (limma-trend); wire DESeq2/edgeR; uniform output schema.
- **M5** Replace Welch default; flagged-fallback only.
- **M6** Composition-unadjusted primary; optional adjusted secondary + mediation hook (D5).
- **M7** Migration report (which cohorts' representation/model changed).
- **M8** Reproducibility bundle, runbook, sign-off.

## Dependencies
- **Blocks-on:** spec 010 (`assay_type` Active) — hard dependency.
- **Feeds:** spec 016 (meta input guard), spec 017 (signature), spec 018 (mediation needs deconvolution; soft — can land adjusted-variant later).
- R: limma, DESeq2, edgeR (Bioconductor).

## Rollback
- New module dispatches behind the existing `de run` CLI; revert by re-pointing to in-`cli.py` `cmd_de_run`.
- Old Welch results are reproducible via the flagged fallback for diff/migration.
- No committed results overwritten; outputs land in a new Stage-06 run dir; migration report quantifies the change before any rerun.

## Constitutional Checks
6-file template ✓; contracts frozen in research.md §3 ✓; tests-first (M2) ✓; reproducibility bundle (M8) ✓; scientific-validity section (research.md §4) ✓; carries forward spec-009/010 module + bundle patterns ✓.
