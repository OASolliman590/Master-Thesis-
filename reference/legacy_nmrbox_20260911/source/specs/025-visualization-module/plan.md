# Plan: Spec 025 — Visualization Module

## Architecture
```
src/pipeline/modules/_viz/
  registry.py        # load configs/figure_registry.tsv → figure contracts
  builders/          # one builder per figure type (qc, pca, volcano, forest, heatmap, ssgsea, tcga, concordance)
  build.py           # orchestrate: for each figure → resolve inputs → render → manifest + caption sidecar
```
New CLI group `viz` with `viz build`. `qc_plots.py` builders are imported/reused; the inline forest code in `cmd_meta_run` is moved here and Stage 07 calls `_viz`.

## Milestones
- **M1** Spec kit (this commit).
- **M2** Tests-first: per-builder render test on a fixture; manifest-completeness integration test.
- **M3** `registry.py` + `configs/figure_registry.tsv` (the §2 catalogue).
- **M4** Builders: reuse qc_plots; add volcano, signature heatmap, ssGSEA-layer, TCGA-KM (continuous), Thorsson-assoc, concordance.
- **M5** `scientific_note` enforcement (every figure has one; lint test).
- **M6** Move forest code out of `cmd_meta_run`; Stage 07 dispatches to `_viz`.
- **M7** Reproducibility bundle, runbook (figure-number → figure_id map), sign-off.

## Dependencies
- **Soft-blocks-on** the corrected outputs: specs 016 (forest), 018 (ssGSEA), 021 (TCGA). Builders can be written against the frozen output schemas before those stages finish, but figures are only *scientifically valid* once those land — gate the thesis-final build on them.
- matplotlib (Agg), pandas, numpy. No new heavy deps.

## Rollback
- New `viz` CLI is additive; existing stage-side-effect plots remain until M6 moves them. Revert by leaving `cmd_meta_run`'s inline forest in place.
- Figures write to a fresh `--out`; nothing overwritten.

## Constitutional Checks
6-file template ✓; figure contract frozen (research §2) ✓; tests-first (M2) ✓; reproducibility bundle (M7) ✓; scientific-validity = labeling discipline (research §3) ✓.
