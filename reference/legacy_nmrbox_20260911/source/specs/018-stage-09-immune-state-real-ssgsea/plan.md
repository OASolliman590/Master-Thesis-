# Plan: Spec 018 — Stage 09 Real ssGSEA / Deconvolution / Layer-4

## Architecture
Extract to `src/pipeline/modules/_09_immune_state/`:
- `ssgsea.py` — dispatch to `scripts/ssgsea_gsva.R` (real GSVA), parse scores, attach layers.
- `deconvolution.py` — dispatch to `scripts/estimate_scores.R` + `scripts/epic_scores.R` (or remove if not pursued).
- `gene_sets/epigenetic_layer/*.gmt` — author the 6 missing Layer-4 sets.

CLI `immune score` preserved; the Python rank-mean backend is deleted.

## Milestones
- **M1** Spec kit (this commit).
- **M2** Tests-first: ssGSEA vs GSVA reference on a fixture; Layer-4 membership tests (8 sets); backend-required failure test.
- **M3** Wire `ssgsea_gsva.R`; remove rank-mean; fix `abs.ranking` for directional sets; assay-correct input (log2).
- **M4** Author 6 Layer-4 GMTs (cited membership); register + score.
- **M5** Wire ESTIMATE/EPIC (or delete placeholders + columns); expose composition as the spec-015 mediator.
- **M6** Reproducibility bundle, runbook, sign-off; mark spec-007 "real ssGSEA" met.

## Dependencies
- **Soft-blocks-on:** spec 010 (assay_type → correct ssGSEA input scale).
- **Feeds:** spec 015 (composition mediator for D5), spec 021 (Layer-4 vs Thorsson).
- R: GSVA, (ESTIMATE), EPIC packages. Fail loudly if missing (no silent proxy).

## Rollback
- Dispatch behind existing `immune score` CLI; revert by restoring the Python backend (kept until M3 sign-off behind `--legacy-rank-mean`, clearly deprecated).
- New scores land in a new run dir; the old `IMMUNE_SCORE_proxy_deprecated` outputs are not overwritten.
- Authoring GMTs is additive.

## Constitutional Checks
6-file template ✓; frozen contracts (research §3) ✓; tests-first (M2) ✓; reproducibility bundle (M6) ✓; scientific-validity (research §4) ✓.
